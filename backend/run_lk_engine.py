#!/usr/bin/env python3
"""
Lal Kitab Engine — Main Entry Point
====================================
Interactive CLI that:
  1. Collects user input (name, DOB, TOB, place)
  2. Builds Natal + 75 Annual charts via ChartGenerator
  3. Runs the full Grammar + Strength + Rules Engine pipeline
  4. Saves a structured JSON output ready for LLM analysis

Usage:
    cd <project-root>
    PYTHONPATH=backend python backend/run_lk_engine.py

Or, if using the venv:
    PYTHONPATH=backend backend/.venv/bin/python backend/run_lk_engine.py
"""

import os
import sys
import json
import re
import logging
from datetime import datetime

# ── Path bootstrap ────────────────────────────────────────────────────────────
BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# ── Core imports ──────────────────────────────────────────────────────────────
from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.grammar_analyser import GrammarAnalyser
from astroq.lk_prediction.strength_engine import StrengthEngine
from astroq.lk_prediction.rules_engine import RulesEngine
from astroq.lk_prediction.prediction_translator import PredictionTranslator
from astroq.lk_prediction.pipeline import LKPredictionPipeline

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.WARNING,
                    format="%(levelname)s  %(name)s: %(message)s")

DATA_DIR       = os.path.join(BACKEND_DIR, "data")
DB_PATH        = os.path.join(DATA_DIR, "rules.db")
DEFAULTS_PATH  = os.path.join(DATA_DIR, "model_defaults.json")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _safe_filename(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9\s]", "", name).strip().replace(" ", "_").lower()


def _prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        val = input(f"  {label}{suffix}: ").strip()
    except KeyboardInterrupt:
        print("\n\nAborted.")
        sys.exit(0)
    return val or default


def _extract_charts(payload: dict) -> tuple[dict, list[dict]]:
    """
    Splits build_full_chart_payload() output into (natal_chart, annual_charts_list).

    Payload keys:   chart_0  = Natal,  chart_1..chart_75 = Annual year 1-75,
                    metadata = system metadata (skip)
    """
    natal_chart    = payload.get("chart_0")
    annual_charts  = []
    for key in sorted(payload.keys()):
        if key == "chart_0" or not key.startswith("chart_"):
            continue
        c = payload[key]
        if isinstance(c, dict) and c.get("chart_type") == "Yearly":
            annual_charts.append(c)
    return natal_chart, annual_charts


# ─────────────────────────────────────────────────────────────────────────────
# Core pipeline runner
# ─────────────────────────────────────────────────────────────────────────────

def _build_chart_section(
    chart: dict,
    pipeline: LKPredictionPipeline,
    is_natal: bool = False
) -> dict:
    """
    Runs the full pipeline on a single chart and returns a compact JSON section.

    Steps:
      1. Masnui detection (so house_status is accurate)
      2. House status enrichment
      3. Strength calculation
      4. Grammar rules (Dharmi, Kaayam, Sleeping, BilMukabil, etc.)
      5. Rules engine evaluation
      6. Prediction translation
    """
    # Run through the pipeline (sets chart["_enriched"] as a side effect)
    predictions = pipeline.generate_predictions(chart)

    # After pipeline runs, enriched data is attached to chart["_enriched"]
    enriched = chart.get("_enriched", {})

    # ── Collect grammar signals ────────────────────────────────────────────
    grammar_signals = []
    if chart.get("mangal_badh_status") == "Active":
        grammar_signals.append(f"Mangal Badh: Active (counter={chart.get('mangal_badh_count', 0)})")
    if chart.get("dharmi_kundli_status") == "Dharmi Teva":
        grammar_signals.append("Dharmi Teva: Protected Chart (Jupiter+Saturn conjunct)")
    if chart.get("andhi_kundli_status") and chart["andhi_kundli_status"] != "Normal":
        grammar_signals.append(f"Andhi Kundli: {chart['andhi_kundli_status']}")
    for debt in chart.get("lal_kitab_debts", []):
        if debt.get("active"):
            grammar_signals.append(f"Karmic Debt: {debt['debt_name']}")
    for masnui in chart.get("masnui_grahas_formed", []):
        grammar_signals.append(
            f"Masnui: {masnui['masnui_graha_name']} (H{masnui['formed_in_house']}) "
            f"← [{', '.join(masnui.get('components', []))}]"
        )

    # ── Planet positions + grammar state ──────────────────────────────────
    # enriched contains strength, sleeping, kaayam, dharmi, aspects per planet
    planet_states = {}
    for p_name, p_data in chart.get("planets_in_houses", {}).items():
        ep = enriched.get(p_name, p_data)  # enriched has grammar-enhanced data
        states = []
        if ep.get("sleeping_status"):
            states.append(ep["sleeping_status"])
        if ep.get("kaayam_status") == "Kaayam":
            states.append("Kaayam")
        if ep.get("dharmi_status"):
            states.append(ep["dharmi_status"])
        if ep.get("is_masnui_parent"):
            states.append("Masnui Parent")
        if ep.get("bilmukabil_hostile_to"):
            states.append(f"BilMukabil ← {ep['bilmukabil_hostile_to']}")
        planet_states[p_name] = {
            "house": p_data.get("house"),
            "strength": round(ep.get("strength_total", 0.0), 2),
            "states": states,
        }

    # ── Significant aspects (from enriched, populated by _find_aspects) ───
    significant_aspects = []
    for p_name, ep in enriched.items():
        for asp in ep.get("aspects", []):
            if asp.get("aspect_type") in {"100 Percent", "50 Percent", "25 Percent"}:
                significant_aspects.append({
                    "from": p_name,
                    "to": asp.get("target", "?"),
                    "type": asp["aspect_type"],
                    "relationship": asp.get("relationship", "neutral"),
                })

    section = {
        "planet_positions": planet_states,
        "grammar_signals": sorted(set(grammar_signals)),
        "significant_aspects": significant_aspects,
        "predictions": [p.prediction_text for p in predictions if p.prediction_text],
    }
    return section



