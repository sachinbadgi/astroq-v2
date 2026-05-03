#!/usr/bin/env python3
"""
run_lk_engine.py
================
Full Lal Kitab Engine Runner.
Takes birth data as input → builds natal chart → runs the full prediction
pipeline (rules engine + grammar + varshphal timing) → produces the Domain
Fate Report for the created chart.

Two modes:
  NATAL    — analyses the birth chart alone (default)
  ANNUAL   -- also runs the engine for a specific age year

Usage:
    cd /Users/sachinbadgi/Documents/lal_kitab/astroq-v2/backend

    # Known figure
    python run_lk_engine.py --figure "Amitabh Bachchan"
    python run_lk_engine.py --figure "MS Dhoni" --no-neither

    # Custom birth data
    python run_lk_engine.py --dob 1942-10-11 --tob 16:00 --place "Allahabad, India" --name "Amitabh"

    # With annual analysis at age 40
    python run_lk_engine.py --figure "Amitabh Bachchan" --age 40

    # Domain-only (skip rule engine predictions)
    python run_lk_engine.py --figure "Vladimir Putin" --domain-only

    # JSON output
    python run_lk_engine.py --figure "Steve Jobs" --json

    # JSON output WITH full natal chart + all 75 annual chart positions
    python run_lk_engine.py --figure "Steve Jobs" --json --charts
    python run_lk_engine.py --dob 1977-11-28 --tob 18:30 --place "Sangli, India" --name sachin --charts

    # List all known figures
    python run_lk_engine.py --list
"""
import argparse
import io
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from astroq.lk_prediction.engine_runner import LKEngineRunner

