#!/usr/bin/env python3
"""
run_lk_engine_75yr.py
=====================
Full 75-Year Life Timeline Analysis.
Extends run_lk_engine.py by sweeping all annual charts (age 1–75) through the
VarshphalTimingEngine + Double-Confirmation model to find which life domains
get triggered at each age.

Double-Confirmation logic:
  1. Natal Fate View  → is domain GRAHA_PHAL or RASHI_PHAL at birth?
  2. Varshphal Timing → does the annual chart geometry fire a matching trigger?
  Both must fire for a HIGH-confidence prediction.
  Only annual chart → MEDIUM.
  Only natal promise, no trigger → LOW (exists in chart but timing not ripe).

Output:
  - Year-by-year timeline table (age 1–75)
  - Domain activation heatmap
  - Top predicted years (most simultaneous domain triggers)
  - GP-confirmed events vs RP-conditional events

Usage:
    cd /Users/sachinbadgi/Documents/lal_kitab/astroq-v2/backend

    python run_lk_engine_75yr.py --figure "Amitabh Bachchan"
    python run_lk_engine_75yr.py --figure "MS Dhoni"
    python run_lk_engine_75yr.py --dob 1942-10-11 --tob 16:00 --place "Allahabad, India" --name "Amitabh"
    python run_lk_engine_75yr.py --figure "Amitabh Bachchan" --domains marriage finance career_travel
    python run_lk_engine_75yr.py --figure "Elon Musk" --min-confidence Medium
    python run_lk_engine_75yr.py --figure "Steve Jobs" --json
    python run_lk_engine_75yr.py --list
"""
import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, date

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.natal_fate_view import NatalFateView
from astroq.lk_prediction.varshphal_timing_engine import VarshphalTimingEngine

# ── Geo map ────────────────────────────────────────────────────────────────────
GEO_MAP = {
    "Allahabad, India":                        (25.4358,  81.8463,  "+05:30"),
    "Mumbai, India":                           (19.0760,  72.8777,  "+05:30"),
    "Vadnagar, India":                         (23.7801,  72.6373,  "+05:30"),
    "San Francisco, California, US":           (37.7749,-122.4194,  "-08:00"),
    "Seattle, Washington, US":                 (47.6062,-122.3321,  "-08:00"),
    "Sandringham, Norfolk, UK":                (52.8311,   0.5054,  "+00:00"),
    "New Delhi, India":                        (28.6139,  77.2090,  "+05:30"),
    "Gary, Indiana, US":                       (41.5934, -87.3464,  "-06:00"),
    "Pretoria, South Africa":                  (-25.7479, 28.2293,  "+02:00"),
    "Porbandar, India":                        (21.6417,  69.6293,  "+05:30"),
    "Jamaica Hospital, Queens, New York, US":  (40.7028, -73.8152,  "-05:00"),
    "Honolulu, Hawaii, US":                    (21.3069,-157.8583,  "-10:00"),
    "Mayfair, London, UK":                     (51.5100,  -0.1458,  "+00:00"),
    "Skopje, North Macedonia":                 (42.0003,  21.4280,  "+01:00"),
    "Scranton, Pennsylvania, US":              (41.4090, -75.6624,  "-05:00"),
    "Buckingham Palace, London, UK":           (51.5014,  -0.1419,  "+00:00"),
    "St. Petersburg, Russia":                  (59.9311,  30.3609,  "+03:00"),
    "Hodgenville, KY, USA":                    (37.5737, -85.7411,  "-06:00"),
    "Mvezo, South Africa":                     (-31.9329, 28.9988,  "+02:00"),
    "Aden, Yemen":                             (12.7855,  45.0187,  "+03:00"),
    "Indore, India":                           (22.7196,  75.8577,  "+05:30"),
    "Jamshedpur, India":                       (22.8046,  86.2029,  "+05:30"),
    "Raisen, India":                           (23.3314,  77.7886,  "+05:30"),
    "Madanapalle, India":                      (13.5510,  78.5051,  "+05:30"),
}
DEFAULT_GEO = (28.6139, 77.2090, "+05:30")

# Domains with Varshphal triggers defined
TIMED_DOMAINS = ["marriage", "finance", "health", "career_travel", "progeny"]

# Domain → canonical label map (for display)
DOMAIN_LABEL = {
    "marriage":      "Marriage & Partnerships",
    "finance":       "Finance & Wealth",
    "health":        "Health & Vitality",
    "career_travel": "Career & Travel",
    "progeny":       "Progeny (Children)",
}

# Confidence colours / symbols
CONF_BADGE = {
    "High":   "[ HIGH ✓✓ ]",
    "Medium": "[ MED  ✓  ]",
    "Low":    "[ LOW  ~  ]",
    "None":   "[  --  ✗  ]",
}

