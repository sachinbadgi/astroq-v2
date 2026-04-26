"""
natal_fate_audit.py
===================
Prints a Natal Fate View table for any public figure or custom birth data.

Usage:
    python backend/scripts/natal_fate_audit.py --figure "Walter Matthau"
    python backend/scripts/natal_fate_audit.py --figure "Steve Jobs" --categories canonical finance
    python backend/scripts/natal_fate_audit.py --figure "Steve Jobs" --json
    python backend/scripts/natal_fate_audit.py --dob "1920-10-01" --tob "11:00" --place "New York, US"
"""
import os
import sys
import json
import argparse

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.natal_fate_view import NatalFateView

# ── GEO MAP ────────────────────────────────────────────────────────────────
GEO_MAP = {
    "Allahabad, India":                        (25.4358,   81.8463,   "+05:30"),
    "Mumbai, India":                           (19.0760,   72.8777,   "+05:30"),
    "Vadnagar, India":                         (23.7801,   72.6373,   "+05:30"),
    "San Francisco, California, US":           (37.7749,  -122.4194,  "-08:00"),
    "Seattle, Washington, US":                 (47.6062,  -122.3321,  "-08:00"),
    "Sandringham, Norfolk, UK":                (52.8311,    0.5054,   "+00:00"),
    "New Delhi, India":                        (28.6139,   77.2090,   "+05:30"),
    "Gary, Indiana, US":                       (41.5934,  -87.3464,  "-06:00"),
    "Pretoria, South Africa":                  (-25.7479,  28.2293,   "+02:00"),
    "Porbandar, India":                        (21.6417,   69.6293,   "+05:30"),
    "Jamaica Hospital, Queens, New York, US":  (40.7028,  -73.8152,  "-05:00"),
    "Honolulu, Hawaii, US":                    (21.3069, -157.8583,  "-10:00"),
    "Mayfair, London, UK":                     (51.5100,   -0.1458,  "+00:00"),
    "Skopje, North Macedonia":                 (42.0003,   21.4280,  "+01:00"),
}
DEFAULT_GEO = (28.6139, 77.2090, "+05:30")  # New Delhi fallback


def load_ground_truth() -> list:
    gt_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "public_figures_ground_truth.json"
    )
    if os.path.exists(gt_path):
        with open(gt_path) as f:
            return json.load(f)
    return []


def find_figure(name: str, figures: list) -> dict | None:
    name_lower = name.lower()
    for fig in figures:
        if fig.get("name", "").lower() == name_lower:
            return fig
    # Partial match
    for fig in figures:
        if name_lower in fig.get("name", "").lower():
            return fig
    return None


def build_natal_chart(dob: str, tob: str, place: str) -> dict:
    lat, lon, tz = GEO_MAP.get(place, DEFAULT_GEO)
    if len(tob.split(":")) == 2:
        tob += ":00"
    gen = ChartGenerator()
    payload = gen.build_full_chart_payload(
        dob_str=dob, tob_str=tob, place_name=place,
        latitude=lat, longitude=lon, utc_string=tz,
        chart_system="vedic",
    )
    natal = payload.get("chart_0")
    if natal is None:
        raise ValueError(f"Could not generate natal chart for {dob} / {tob} / {place}")
    return natal


def print_summary(entries: list, name: str, dob: str):
    gp = sum(1 for e in entries if e["fate_type"] == "GRAHA_PHAL")
    rp = sum(1 for e in entries if e["fate_type"] == "RASHI_PHAL")
    hy = sum(1 for e in entries if e["fate_type"] == "HYBRID")
    ni = sum(1 for e in entries if e["fate_type"] == "NEITHER")
    total = len(entries)

    print(f"\n{'='*70}")
    print(f"  NATAL FATE VIEW — {name} (DOB: {dob})")
    print(f"{'='*70}")
    print(f"  Domains evaluated : {total}")
    print(f"  Graha Phal (Fixed): {gp} ({gp/total*100:.0f}%)")
    print(f"  Rashi Phal (Cond.): {rp} ({rp/total*100:.0f}%)")
    print(f"  Hybrid            : {hy} ({hy/total*100:.0f}%)")
    print(f"  Neither (Absent)  : {ni} ({ni/total*100:.0f}%)")
    print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Print a Natal Fate View for any Lal Kitab chart."
    )
    parser.add_argument("--figure", type=str, help="Figure name from ground_truth.json")
    parser.add_argument("--dob", type=str, help="Date of birth, e.g. 1955-10-28")
    parser.add_argument("--tob", type=str, help="Time of birth, e.g. 07:45")
    parser.add_argument("--place", type=str, default="New Delhi, India")
    parser.add_argument(
        "--categories", nargs="*",
        choices=[
            "canonical", "career_tech", "finance", "home_lifestyle",
            "health_wellness", "tech_infra", "modern_finance",
            "sustainable", "social_psych",
        ],
        help="Filter to specific categories (default: all)",
    )
    parser.add_argument(
        "--no-neither", action="store_true",
        help="Exclude domains with no natal promise (NEITHER)"
    )
    parser.add_argument(
        "--json", action="store_true", dest="as_json",
        help="Output raw JSON instead of table (for LLM consumption)"
    )
    args = parser.parse_args()

    # ── Resolve birth data ──────────────────────────────────────────────────
    name = "Custom Chart"
    dob = args.dob or ""
    tob = args.tob or "12:00"
    place = args.place

    if args.figure:
        figures = load_ground_truth()
        fig = find_figure(args.figure, figures)
        if fig is None:
            print(f"[ERROR] Figure '{args.figure}' not found in ground truth. "
                  "Use --dob / --tob / --place instead.")
            sys.exit(1)
        name = fig["name"]
        dob = fig["dob"]
        tob = fig.get("tob", "12:00")
        place = fig.get("birth_place", place)
    elif not dob:
        parser.error("Provide --figure or --dob.")

    # ── Generate chart ──────────────────────────────────────────────────────
    print(f"Generating natal chart for {name}...")
    try:
        natal_chart = build_natal_chart(dob, tob, place)
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    # ── Evaluate ────────────────────────────────────────────────────────────
    view = NatalFateView()
    entries = view.evaluate(
        natal_chart,
        categories=args.categories or None,
        include_neither=not args.no_neither,
    )

    # ── Output ──────────────────────────────────────────────────────────────
    if args.as_json:
        print(json.dumps(entries, indent=2))
    else:
        print_summary(entries, name, dob)
        print(view.format_as_table(entries))


if __name__ == "__main__":
    main()
