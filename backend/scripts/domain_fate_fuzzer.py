"""
domain_fate_fuzzer.py
=====================
Runs NatalFateView for all 68 public figures and produces a comprehensive
report showing how all 50+ event/domains are classified (GP/RP/HYBRID/NEITHER)
per figure.

Run:
    cd /Users/sachinbadgi/Documents/lal_kitab/astroq-v2/backend
    python scripts/domain_fate_fuzzer.py
"""
import json
import sys
import os
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.natal_fate_view import NatalFateView

# ── GEO LOOKUP ──────────────────────────────────────────────────────────────
GEO_MAP = {
    "Allahabad, India":                        (25.4358,  81.8463,  "+05:30"),
    "Mumbai, India":                           (19.0760,  72.8777,  "+05:30"),
    "Vadnagar, India":                         (23.7801,  72.6373,  "+05:30"),
    "San Francisco, California, US":           (37.7749, -122.4194, "-08:00"),
    "Seattle, Washington, US":                 (47.6062, -122.3321, "-08:00"),
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

FATE_SYMBOL = {
    "GRAHA_PHAL": "GP ✓",
    "RASHI_PHAL": "RP ~",
    "HYBRID":     "HY ⊕",
    "NEITHER":    "-- ○",
}

def get_geo(place: str):
    for key, val in GEO_MAP.items():
        if key.lower() in place.lower() or place.lower() in key.lower():
            return val
    return DEFAULT_GEO

def build_natal(gen, fig):
    dob = fig["dob"]
    tob = fig.get("tob", "12:00") + ":00" if len(fig.get("tob","12:00")) == 5 else fig.get("tob","12:00:00")
    place = fig.get("birth_place", "New Delhi, India")
    lat, lon, tz = get_geo(place)
    try:
        payload = gen.build_full_chart_payload(
            dob_str=dob, tob_str=tob,
            place_name=place,
            latitude=lat, longitude=lon, utc_string=tz,
            chart_system="vedic"
        )
        return payload.get("chart_0")
    except Exception as e:
        return None

def run():
    gt_path = os.path.join(os.path.dirname(__file__), "..", "data", "public_figures_ground_truth.json")
    with open(gt_path) as f:
        figures = json.load(f)

    gen = ChartGenerator()
    view = NatalFateView()

    # Store results: { figure_name: { domain: fate_type } }
    all_results = []
    failed = []
    domain_order = None  # Will be set from first successful run

    print(f"\nProcessing {len(figures)} public figures...\n")

    for i, fig in enumerate(figures):
        name = fig["name"]
        print(f"  [{i+1:02d}/{len(figures)}] {name}...", end=" ", flush=True)

        natal = build_natal(gen, fig)
        if natal is None:
            print("FAILED (chart generation error)")
            failed.append(name)
            continue

        planets = {p: d.get("house") for p, d in natal.get("planets_in_houses", {}).items()}
        entries = view.evaluate(natal)

        if domain_order is None:
            domain_order = [(e["domain"], e["label"], e["category"]) for e in entries]

        fate_map = {e["domain"]: e["fate_type"] for e in entries}
        gp = sum(1 for v in fate_map.values() if v == "GRAHA_PHAL")
        rp = sum(1 for v in fate_map.values() if v == "RASHI_PHAL")
        hy = sum(1 for v in fate_map.values() if v == "HYBRID")
        ni = sum(1 for v in fate_map.values() if v == "NEITHER")

        all_results.append({
            "name": name,
            "dob": fig["dob"],
            "birth_place": fig.get("birth_place", "?"),
            "planets": planets,
            "fate_map": fate_map,
            "entries": entries,
            "stats": {"GP": gp, "RP": rp, "HY": hy, "NI": ni, "total": len(entries)},
        })
        print(f"GP={gp} RP={rp} HY={hy} NI={ni}")

    # ── REPORT ──────────────────────────────────────────────────────────────
    sep = "=" * 120
    thin = "-" * 120

    print(f"\n\n{sep}")
    print("  NATAL FATE VIEW — FULL DOMAIN CLASSIFICATION REPORT")
    print(f"  Figures processed: {len(all_results)} / {len(figures)}  |  Failed: {len(failed)}")
    print(sep)

    # ── PER-FIGURE DETAILED REPORT ──────────────────────────────────────────
    for res in all_results:
        planets_str = "  ".join(f"{p}→H{h}" for p, h in sorted(res["planets"].items(), key=lambda x: x[1] or 0))
        st = res["stats"]
        print(f"\n{'─'*120}")
        print(f"  {res['name']}  |  DOB: {res['dob']}  |  {res['birth_place']}")
        print(f"  Planets: {planets_str}")
        print(f"  Summary: GP={st['GP']} | RP={st['RP']} | HY={st['HY']} | NI={st['NI']} | Total={st['total']}")
        print(f"{'─'*120}")

        # Group by category
        by_cat = defaultdict(list)
        for e in res["entries"]:
            by_cat[e["category"]].append(e)

        cat_labels = {
            "canonical":      "CANONICAL DOMAINS",
            "career_tech":    "CAREER & TECHNOLOGY",
            "finance":        "FINANCE & INVESTMENTS",
            "home_lifestyle": "HOME, LIFESTYLE & SUSTAINABILITY",
            "health_wellness":"HEALTH & WELLNESS",
            "tech_infra":     "TECHNOLOGY & DIGITAL INFRA",
            "modern_finance": "MODERN FINANCE",
            "sustainable":    "SUSTAINABLE INNOVATION",
            "social_psych":   "SOCIAL & PSYCHOLOGICAL",
        }

        for cat in ["canonical","career_tech","finance","home_lifestyle",
                    "health_wellness","tech_infra","modern_finance","sustainable","social_psych"]:
            cat_entries = by_cat.get(cat, [])
            if not cat_entries:
                continue
            print(f"\n  [{cat_labels.get(cat, cat)}]")
            for e in cat_entries:
                sym = FATE_SYMBOL.get(e["fate_type"], "??")
                evid = e["evidence"][0] if e["evidence"] else ""
                dignity = ", ".join(f"{p}:{d}" for p,d in e["dignity_details"].items() if d not in ("Absent",""))
                print(f"    {sym}  {e['label']:<40}  {dignity[:50]:<50}  | {evid[:50]}")

    # ── CROSS-FIGURE DOMAIN HEATMAP ──────────────────────────────────────────
    if domain_order and all_results:
        print(f"\n\n{sep}")
        print("  CROSS-FIGURE DOMAIN HEATMAP  (GP=Graha Phal | RP=Rashi Phal | HY=Hybrid | --=Absent)")
        print(sep)

        # Count across all figures per domain
        domain_stats = {}
        for domain, label, cat in domain_order:
            counts = defaultdict(int)
            for res in all_results:
                ft = res["fate_map"].get(domain, "NEITHER")
                counts[ft] += 1
            domain_stats[domain] = counts

        print(f"\n  {'Domain':<45} {'Category':<16} {'GP':>4} {'RP':>4} {'HY':>4} {'NI':>4}  {'GP%':>5}")
        print(f"  {'─'*45} {'─'*16} {'─'*4} {'─'*4} {'─'*4} {'─'*4}  {'─'*5}")
        for domain, label, cat in domain_order:
            c = domain_stats[domain]
            total = len(all_results)
            gp_pct = c["GRAHA_PHAL"] / total * 100 if total else 0
            print(f"  {label:<45} {cat:<16} {c['GRAHA_PHAL']:>4} {c['RASHI_PHAL']:>4} {c['HYBRID']:>4} {c['NEITHER']:>4}  {gp_pct:>4.0f}%")

    # ── MOST GP-RICH FIGURES ─────────────────────────────────────────────────
    print(f"\n\n{sep}")
    print("  TOP 10 — MOST GRAHA PHAL DOMAINS (Fixed Destiny Charts)")
    print(sep)
    ranked = sorted(all_results, key=lambda r: r["stats"]["GP"], reverse=True)
    for r in ranked[:10]:
        st = r["stats"]
        print(f"  {r['name']:<30} GP={st['GP']:>3}  RP={st['RP']:>3}  HY={st['HY']:>2}  NI={st['NI']:>3}  GP%={st['GP']/st['total']*100:>4.0f}%")

    print(f"\n{sep}")
    print("  TOP 10 — MOST RASHI PHAL DOMAINS (Conditional Destiny Charts)")
    print(sep)
    ranked_rp = sorted(all_results, key=lambda r: r["stats"]["RP"], reverse=True)
    for r in ranked_rp[:10]:
        st = r["stats"]
        print(f"  {r['name']:<30} GP={st['GP']:>3}  RP={st['RP']:>3}  HY={st['HY']:>2}  NI={st['NI']:>3}  RP%={st['RP']/st['total']*100:>4.0f}%")

    if failed:
        print(f"\n⚠️  Failed figures: {', '.join(failed)}")

    print(f"\n{'='*120}\n")

    # Save JSON for downstream use
    out_path = os.path.join(os.path.dirname(__file__), "..", "data", "domain_fate_report.json")
    out_data = [
        {
            "name": r["name"],
            "dob": r["dob"],
            "planets": r["planets"],
            "stats": r["stats"],
            "domain_fate": r["fate_map"],
        }
        for r in all_results
    ]
    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2)
    print(f"JSON report saved → {out_path}\n")

if __name__ == "__main__":
    run()