CAT_ORDER = [
    "canonical", "career_tech", "finance", "home_lifestyle",
    "health_wellness", "tech_infra", "modern_finance", "sustainable", "social_psych",
]
CAT_LABELS = {
    "canonical":      "CANONICAL DOMAINS",
    "career_tech":    "CAREER & TECHNOLOGY",
    "finance":        "FINANCE & INVESTMENTS",
    "home_lifestyle": "HOME, LIFESTYLE & SUSTAINABILITY",
    "health_wellness":"HEALTH & WELLNESS",
    "tech_infra":     "TECHNOLOGY & DIGITAL INFRASTRUCTURE",
    "modern_finance": "MODERN FINANCE",
    "sustainable":    "SUSTAINABLE INNOVATION",
    "social_psych":   "SOCIAL & PSYCHOLOGICAL",
}
BADGE = {
    "GRAHA_PHAL": "[ GP ✓ ]",
    "RASHI_PHAL": "[ RP ~ ]",
    "HYBRID":     "[ HY ⊕ ]",
    "NEITHER":    "[  --  ]",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_figures():
    path = os.path.join(ROOT, "data", "public_figures_ground_truth.json")
    return json.load(open(path)) if os.path.exists(path) else []


def find_figure(name, figures):
    nl = name.lower()
    for fig in figures:
        if fig.get("name","").lower() == nl: return fig
    for fig in figures:
        if nl in fig.get("name","").lower(): return fig
    return None


# ── Rendering ─────────────────────────────────────────────────────────────────
def render(name, dob, tob, place, natal, fate_entries, rule_preds,
           annual_preds, age, include_neither):
    W = 112
    SEP  = "═" * W
    THIN = "─" * W

    planets = {p: d.get("house") for p, d in natal.get("planets_in_houses", {}).items()}
    planet_line = "  ".join(f"{p}→H{h}" for p, h in sorted(planets.items(), key=lambda x: x[1] or 0))

    gp = [e for e in fate_entries if e["fate_type"] == "GRAHA_PHAL"]
    rp = [e for e in fate_entries if e["fate_type"] == "RASHI_PHAL"]
    hy = [e for e in fate_entries if e["fate_type"] == "HYBRID"]
    ni = [e for e in fate_entries if e["fate_type"] == "NEITHER"]
    total = len(fate_entries)

    print()
    print(SEP)
    print(f"  LAL KITAB ENGINE — FULL CHART ANALYSIS")
    print(f"  {name}  │  DOB: {dob}  TOB: {tob}  │  {place}")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(SEP)

    # ── Natal positions ───────────────────────────────────────────────────────
    print(f"\n  ◈ NATAL CHART POSITIONS")
    print(f"  {THIN}")
    print(f"  {planet_line}\n")

    # ── Rule engine predictions ───────────────────────────────────────────────
    if rule_preds is not None:
        benefic = [p for p in rule_preds if p.polarity.lower() == "benefic"]
        malefic = [p for p in rule_preds if p.polarity.lower() == "malefic"]
        print(f"  ◈ NATAL RULE ENGINE — {len(rule_preds)} PREDICTIONS  "
              f"(+{len(benefic)} benefic  −{len(malefic)} malefic)")
        print(f"  {THIN}")
        for p in sorted(rule_preds, key=lambda x: -x.magnitude)[:20]:
            pol = "✓" if p.polarity == "benefic" else "✗"
            print(f"  [{pol}] [{p.domain:<14}]  mag={p.magnitude:>5.2f}  {p.prediction_text[:70]}")
        if len(rule_preds) > 20:
            print(f"  ... ({len(rule_preds)-20} more)")
        print()

    # ── Annual predictions ────────────────────────────────────────────────────
    if annual_preds is not None and age:
        print(f"\n  ◈ ANNUAL CHART — AGE {age} ENGINE PREDICTIONS  ({len(annual_preds)} hits)")
        print(f"  {THIN}")
        for p in sorted(annual_preds, key=lambda x: -x.magnitude)[:15]:
            pol = "✓" if p.polarity.lower() == "benefic" else "✗"
            tc  = f"[{p.timing_confidence.upper()}]" if p.timing_confidence else ""
            print(f"  [{pol}] {tc:<8} [{p.domain:<14}]  {p.prediction_text[:65]}")
            for sig in p.timing_signals[:2]:
                print(f"         ↳ {sig[:80]}")
        print()

    # ── Fate distribution ─────────────────────────────────────────────────────
    bar = 52
    print(f"  ◈ DOMAIN FATE DISTRIBUTION  ({total} domains)")
    print(f"  {THIN}")
    print(f"  GP ✓  Graha Phal  (Fixed Fate)    : {len(gp):>3}  ({len(gp)/total*100:>5.1f}%)  {'█'*round(len(gp)/total*bar)}")
    print(f"  RP ~  Rashi Phal  (Conditional)   : {len(rp):>3}  ({len(rp)/total*100:>5.1f}%)  {'▒'*round(len(rp)/total*bar)}")
    print(f"  HY ⊕  Hybrid      (Mixed)          : {len(hy):>3}  ({len(hy)/total*100:>5.1f}%)  {'░'*round(len(hy)/total*bar)}")
    print(f"  --    Neither     (Absent)         : {len(ni):>3}  ({len(ni)/total*100:>5.1f}%)  {'·'*round(len(ni)/total*bar)}")

    # ── Full domain table ─────────────────────────────────────────────────────
    print(f"\n\n  ◈ FULL DOMAIN CLASSIFICATION  (56 domains)")
    print(f"  {THIN}")
    print(f"  {'Badge':<10}  {'Domain':<45}  {'Planet Dignity':<50}")
    print(f"  {'─'*10}  {'─'*45}  {'─'*50}")

    by_cat = defaultdict(list)
    for e in fate_entries:
        by_cat[e["category"]].append(e)

    for cat in CAT_ORDER:
        cat_entries = by_cat.get(cat, [])
        if not cat_entries:
            continue
        print(f"\n  ▸ {CAT_LABELS.get(cat, cat)}")
        for e in cat_entries:
            if not include_neither and e["fate_type"] == "NEITHER":
                continue
            badge  = BADGE.get(e["fate_type"], "[  ?? ]")
            dignity = ", ".join(
                f"{p}:{d}" for p, d in e["dignity_details"].items()
                if d and "Absent" not in d and "Off-domain" not in d
            )
            print(f"  {badge}  {e['label']:<45}  {dignity[:50]}")

    # ── GP summary ────────────────────────────────────────────────────────────
    if gp:
        print(f"\n\n  {'─'*W}")
        print(f"  GRAHA PHAL — {len(gp)} FIXED FATE DOMAINS  ✓ Hard-wired natal promises")
        print(f"  {'─'*W}")
        for e in gp:
            dignity = ", ".join(
                f"{p}:{d}" for p, d in e["dignity_details"].items()
                if d and "Absent" not in d and "Off-domain" not in d
            )
            evid = e["evidence"][0][:45] if e["evidence"] else ""
            print(f"  [ GP ✓ ]  {e['label']:<45}  {dignity:<40}  → {evid}")

    # ── RP summary ────────────────────────────────────────────────────────────
    if rp:
        print(f"\n\n  {'─'*W}")
        print(f"  RASHI PHAL — {len(rp)} CONDITIONAL DOMAINS  ~ Need annual chart geometry to activate")
        print(f"  {'─'*W}")
        for e in rp:
            dignity = ", ".join(
                f"{p}:{d}" for p, d in e["dignity_details"].items()
                if d and "Absent" not in d and "Off-domain" not in d
            )
            print(f"  [ RP ~ ]  {e['label']:<45}  {dignity}")

    print(f"\n{'═'*W}\n")


# ── Auto-save ─────────────────────────────────────────────────────────────────

def _safe_filename(name: str) -> str:
    """Convert a person's name to a safe filename slug."""
    slug = re.sub(r"[^\w\s-]", "", name).strip()
    slug = re.sub(r"[\s]+", "_", slug)
    return slug


def _build_natal_chart_json(natal: dict) -> dict:
    """Serialise the full natal chart with per-planet detail."""
    planets_detail = {}
    for planet, data in natal.get("planets_in_houses", {}).items():
        planets_detail[planet] = {
            "house":       data.get("house"),
            "house_natal": data.get("house_natal", data.get("house")),
            "states":      data.get("states", []),
        }
    return {
        "chart_type":   natal.get("chart_type", "Birth"),
        "chart_system": natal.get("chart_system", "vedic"),
        "birth_time":   natal.get("birth_time", ""),
        "planets":      planets_detail,
    }


def _build_annual_charts_json(full_payload: dict) -> dict:
    """
    Serialise all annual charts (age 1-75) from the full payload.
    Supports both raw chart_N payloads and enriched annual_timeline payloads.
    """
    annual = {}
    
    # Check if this is an enriched payload from the pipeline
    timeline = full_payload.get("annual_timeline")
    if timeline and isinstance(timeline, list):
        for entry in timeline:
            age = entry.get("age")
            if age is not None:
                annual[str(age)] = {
                    "period_start": entry.get("from", ""),
                    "period_end":   entry.get("to", ""),
                    "planets":      {p: {"house": h} for p, h in entry.get("chart", {}).items()},
                    "logic":        entry.get("logic", []),
                    "forensic_machine_ledger": entry.get("forensic_machine_ledger", {})
                }
        return annual

    # Fallback to raw chart_N keys
    for age in range(1, 76):
        key = f"chart_{age}"
        chart = full_payload.get(key)
        if not chart:
            continue
        planets = {}
        for planet, data in chart.get("planets_in_houses", {}).items():
            planets[planet] = {
                "house":  data.get("house"),
                "states": data.get("states", []),
            }
        annual[str(age)] = {
            "period_start": chart.get("period_start", ""),
            "period_end":   chart.get("period_end", ""),
            "planets":      planets,
            "logic":        chart.get("logic", []),
            "forensic_machine_ledger": chart.get("forensic_machine_ledger", {})
        }
    return annual


def save_chart(
    name: str, dob: str, tob: str, place: str,
    natal: dict, fate_entries: list, rule_preds, annual_preds,
    age, include_neither: bool,
    full_payload: dict | None = None,
    include_charts: bool = False,
):
    """
    Write the chart output to backend/output/<slug>_<date>.txt  (plain text)
    and                         backend/output/<slug>_<date>.json (structured).
    Returns the paths of the two saved files.

    Parameters
    ----------
    full_payload : dict | None
        The complete chart payload (chart_0 + chart_1..chart_75).  Required
        when include_charts=True.
    include_charts : bool
        When True, the JSON will include ``natal_chart`` (full planet detail)
        and ``annual_charts`` (positions for all 75 years).
    """
    output_dir = os.path.join(ROOT, "output")
    os.makedirs(output_dir, exist_ok=True)

    slug = _safe_filename(name)
    date_tag = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    base = os.path.join(output_dir, f"{slug}_{date_tag}")

    # ── Text report ──────────────────────────────────────────────────────────
    buf = io.StringIO()
    _old_stdout = sys.stdout
    sys.stdout = buf
    try:
        render(name, dob, tob, place, natal, fate_entries, rule_preds,
               annual_preds, age, include_neither=include_neither)
    finally:
        sys.stdout = _old_stdout
    txt_path = base + ".txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(buf.getvalue())

    # ── JSON report ──────────────────────────────────────────────────────────
    planets = {p: d.get("house") for p, d in natal.get("planets_in_houses", {}).items()}
    gp = [e for e in fate_entries if e["fate_type"] == "GRAHA_PHAL"]
    rp = [e for e in fate_entries if e["fate_type"] == "RASHI_PHAL"]
    hy = [e for e in fate_entries if e["fate_type"] == "HYBRID"]
    ni = [e for e in fate_entries if e["fate_type"] == "NEITHER"]
    out = {
        "meta": {
            "name": name, "dob": dob, "tob": tob, "place": place,
            "generated_at": datetime.now().isoformat(),
        },
        "natal_positions": planets,
        "fate_stats": {
            "GRAHA_PHAL": len(gp), "RASHI_PHAL": len(rp),
            "HYBRID": len(hy), "NEITHER": len(ni), "total": len(fate_entries),
        },
        "domain_fate_view": fate_entries,
        "rule_predictions": [
            {"domain": p.domain, "polarity": p.polarity, "magnitude": round(p.magnitude, 3), "text": p.prediction_text}
            for p in (rule_preds or [])
        ],
        "annual_predictions": [
            {
                "domain": p.domain, 
                "polarity": p.polarity, 
                "magnitude": round(p.magnitude, 3), 
                "confidence": p.timing_confidence,
                "text": p.prediction_text,
                "signals": p.timing_signals
            }
            for p in (annual_preds or [])
        ] if age else None,
    }

    if include_charts and full_payload:
        out["natal_chart"]    = _build_natal_chart_json(natal)
        out["annual_charts"]  = _build_annual_charts_json(full_payload)

    json_path = base + ".json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    return txt_path, json_path


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Lal Kitab Full Engine — Chart + Predictions + Domain Fate Report",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_lk_engine.py --figure "Amitabh Bachchan"
  python run_lk_engine.py --figure "MS Dhoni" --no-neither
  python run_lk_engine.py --figure "Amitabh Bachchan" --age 40
  python run_lk_engine.py --dob 1942-10-11 --tob 16:00 --place "Allahabad, India" --name "Amitabh"
  python run_lk_engine.py --figure "Vladimir Putin" --domain-only
  python run_lk_engine.py --figure "Steve Jobs" --json
  python run_lk_engine.py --list
        """,
    )
    parser.add_argument("--figure",      type=str)
    parser.add_argument("--name",        type=str, default="Custom Chart")
    parser.add_argument("--dob",         type=str)
    parser.add_argument("--tob",         type=str, default="12:00")
    parser.add_argument("--place",       type=str, default="New Delhi, India")
    parser.add_argument("--age",         type=int, default=None, help="Run annual chart for this age too")
    parser.add_argument("--no-neither",  action="store_true")
    parser.add_argument("--domain-only", action="store_true", help="Skip rule engine, only domain fate view")
    parser.add_argument("--json",        action="store_true")
    parser.add_argument("--charts",      action="store_true",
                        help="Include full natal + annual (1-75) chart planet positions in JSON output")
    parser.add_argument("--list",        action="store_true")
    args = parser.parse_args()

    figures = load_figures()

    if args.list:
        print(f"\n{'─'*65}")
        print(f"  {'#':>3}  {'Name':<30}  {'DOB':<12}  Place")
        print(f"{'─'*65}")
        for i, f in enumerate(figures, 1):
            print(f"  {i:>3}  {f['name']:<30}  {f['dob']:<12}  {f.get('birth_place','?')[:25]}")
        print(); sys.exit(0)

    # Resolve birth data
    if args.figure:
        fig = find_figure(args.figure, figures)
        if not fig:
            print(f"\n❌  '{args.figure}' not found. Use --list.\n"); sys.exit(1)
        name, dob, tob, place = fig["name"], fig["dob"], fig.get("tob","12:00"), fig.get("birth_place","New Delhi, India")
    elif args.dob:
        name, dob, tob, place = args.name, args.dob, args.tob, args.place
    else:
        print("\n  Enter birth details:")
        name  = input("  Name      : ").strip() or "Custom"
        dob   = input("  DOB (YYYY-MM-DD): ").strip()
        tob   = input("  TOB (HH:MM)     : ").strip() or "12:00"
        place = input("  Place           : ").strip() or "New Delhi, India"

    print(f"\n  Building natal chart for {name} ({dob} {tob}, {place})...",
          file=sys.stderr if args.json else sys.stdout)
    
    db_path = os.path.join(ROOT, "data", "rules.db")
    cfg_file = os.path.join(ROOT, "data", "model_defaults.json")
    
    runner = LKEngineRunner(db_path, cfg_file)
    try:
        results = runner.run(
            dob=dob,
            tob=tob,
            place=place,
            age=args.age,
            domain_only=args.domain_only,
            include_neither=not args.no_neither
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n❌  {e}\n"); sys.exit(1)

    if results.get("pipeline_error"):
        _out = sys.stderr if args.json else sys.stdout
        print(f"  ⚠️  Rule engine error: {results['pipeline_error']} — continuing with domain fate only.", file=_out)

    natal = results["natal_chart"]
    full_payload = results["full_payload"]
    fate_entries = results["fate_entries"]
    rule_preds = results["rule_predictions"]
    annual_preds = results["annual_predictions"]

    # ── Output ────────────────────────────────────────────────────────────────
    include_neither = not args.no_neither

    if args.json:
        planets = {p: d.get("house") for p, d in natal.get("planets_in_houses", {}).items()}
        out = {
            "name": name, "dob": dob, "tob": tob, "place": place,
            "planets": planets,
            "fate_stats": {
                "GP": sum(1 for e in fate_entries if e["fate_type"] == "GRAHA_PHAL"),
                "RP": sum(1 for e in fate_entries if e["fate_type"] == "RASHI_PHAL"),
                "HY": sum(1 for e in fate_entries if e["fate_type"] == "HYBRID"),
                "NI": sum(1 for e in fate_entries if e["fate_type"] == "NEITHER"),
                "total": len(fate_entries),
            },
            "domain_fate_view": fate_entries,
            "rule_predictions": [
                {"domain": p.domain, "polarity": p.polarity,
                 "magnitude": round(p.magnitude, 3), "text": p.prediction_text}
                for p in (rule_preds or [])
            ],
            "annual_predictions": [
                {
                    "domain": p.domain, 
                    "polarity": p.polarity, 
                    "magnitude": round(p.magnitude, 3), 
                    "confidence": p.timing_confidence,
                    "text": p.prediction_text,
                    "signals": p.timing_signals
                }
                for p in (annual_preds or [])
            ] if args.age else None,
        }
        if args.charts:
            out["natal_chart"]   = _build_natal_chart_json(natal)
            out["annual_charts"] = _build_annual_charts_json(full_payload)
        print(json.dumps(out, indent=2))
    else:
        render(name, dob, tob, place, natal, fate_entries, rule_preds,
               annual_preds, args.age, include_neither=include_neither)

    # ── Auto-save (always runs, regardless of --json flag) ────────────────────
    txt_path, json_path = save_chart(
        name, dob, tob, place, natal, fate_entries, rule_preds,
        annual_preds, args.age, include_neither=include_neither,
        full_payload=full_payload,
        include_charts=args.charts,
    )
    _out = sys.stderr if args.json else sys.stdout
    print(f"  [saved]  {txt_path}", file=_out)
    print(f"  [saved]  {json_path}\n", file=_out)


if __name__ == "__main__":
    main()
