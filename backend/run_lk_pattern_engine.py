#!/usr/bin/env python3
"""
Lal Kitab Pattern Engine — Main Entry Point
===========================================
Interactive CLI that:
  1. Collects user input (name, DOB, TOB, place)
  2. Builds Natal + 75 Annual charts via ChartGenerator
  3. Runs the newly discovered PATTERN-BASED Engine (Bypasses rules.db)
  4. Saves a structured JSON output mapped to lk_pattern_constants.py logic

Usage:
    cd <project-root>
    PYTHONPATH=backend python backend/run_lk_pattern_engine.py
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
from astroq.lk_prediction.lk_constants import PLANET_PAKKA_GHAR, PLANET_EXALTATION, PLANET_DEBILITATION
from astroq.lk_prediction.lk_pattern_constants import BENEFIC_YIELD_PATTERN, MATURITY_AGE_PATTERN

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.WARNING, format="%(levelname)s  %(name)s: %(message)s")

# ─────────────────────────────────────────────────────────────────────────────
# Pattern Logic Implementations
# ─────────────────────────────────────────────────────────────────────────────
def is_house_dormant(house, occupied_houses):
    if house == 7 and 1 not in occupied_houses: return True
    if house == 8 and 2 not in occupied_houses: return True
    if house == 9 and 3 not in occupied_houses: return True
    if house == 10 and 4 not in occupied_houses: return True
    if house == 11 and 5 not in occupied_houses: return True
    if house == 12 and 6 not in occupied_houses: return True
    return False

def evaluate_pattern_logic(ppos):
    pattern_predictions = []
    occupied_houses = set(ppos.values())
    
    for planet, house in ppos.items():
        if planet == "Lagna": continue
        
        is_dormant = is_house_dormant(house, occupied_houses)
        if planet == "Rahu" and 2 not in occupied_houses: is_dormant = True
            
        is_pakka = house == PLANET_PAKKA_GHAR.get(planet)
        is_uchha = house in PLANET_EXALTATION.get(planet, [])
        is_neech = house in PLANET_DEBILITATION.get(planet, [])
        
        is_doubtful = False
        if planet == "Venus" and house == 4: is_doubtful = True
        if planet == "Sun" and house == 4 and ppos.get("Saturn") == 10: is_doubtful = True
        if planet == "Saturn" and house == 10 and ppos.get("Sun") == 4: is_doubtful = True
            
        is_opposed = False
        for op_planet, op_house in ppos.items():
            if op_planet != planet:
                if house == (op_house + 6) % 12 or house == op_house - 6 or house == op_house + 6:
                    if not (is_uchha and op_house in PLANET_EXALTATION.get(op_planet, [])):
                        is_opposed = True
                        break
                        
        is_bio_planet = planet in ["Sun", "Moon", "Jupiter", "Venus", "Mars"]
        is_bio_house = house in [1, 3, 4, 5, 7, 8, 9]
        
        severity = "MINOR_MALEFIC"
        scoring = "PENALTY"
        fate_bucket = "N/A"
        
        if is_dormant:
            severity = "NEUTRALIZED_DORMANT"
            scoring = "NEUTRAL"
        elif is_doubtful:
            severity = "EXTREME_MALEFIC"
            scoring = "PENALTY"
        elif is_neech or is_opposed:
            severity = "MODERATE_MALEFIC"
            scoring = "PENALTY"
        elif is_uchha or is_pakka:
            severity = "EXTREME_BENEFIC"
            scoring = "BOOST"
            fate_bucket = "BENEFIC_BUILD"
            
        if scoring == "PENALTY":
            if is_bio_planet or is_bio_house: fate_bucket = "TRANSFERENCE_TRAP_BIOLOGICAL"
            else: fate_bucket = "MATERIAL_BLOCK_WEALTH"
            
        maturity_age = MATURITY_AGE_PATTERN["maturity_ages"].get(planet, "Unknown")
        
        # Formulate string to match a fluent, narrative astrological output (Option 3)
        pred_text = f"Astrological Assessment for {planet} in House {house}: "
        
        if scoring == "BOOST":
            yield_data = BENEFIC_YIELD_PATTERN["yield_mapping"].get(house, {})
            lord = yield_data.get("house_lord", "Unknown")
            items = ", ".join(yield_data.get("primary_yields", []))
            pred_text += f"Because {planet} is highly dignified (Exalted or in its Pakka Ghar), the engine predicts an '{severity}' outcome. Structurally, it acts as a Benefic Harvester, capturing the material domain of the House Lord ({lord}) to generate specific yields such as [{items}]. However, adhering to the Chronological Trigger pattern, this peak destiny remains in escrow and will fully unlock once {planet} reaches its maturity at age {maturity_age}."
            
        elif scoring == "PENALTY":
            if fate_bucket == "TRANSFERENCE_TRAP_BIOLOGICAL":
                pred_text += f"Its '{severity}' state activates a 'Biological Transference Trap'. Because {planet} is a life-force karaka or resides in a Foundational House (H{house}), the engine bypasses material losses and routes the karmic penalty to strictly attack the physical health or well-being of its assigned living relative in the Lal Kitab table. This friction enforces a rigid biological sacrifice until the planet reaches maturity at age {maturity_age}, after which it may neutralize. A non-living item substitution remedy is structurally required to lift the trap early."
            else:
                pred_text += f"Its '{severity}' state activates a 'Material Block'. Because {planet} acts as an operational karaka or resides in an Arth/Karma transaction house (H{house}), the engine bypasses biological harm entirely. Instead, the karmic penalty is mathematically routed to attack accumulated wealth, trade, profession, or status. This friction will forcefully limit financial/operational success until {planet} achieves independence at its maturity age of {maturity_age}."
                
        elif scoring == "NEUTRAL":
            pred_text += f"The predictive engine detects a severed activation line (empty trigger houses), plunging {planet} into a 'Dormant' (Soyi Hui) state. Its theoretical power—whether tremendously benefic or malefic—is neutralized and clamped to zero. It will remain asleep until transit-based activation occurs."

        pattern_predictions.append(pred_text)
        
    return pattern_predictions

# ─────────────────────────────────────────────────────────────────────────────
# Helpers & Pipeline execution
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
    natal_chart = payload.get("chart_0")
    annual_charts = []
    for key in sorted(payload.keys()):
        if key == "chart_0" or not key.startswith("chart_"): continue
        c = payload[key]
        if isinstance(c, dict) and c.get("chart_type") == "Yearly":
            annual_charts.append(c)
    return natal_chart, annual_charts

def _build_pattern_section(chart: dict) -> dict:
    # ── Execute pure pattern algorithm ──────────────────────────────────────
    ppos = {p: d["house"] for p, d in chart.get("planets_in_houses", {}).items() if p != "Lagna"}
    predictions = evaluate_pattern_logic(ppos)

    planet_states = {}
    for p_name, h_idx in ppos.items():
        planet_states[p_name] = {"house": h_idx, "states": ["Pattern Calculated"]}

    section = {
        "planet_positions": planet_states,
        "grammar_signals": ["Calculated purely via Structural Meta-Patterns"],
        "significant_aspects": [],
        "predictions": predictions,
    }
    return section

def run_engine(client_name: str, dob: str, tob: str, place: str, chart_system: str="vedic", annual_basis: str="vedic", output_path: str=None) -> str:
    print("\n" + "─" * 60)
    print(f"  Step 1/3  Generating astronomical charts …")
    print("─" * 60)

    generator = ChartGenerator()
    payload = generator.build_full_chart_payload(dob_str=dob, tob_str=tob, place_name=place, chart_system=chart_system, annual_basis=annual_basis)
    natal_chart, annual_charts = _extract_charts(payload)
    if not natal_chart: raise RuntimeError("ChartGenerator returned no natal chart.")
    print(f"  ✓  Natal chart built.  {len(annual_charts)} annual charts generated.")

    print("\n" + "─" * 60)
    print(f"  Step 2/3  Initialising Pattern engine …")
    print("─" * 60)
    print("  Running natal chart …")
    natal_section = _build_pattern_section(natal_chart)
    print(f"  ✓  Natal:  {len(natal_section['predictions'])} pattern predictions generated.")

    print("\n" + "─" * 60)
    print(f"  Step 3/3  Running {len(annual_charts)} annual charts …")
    print("─" * 60)

    timeline = []
    for chart in annual_charts:
        age = chart.get("chart_period", 0)
        section = _build_pattern_section(chart)
        timeline.append({
            "age": age,
            "from": chart.get("period_start", ""),
            "to":   chart.get("period_end", ""),
            **section,
        })
        if age % 10 == 0: print(f"  … age {age} done")

    print(f"  ✓  All annual charts complete.")

    output = {
        "metadata": {
            "name":         client_name,
            "dob":          dob,
            "tob":          tob,
            "place":        place,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "engine":       "lk-pattern-engine-v1.0",
            "pattern_dictionary": {
                "Biological Transference Trap": "A penalty routed strictly to attack physical health or a biological relative. Remedy logic requires substitution of a fixed 'Living' entity with a 'Non-Living' object from the same house mapping.",
                "Material Block": "A penalty that entirely bypasses biology and strictly attacks accumulated wealth, cashflow, career, or status. Governed by material planets (Saturn, Mercury, Rahu, Ketu) or Arth houses.",
                "Chronological Trigger Escrow": "Benefic fate spikes or Malefic Blocks are mathematically escrowed until the triggering planet reaches its defined 35-year Cycle Maturity Age.",
                "Dormant (Soyi Hui)": "Theoretical planet power is completely neutralized to zero because its activation line is severed (the preceding trigger house is empty)."
            }
        },
        "natal_chart": natal_section,
        "annual_timeline": timeline,
    }

    if not output_path:
        output_path = f"{_safe_filename(client_name)}_pattern_predictions.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    return output_path

# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────
def main():
    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║         Lal Kitab Pattern Engine  v1.0                   ║")
    print("║    Abstract Meta-Logic based on Universal LK Patterns    ║")
    print("╚══════════════════════════════════════════════════════════╝\n")

    client_name  = _prompt("Full Name", "Demo Pattern User")
    dob          = _prompt("Date of Birth  (YYYY-MM-DD)", "1990-01-01")
    tob          = _prompt("Time of Birth  (HH:MM, 24h)", "12:00")
    place        = _prompt("Place of Birth (city, country)", "New Delhi")

    try:
        output_path = run_engine(client_name=client_name, dob=dob, tob=tob, place=place)
    except Exception as e:
        print(f"\n✗  Engine error: {e}")
        logging.exception("Pattern Engine failed")
        sys.exit(1)

    print("\n" + "─" * 60)
    print(f"  ✅  Done!  Pattern JSON Output → {output_path}")
    print("─" * 60 + "\n")

if __name__ == "__main__":
    main()