def run_engine(
    client_name: str,
    dob: str,
    tob: str,
    place: str,
    chart_system: str = "vedic",
    annual_basis: str = "vedic",
    output_path: str = None,
) -> str:
    """
    Full engine run. Returns the path to the output JSON file.
    """
    print()
    print("─" * 60)
    print(f"  Step 1/3  Generating astronomical charts …")
    print("─" * 60)

    generator = ChartGenerator()
    payload = generator.build_full_chart_payload(
        dob_str=dob,
        tob_str=tob,
        place_name=place,
        chart_system=chart_system,
        annual_basis=annual_basis,
    )

    natal_chart, annual_charts = _extract_charts(payload)
    if not natal_chart:
        raise RuntimeError("ChartGenerator returned no natal chart (chart_0 missing).")

    print(f"  ✓  Natal chart built.  {len(annual_charts)} annual charts generated.")

    # ── Initialise pipeline ───────────────────────────────────────────────
    print()
    print("─" * 60)
    print(f"  Step 2/3  Initialising Grammar + Rules engine …")
    print("─" * 60)

    cfg      = ModelConfig(db_path=DB_PATH, defaults_path=DEFAULTS_PATH)
    pipeline = LKPredictionPipeline(cfg)
    pipeline.load_natal_baseline(natal_chart)

    # ── Natal chart ───────────────────────────────────────────────────────
    print("  Running natal chart …")
    natal_section = _build_chart_section(natal_chart, pipeline, is_natal=True)
    print(f"  ✓  Natal:  {len(natal_section['predictions'])} predictions,  "
          f"{len(natal_section['grammar_signals'])} grammar signals")

    # ── Annual charts (deterministic, ordered) ───────────────────────────
    print()
    print("─" * 60)
    print(f"  Step 3/3  Running {len(annual_charts)} annual charts …")
    print("─" * 60)

    timeline = []
    for chart in annual_charts:
        age = chart.get("chart_period", 0)
        section = _build_chart_section(chart, pipeline)
        timeline.append({
            "age": age,
            "from": chart.get("period_start", ""),
            "to":   chart.get("period_end", ""),
            **section,
        })
        if age % 10 == 0:
            print(f"  … age {age} done")

    print(f"  ✓  All annual charts complete.")

    # ── Assemble final output ─────────────────────────────────────────────
    output = {
        "metadata": {
            "name":         client_name,
            "dob":          dob,
            "tob":          tob,
            "place":        place,
            "chart_system": chart_system,
            "annual_basis": annual_basis,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "engine":       "lk-engine-v2.5",
        },
        "natal_chart": natal_section,
        "annual_timeline": timeline,
    }

    # ── Write output ──────────────────────────────────────────────────────
    if not output_path:
        output_path = f"{_safe_filename(client_name)}_lk_predictions.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    return output_path


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║         Lal Kitab Predictive Engine  v2.5               ║")
    print("║    Goswami 1952 — Grammar + Rules + Strength Engine     ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()
    print("  Enter birth details (Ctrl+C to exit at any time)")
    print()

    client_name  = _prompt("Full Name")
    dob          = _prompt("Date of Birth  (YYYY-MM-DD)")
    tob          = _prompt("Time of Birth  (HH:MM, 24h)")
    place        = _prompt("Place of Birth (city, country)")
    chart_system = _prompt("Chart System   (vedic / kp)", default="vedic").lower()
    annual_basis = _prompt("Annual Basis   (vedic / kp)", default=chart_system).lower()

    if not all([client_name, dob, tob, place]):
        print("\nError: all fields are required.")
        sys.exit(1)

    # Validate date/time formats
    try:
        datetime.strptime(dob, "%Y-%m-%d")
    except ValueError:
        print(f"\nError: Date '{dob}' must be in YYYY-MM-DD format.")
        sys.exit(1)
    try:
        datetime.strptime(tob, "%H:%M")
    except ValueError:
        print(f"\nError: Time '{tob}' must be in HH:MM format.")
        sys.exit(1)

    try:
        output_path = run_engine(
            client_name=client_name,
            dob=dob,
            tob=tob,
            place=place,
            chart_system=chart_system,
            annual_basis=annual_basis,
        )
    except Exception as e:
        print(f"\n✗  Engine error: {e}")
        logging.exception("Engine failed")
        sys.exit(1)

    print()
    print("─" * 60)
    print(f"  ✅  Done!  Output → {output_path}")
    print("─" * 60)
    print()
    print("  Load this file into NotebookLM / Gemini for full analysis.")
    print()


if __name__ == "__main__":
    main()