CONF_RANK = {"High": 3, "Medium": 2, "Low": 1, "None": 0}

# Fate type → short badge
FATE_BADGE = {
    "GRAHA_PHAL": "GP",
    "RASHI_PHAL": "RP",
    "HYBRID":     "HY",
    "NEITHER":    "--",
}


# ── Helpers ────────────────────────────────────────────────────────────────────
def get_geo(place):
    pl = place.lower()
    for key, val in GEO_MAP.items():
        if key.lower() in pl or pl in key.lower():
            return val
    return DEFAULT_GEO


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


def birth_year(dob: str) -> int:
    return int(dob.split("-")[0])


def age_to_year(dob: str, age: int) -> int:
    return birth_year(dob) + age


# ── Core Analysis ──────────────────────────────────────────────────────────────
def analyse_75_years(
    natal_chart: dict,
    full_payload: dict,
    dob: str,
    fate_entries: list,
    domains: list,
    min_confidence: str = "Low",
) -> list:
    """
    Sweeps ages 1–75, runs VarshphalTimingEngine for each domain,
    applies Double-Confirmation (natal fate × annual trigger).

    Returns list of dicts, one per activated domain-year pair.
    """
    timing_engine = VarshphalTimingEngine()

    # Build natal fate map: domain → fate_type (GP/RP/HY/--)
    # Map canonical domains to event-domain-list keys
    domain_fate_map = {}
    for e in fate_entries:
        domain_fate_map[e["domain"]] = e["fate_type"]

    # Canonical → event-domain-catalogue key mapping
    canonical_map = {
        "marriage":      "marriage",
        "finance":       "wealth",
        "health":        "health",
        "career_travel": "career",
        "progeny":       "progeny",
    }

    results = []
    min_rank = CONF_RANK.get(min_confidence, 1)

    for age in range(1, 76):
        annual_chart = full_payload.get(f"chart_{age}")
        if not annual_chart:
            continue

        period_start = annual_chart.get("period_start", "")
        period_end   = annual_chart.get("period_end", "")
        cal_year     = age_to_year(dob, age)

        for domain in domains:
            # ── Step 1: Varshphal timing check ─────────────────────────────
            timing = timing_engine.get_timing_confidence(natal_chart, annual_chart, age, domain)

            if timing.get("prohibited"):
                continue

            confidence = timing.get("confidence", "Low")
            triggers   = timing.get("triggers", [])
            warnings   = timing.get("warnings", [])

            if not triggers:
                continue  # no trigger fired at all — skip this age/domain

            # ── Step 2: Double-Confirmation — natal fate check ──────────────
            cat_key = canonical_map.get(domain, domain)
            natal_fate = domain_fate_map.get(cat_key, "NEITHER")

            # Compute double-confirmation level
            if natal_fate in ("GRAHA_PHAL", "HYBRID") and confidence == "High":
                dc_level = "DOUBLE_CONFIRMED"
                dc_label = "Double Confirmed ✓✓ (GP + High Trigger)"
            elif natal_fate in ("GRAHA_PHAL", "HYBRID") and confidence == "Medium":
                dc_level = "GP_MEDIUM"
                dc_label = "GP × Medium Trigger  ✓ (likely)"
            elif natal_fate == "RASHI_PHAL" and confidence == "High":
                dc_level = "RP_HIGH"
                dc_label = "RP × High Trigger  ~ (conditional but strong)"
            elif natal_fate == "RASHI_PHAL" and confidence == "Medium":
                dc_level = "RP_MEDIUM"
                dc_label = "RP × Medium Trigger  ~ (conditional)"
            elif confidence == "High":
                dc_level = "TRIGGER_ONLY_HIGH"
                dc_label = "Trigger only (High) — no clear natal promise"
            else:
                dc_level = "TRIGGER_ONLY_MED"
                dc_label = "Trigger only (Medium)"

            if CONF_RANK.get(confidence, 0) < min_rank:
                continue

            results.append({
                "age":          age,
                "calendar_year": cal_year,
                "period":       f"{period_start} – {period_end}",
                "domain":       domain,
                "domain_label": DOMAIN_LABEL.get(domain, domain),
                "natal_fate":   natal_fate,
                "confidence":   confidence,
                "dc_level":     dc_level,
                "dc_label":     dc_label,
                "triggers":     triggers,
                "warnings":     warnings,
            })

    return results


