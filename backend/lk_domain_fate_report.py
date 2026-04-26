#!/usr/bin/env python3
"""
lk_domain_fate_report.py
========================
Dedicated script — produces a full Domain Fate Report for a single natal chart.
Classifies all 56 life domains (13 canonical + 43 modern) as:
  GP ✓  Graha Phal  — Fixed Fate (promise hard-wired at birth)
  RP ~  Rashi Phal  — Conditional (requires annual chart to activate)
  HY ⊕  Hybrid      — Both signals present
  --    Neither     — Domain structurally absent from this chart

Usage:
    cd /Users/sachinbadgi/Documents/lal_kitab/astroq-v2/backend

    # Known public figure
    python lk_domain_fate_report.py --figure "MS Dhoni"
    python lk_domain_fate_report.py --figure "Amitabh Bachchan"

    # Custom birth data
    python lk_domain_fate_report.py --dob 1942-10-11 --tob 16:00 --place "Allahabad, India" --name "Amitabh"

    # Filter options
    python lk_domain_fate_report.py --figure "Steve Jobs" --categories canonical finance tech_infra
    python lk_domain_fate_report.py --figure "Vladimir Putin" --no-neither
    python lk_domain_fate_report.py --figure "Elon Musk" --gp-only
    python lk_domain_fate_report.py --figure "Ratan Tata"  --rp-only

    # JSON output (LLM / pipeline ready)
    python lk_domain_fate_report.py --figure "MS Dhoni" --json

    # List all known figures
    python lk_domain_fate_report.py --list
"""
import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.natal_fate_view import NatalFateView

# ── Geo map ───────────────────────────────────────────────────────────────────
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


def get_geo(place: str):
    pl = place.lower()
    for key, val in GEO_MAP.items():
        if key.lower() in pl or pl in key.lower():
            return val
    return DEFAULT_GEO


def load_figures():
    path = os.path.join(ROOT, "data", "public_figures_ground_truth.json")
    return json.load(open(path)) if os.path.exists(path) else []


def find_figure(name: str, figures: list):
    nl = name.lower()
    for fig in figures:
        if fig.get("name", "").lower() == nl:
            return fig
    for fig in figures:
        if nl in fig.get("name", "").lower():
            return fig
    return None


def build_chart(dob: str, tob: str, place: str) -> dict:
    tob_full = tob + ":00" if len(tob) == 5 else tob
    lat, lon, tz = get_geo(place)
    gen = ChartGenerator()
    payload = gen.build_full_chart_payload(
        dob_str=dob, tob_str=tob_full, place_name=place,
        latitude=lat, longitude=lon, utc_string=tz, chart_system="vedic",
    )
    natal = payload.get("chart_0")
    if natal is None:
        raise RuntimeError("Chart generation failed — no chart_0 returned")
    return natal


def print_report(name, dob, tob, place, natal, entries, include_neither, gp_only, rp_only):
    W = 112
    planets = {p: d.get("house") for p, d in natal.get("planets_in_houses", {}).items()}
    planet_line = "  ".join(f"{p}→H{h}" for p, h in sorted(planets.items(), key=lambda x: x[1] or 0))

    gp = [e for e in entries if e["fate_type"] == "GRAHA_PHAL"]
    rp = [e for e in entries if e["fate_type"] == "RASHI_PHAL"]
    hy = [e for e in entries if e["fate_type"] == "HYBRID"]
    ni = [e for e in entries if e["fate_type"] == "NEITHER"]
    total = len(entries)

    print()
    print("═" * W)
    print(f"  LAL KITAB — DOMAIN FATE REPORT")
    print(f"  {name}  │  DOB: {dob}  TOB: {tob}  │  {place}")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("═" * W)

    # Natal positions
    print(f"\n  NATAL CHART POSITIONS")
    print(f"  {'─'*W}")
    print(f"  {planet_line}\n")

    # Fate bar
    bar_len = 56
    gp_n = round(len(gp) / total * bar_len) if total else 0
    rp_n = round(len(rp) / total * bar_len) if total else 0
    hy_n = round(len(hy) / total * bar_len) if total else 0
    ni_n = bar_len - gp_n - rp_n - hy_n

    print(f"  FATE DISTRIBUTION  ({total} domains)")
    print(f"  {'─'*W}")
    print(f"  GP ✓  Graha Phal  (Fixed Fate)    : {len(gp):>3}  ({len(gp)/total*100:>5.1f}%)  {'█'*gp_n}")
    print(f"  RP ~  Rashi Phal  (Conditional)   : {len(rp):>3}  ({len(rp)/total*100:>5.1f}%)  {'▒'*rp_n}")
    print(f"  HY ⊕  Hybrid      (Mixed Signals)  : {len(hy):>3}  ({len(hy)/total*100:>5.1f}%)  {'░'*hy_n}")
    print(f"  --    Neither     (Absent)         : {len(ni):>3}  ({len(ni)/total*100:>5.1f}%)  {'·'*max(ni_n,0)}")

    # Filtered view
    if gp_only:
        _print_section("GRAHA PHAL — FIXED FATE DOMAINS", gp, W, show_evidence=True)
    elif rp_only:
        _print_section("RASHI PHAL — CONDITIONAL DOMAINS", rp, W, show_evidence=True)
    else:
        # Full domain table grouped by category
        print(f"\n\n  FULL DOMAIN CLASSIFICATION")
        print(f"  {'─'*W}")
        print(f"  {'Badge':<10}  {'Domain':<45}  {'Planet Dignity':<50}")
        print(f"  {'─'*10}  {'─'*45}  {'─'*50}")

        by_cat = defaultdict(list)
        for e in entries:
            by_cat[e["category"]].append(e)

        for cat in CAT_ORDER:
            cat_entries = by_cat.get(cat, [])
            if not cat_entries:
                continue
            print(f"\n  ▸ {CAT_LABELS.get(cat, cat)}")
            for e in cat_entries:
                if not include_neither and e["fate_type"] == "NEITHER":
                    continue
                badge = BADGE.get(e["fate_type"], "[  ?? ]")
                dignity = ", ".join(
                    f"{p}:{d}" for p, d in e["dignity_details"].items()
                    if d and "Absent" not in d and "Off-domain" not in d
                )
                print(f"  {badge}  {e['label']:<45}  {dignity[:50]}")

        # GP summary
        if gp:
            _print_section(f"GRAHA PHAL — {len(gp)} FIXED FATE DOMAINS  ✓", gp, W, show_evidence=True)

        # RP summary
        if rp:
            _print_section(f"RASHI PHAL — {len(rp)} CONDITIONAL DOMAINS  ~ (need annual chart)", rp, W, show_evidence=False)

    print(f"\n{'═'*W}\n")