# ── Rendering ──────────────────────────────────────────────────────────────────
def render(name, dob, tob, place, natal_chart, fate_entries, timeline, domains):
    W   = 118
    SEP = "═" * W
    THN = "─" * W

    planets = {p: d.get("house") for p, d in natal_chart.get("planets_in_houses", {}).items()}
    planet_line = "  ".join(f"{p}→H{h}" for p, h in sorted(planets.items(), key=lambda x: x[1] or 0))

    print()
    print(SEP)
    print(f"  LAL KITAB — 75-YEAR DOUBLE CONFIRMATION TIMELINE")
    print(f"  {name}  │  DOB: {dob}  TOB: {tob}  │  {place}")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(SEP)

    # ── Natal chart ────────────────────────────────────────────────────────────
    print(f"\n  ◈ NATAL CHART")
    print(f"  {THN}")
    print(f"  {planet_line}")

    # ── Natal fate for timing domains ──────────────────────────────────────────
    canonical_map = {
        "marriage": "marriage", "finance": "wealth",
        "health": "health", "career_travel": "career", "progeny": "progeny",
    }
    fate_map = {e["domain"]: e["fate_type"] for e in fate_entries}
    print(f"\n  ◈ NATAL FATE VIEW — TIMED DOMAINS")
    print(f"  {THN}")
    for d in domains:
        cat_key = canonical_map.get(d, d)
        ft = fate_map.get(cat_key, "NEITHER")
        badge = FATE_BADGE.get(ft, "--")
        label = DOMAIN_LABEL.get(d, d)
        print(f"  [{badge}]  {label}")

    # ── Summary stats ──────────────────────────────────────────────────────────
    dc = [r for r in timeline if r["dc_level"] == "DOUBLE_CONFIRMED"]
    gp_med = [r for r in timeline if r["dc_level"] == "GP_MEDIUM"]
    rp_high = [r for r in timeline if r["dc_level"] == "RP_HIGH"]
    other = [r for r in timeline if r["dc_level"] not in ("DOUBLE_CONFIRMED","GP_MEDIUM","RP_HIGH")]

    print(f"\n  ◈ ACTIVATION SUMMARY  ({len(timeline)} total domain-year triggers across 75 years)")
    print(f"  {THN}")
    print(f"  Double Confirmed (GP + High)    : {len(dc):>4}  — hardest natal promises + annual trigger")
    print(f"  GP × Medium trigger             : {len(gp_med):>4}  — natal promise + partial annual signal")
    print(f"  RP × High trigger               : {len(rp_high):>4}  — strong annual trigger, conditional promise")
    print(f"  Other activations               : {len(other):>4}  — trigger-only, no strong natal backing")

    # ── Domain activation count ────────────────────────────────────────────────
    print(f"\n  ◈ DOMAIN ACTIVATION COUNTS")
    print(f"  {THN}")
    domain_counts = defaultdict(int)
    for r in timeline:
        domain_counts[r["domain"]] += 1
    for d in domains:
        print(f"  {DOMAIN_LABEL.get(d,d):<35} : {domain_counts[d]:>3} active years out of 75")

    # ── Year-by-year timeline ──────────────────────────────────────────────────
    print(f"\n\n  ◈ YEAR-BY-YEAR ACTIVATION TIMELINE")
    print(f"  {THN}")
    print(f"  {'Age':>4}  {'Year':>5}  {'Domain':<22}  {'Fate':>4}  {'Conf':<8}  {'DC Level':<35}  Trigger")
    print(f"  {'─'*4}  {'─'*5}  {'─'*22}  {'─'*4}  {'─'*8}  {'─'*35}  {'─'*30}")

    prev_age = None
    for r in sorted(timeline, key=lambda x: (x["age"], x["domain"])):
        age_str = f"{r['age']:>4}" if r["age"] != prev_age else "    "
        year_str = f"{r['calendar_year']:>5}" if r["age"] != prev_age else "     "
        prev_age = r["age"]
        fate_b  = FATE_BADGE.get(r["natal_fate"], "--")
        conf    = r["confidence"]
        trig_0  = r["triggers"][0][:48] if r["triggers"] else ""
        print(f"  {age_str}  {year_str}  {r['domain_label']:<22}  [{fate_b}]  {conf:<8}  {r['dc_label']:<35}  {trig_0}")
        for trig in r["triggers"][1:]:
            print(f"  {'':>4}  {'':>5}  {'':22}  {'':4}  {'':8}  {'':35}  {trig[:48]}")
        if r["warnings"]:
            for w in r["warnings"][:1]:
                print(f"  {'':>4}  {'':>5}  {'':22}  ⚠ {w[:60]}")

    # ── Top active years ───────────────────────────────────────────────────────
    year_counts: dict[int, list] = defaultdict(list)
    for r in timeline:
        year_counts[r["age"]].append(r)

    ranked_years = sorted(year_counts.items(), key=lambda x: -len(x[1]))

    print(f"\n\n  ◈ TOP ACTIVE YEARS  (most simultaneous domain triggers)")
    print(f"  {THN}")
    print(f"  {'Age':>4}  {'Year':>5}  {'Triggers':>8}  Domains")
    print(f"  {'─'*4}  {'─'*5}  {'─'*8}  {'─'*50}")
    for age, hits in ranked_years[:15]:
        cal_year = age_to_year(dob, age)
        doms = ", ".join(DOMAIN_LABEL.get(r["domain"], r["domain"])[:14] for r in hits)
        high = sum(1 for r in hits if r["dc_level"] == "DOUBLE_CONFIRMED")
        flag = " ← Double Confirmed!" if high >= 2 else (" ← GP confirmed" if high >= 1 else "")
        print(f"  {age:>4}  {cal_year:>5}  {len(hits):>8}  {doms}{flag}")

    # ── Double-confirmed events ────────────────────────────────────────────────
    if dc:
        print(f"\n\n  ◈ DOUBLE-CONFIRMED EVENTS  (Graha Phal natal promise + High annual trigger)")
        print(f"  {THN}")
        for r in dc:
            print(f"  Age {r['age']:>2} ({r['calendar_year']})  {r['domain_label']:<25}  {r['triggers'][0][:60]}")

    print(f"\n{'═'*W}\n")


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Lal Kitab — 75-Year Double-Confirmation Timeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_lk_engine_75yr.py --figure "Amitabh Bachchan"
  python run_lk_engine_75yr.py --figure "MS Dhoni"
  python run_lk_engine_75yr.py --figure "Amitabh Bachchan" --domains marriage finance
  python run_lk_engine_75yr.py --figure "Elon Musk" --min-confidence Medium
  python run_lk_engine_75yr.py --dob 1942-10-11 --tob 16:00 --place "Allahabad, India" --name "Amitabh"
  python run_lk_engine_75yr.py --figure "Steve Jobs" --json
  python run_lk_engine_75yr.py --list
        """,
    )
    parser.add_argument("--figure",         type=str)
    parser.add_argument("--name",           type=str, default="Custom Chart")
    parser.add_argument("--dob",            type=str)
    parser.add_argument("--tob",            type=str, default="12:00")
    parser.add_argument("--place",          type=str, default="New Delhi, India")
    parser.add_argument("--domains",        nargs="*", choices=TIMED_DOMAINS,
                        default=TIMED_DOMAINS,
                        help=f"Domains to analyse (default: all). Choices: {TIMED_DOMAINS}")
    parser.add_argument("--min-confidence", choices=["Low","Medium","High"], default="Low",
                        help="Minimum confidence level to include (default: Low)")
    parser.add_argument("--json",           action="store_true")
    parser.add_argument("--list",           action="store_true")
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

    # Build charts
    tob_full = tob + ":00" if len(tob) == 5 else tob
    lat, lon, tz = get_geo(place)
    print(f"\n  Building 75-year chart payload for {name} ({dob} {tob}, {place})...")
    gen = ChartGenerator()
    try:
        full_payload = gen.build_full_chart_payload(
            dob_str=dob, tob_str=tob_full, place_name=place,
            latitude=lat, longitude=lon, utc_string=tz, chart_system="vedic",
        )
    except Exception as e:
        print(f"\n❌  Chart generation failed: {e}\n"); sys.exit(1)

    natal_chart = full_payload.get("chart_0")
    if not natal_chart:
        print("\n❌  No natal chart (chart_0) in payload.\n"); sys.exit(1)

    # Domain fate view (for double-confirmation)
    print("  Running natal fate classification...")
    view = NatalFateView()
    fate_entries = view.evaluate(natal_chart, categories=["canonical"])

    # 75-year sweep
    print(f"  Sweeping ages 1–75 across {len(args.domains)} domains...")
    timeline = analyse_75_years(
        natal_chart=natal_chart,
        full_payload=full_payload,
        dob=dob,
        fate_entries=fate_entries,
        domains=args.domains,
        min_confidence=args.min_confidence,
    )
    print(f"  Found {len(timeline)} domain-year activations.\n")

    if args.json:
        print(json.dumps({
            "name": name, "dob": dob, "tob": tob, "place": place,
            "planets": {p: d.get("house") for p, d in natal_chart.get("planets_in_houses",{}).items()},
            "natal_fate": {e["domain"]: e["fate_type"] for e in fate_entries},
            "timeline": timeline,
        }, indent=2))
    else:
        render(name, dob, tob, place, natal_chart, fate_entries, timeline, args.domains)


if __name__ == "__main__":
    main()