def _print_section(title, entries, W, show_evidence=False):
    print(f"\n\n  {'─'*W}")
    print(f"  {title}")
    print(f"  {'─'*W}")
    for e in entries:
        dignity = ", ".join(
            f"{p}:{d}" for p, d in e["dignity_details"].items()
            if d and "Absent" not in d and "Off-domain" not in d
        )
        badge = BADGE.get(e["fate_type"], "")
        if show_evidence and e["evidence"]:
            evid = e["evidence"][0][:45]
            print(f"  {badge}  {e['label']:<45}  {dignity:<40}  → {evid}")
        else:
            print(f"  {badge}  {e['label']:<45}  {dignity}")


def main():
    parser = argparse.ArgumentParser(
        description="Lal Kitab — Domain Fate Report for a natal chart",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python lk_domain_fate_report.py --figure "MS Dhoni"
  python lk_domain_fate_report.py --figure "Vladimir Putin" --no-neither
  python lk_domain_fate_report.py --figure "Steve Jobs" --gp-only
  python lk_domain_fate_report.py --figure "Ratan Tata" --rp-only
  python lk_domain_fate_report.py --figure "Elon Musk" --categories canonical finance
  python lk_domain_fate_report.py --dob 1942-10-11 --tob 16:00 --place "Allahabad, India" --name "Amitabh"
  python lk_domain_fate_report.py --figure "MS Dhoni" --json
  python lk_domain_fate_report.py --list
        """,
    )
    parser.add_argument("--figure",     type=str)
    parser.add_argument("--name",       type=str, default="Custom Chart")
    parser.add_argument("--dob",        type=str)
    parser.add_argument("--tob",        type=str, default="12:00")
    parser.add_argument("--place",      type=str, default="New Delhi, India")
    parser.add_argument("--categories", nargs="*", choices=list(CAT_LABELS.keys()))
    parser.add_argument("--no-neither", action="store_true")
    parser.add_argument("--gp-only",    action="store_true", help="Show only Graha Phal domains")
    parser.add_argument("--rp-only",    action="store_true", help="Show only Rashi Phal domains")
    parser.add_argument("--json",       action="store_true")
    parser.add_argument("--list",       action="store_true")
    args = parser.parse_args()

    figures = load_figures()

    if args.list:
        print(f"\n{'─'*65}")
        print(f"  {'#':>3}  {'Name':<30}  {'DOB':<12}  Place")
        print(f"{'─'*65}")
        for i, f in enumerate(figures, 1):
            print(f"  {i:>3}  {f['name']:<30}  {f['dob']:<12}  {f.get('birth_place','?')[:25]}")
        print()
        sys.exit(0)

    # Resolve birth data
    if args.figure:
        fig = find_figure(args.figure, figures)
        if not fig:
            print(f"\n❌  '{args.figure}' not found. Use --list to see all figures.\n")
            sys.exit(1)
        name, dob, tob, place = fig["name"], fig["dob"], fig.get("tob","12:00"), fig.get("birth_place","New Delhi, India")
    elif args.dob:
        name, dob, tob, place = args.name, args.dob, args.tob, args.place
    else:
        # Interactive
        print("\n  Enter birth details:")
        name  = input("  Name      : ").strip() or "Custom"
        dob   = input("  DOB (YYYY-MM-DD): ").strip()
        tob   = input("  TOB (HH:MM)     : ").strip() or "12:00"
        place = input("  Place           : ").strip() or "New Delhi, India"

    print(f"\n  Building natal chart for {name} ({dob} {tob}, {place})...")
    try:
        natal = build_chart(dob, tob, place)
    except Exception as e:
        print(f"\n❌  {e}\n"); sys.exit(1)

    view = NatalFateView()
    entries = view.evaluate(natal, categories=args.categories or None, include_neither=not args.no_neither)

    if args.json:
        planets = {p: d.get("house") for p, d in natal.get("planets_in_houses", {}).items()}
        print(json.dumps({
            "name": name, "dob": dob, "tob": tob, "place": place,
            "planets": planets,
            "stats": {
                "GP": sum(1 for e in entries if e["fate_type"] == "GRAHA_PHAL"),
                "RP": sum(1 for e in entries if e["fate_type"] == "RASHI_PHAL"),
                "HY": sum(1 for e in entries if e["fate_type"] == "HYBRID"),
                "NI": sum(1 for e in entries if e["fate_type"] == "NEITHER"),
                "total": len(entries),
            },
            "domain_fate_view": entries,
        }, indent=2))
    else:
        print_report(
            name, dob, tob, place, natal, entries,
            include_neither=not args.no_neither,
            gp_only=args.gp_only,
            rp_only=args.rp_only,
        )


if __name__ == "__main__":
    main()
