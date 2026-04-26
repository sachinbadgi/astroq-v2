"""
Public Figures — GP vs RP Rule Hit Analysis  v2
=================================================
For each public figure life event, fires ONLY the rules matching that
event's domain against the natal chart, then classifies each hit by
`fate_type` from the rules.db column.

Domain bridge: ground-truth event domains → DB rule domains
Ground truth:  career_travel, finance, health, marriage, progeny, legal
DB domains:    profession, wealth, health, marriage, progeny, general

This gives a per-event, domain-scoped GP vs RP signal rather than
the undifferentiated "fire everything" approach.
"""

import os
import sys
import json
import sqlite3
from collections import Counter, defaultdict

sys.path.append(os.path.join(os.getcwd(), "backend"))

from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.rules_engine import RulesEngine
from astroq.lk_prediction.lk_constants import RULE_FATE_TYPE_LABELS

DB_PATH = "backend/data/rules.db"

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
    "Raisen, India":                           (23.3308,   77.7788,   "+05:30"),
    "Madanapalle, India":                      (13.5562,   78.5020,   "+05:30"),
    "Indore, India":                           (22.7196,   75.8577,   "+05:30"),
    "Jamshedpur, India":                       (22.8046,   86.2029,   "+05:30"),
    "Jamaica Hospital, Queens, New York, US":  (40.7028,  -73.8152,  "-05:00"),
    "Honolulu, Hawaii, US":                    (21.3069, -157.8583,  "-10:00"),
    "Scranton, Pennsylvania, US":             (41.4090,  -75.6624,  "-05:00"),
    "Mayfair, London, UK":                     (51.5100,   -0.1458,  "+00:00"),
    "Buckingham Palace, London, UK":           (51.5014,   -0.1419,  "+00:00"),
    "Skopje, North Macedonia":                 (42.0003,   21.4280,  "+01:00"),
}

# Map ground-truth event domains → DB rule domains.
# 'general' is intentionally EXCLUDED — those 415 cross-domain rules fire for
# almost every chart and drown out the domain-specific GP/RP signal.
GT_TO_DB_DOMAINS: dict[str, list[str]] = {
    "career_travel": ["profession"],
    "career":        ["profession"],
    "finance":       ["wealth"],
    "wealth":        ["wealth"],
    "health":        ["health"],
    "marriage":      ["marriage"],
    "progeny":       ["progeny"],
    "legal":         ["health"],    # closest proxy — litigation affects health/6H
    "other":         ["profession"],
}


def load_rules_by_domain() -> dict[str, list[dict]]:
    """Load all rules from DB, grouped by domain, with fate_type."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT id, domain, description, condition, fate_type, scale, scoring_type FROM deterministic_rules")
    rows = cur.fetchall()
    conn.close()
    by_domain: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_domain[r["domain"]].append(dict(r))
    return dict(by_domain)


def run():
    print("=== Public Figures — Domain-Scoped Rule Engine GP vs RP Analysis ===\n", flush=True)

    rules_by_domain = load_rules_by_domain()
    generator = ChartGenerator()
    # We'll use the engine just for its _evaluate_node — load with full DB
    engine = RulesEngine(DB_PATH)

    # Build a rule_id → full rule dict for fast lookup
    rule_lookup: dict[str, dict] = {}
    for rules in rules_by_domain.values():
        for r in rules:
            rule_lookup[r["id"]] = r

    with open("backend/data/public_figures_ground_truth.json") as f:
        figures = json.load(f)

    all_fig_stats = []

    for fig in figures:
        name  = fig["name"]
        dob   = fig["dob"]
        tob   = fig["tob"]
        if len(tob.split(":")) == 2:
            tob += ":00"
        place = fig.get("birth_place", "New Delhi, India")
        lat, lon, tz = GEO_MAP.get(place, (28.6139, 77.2090, "+05:30"))

        try:
            payload = generator.build_full_chart_payload(
                dob_str=dob, tob_str=tob, place_name=place,
                latitude=lat, longitude=lon, utc_string=tz,
                chart_system="vedic"
            )
        except Exception as e:
            print(f"  [SKIP] {name}: {e}")
            continue

        natal_chart = payload.get("chart_0")
        if not natal_chart:
            continue

        planets_data = natal_chart.get("planets_in_houses", {})

        print(f"\n{'─'*72}")
        print(f"  {name}")
        print(f"{'─'*72}")

        fig_gp = fig_rp = fig_hyb = fig_ctx = fig_neu = 0
        event_rows = []

        for event in fig.get("events", []):
            age     = event.get("age", "?")
            desc    = event.get("description", "")
            gt_dom  = event.get("domain", "career_travel")
            db_doms = GT_TO_DB_DOMAINS.get(gt_dom, ["general"])

            # Collect only rules for this event's domains
            candidate_rules = []
            for db_dom in db_doms:
                candidate_rules.extend(rules_by_domain.get(db_dom, []))

            # Fire each candidate rule against the natal chart
            ev_counter: Counter = Counter()
            top_gp_rule = top_rp_rule = ""

            for rule in candidate_rules:
                try:
                    import json as _json
                    cond_tree = _json.loads(rule["condition"])
                except Exception:
                    continue
                match, _, _, _ = engine._evaluate_node(cond_tree, planets_data, natal_chart)
                if match:
                    ft = rule.get("fate_type") or "NEUTRAL"
                    ev_counter[ft] += 1
                    if ft == "GRAHA_PHAL" and not top_gp_rule:
                        top_gp_rule = rule["description"][:50]
                    if ft == "RASHI_PHAL" and not top_rp_rule:
                        top_rp_rule = rule["description"][:50]

            total_ev = sum(ev_counter.values())
            gp_ev = ev_counter["GRAHA_PHAL"] + ev_counter["HYBRID"]
            rp_ev = ev_counter["RASHI_PHAL"] + ev_counter["HYBRID"]

            fig_gp  += ev_counter["GRAHA_PHAL"]
            fig_rp  += ev_counter["RASHI_PHAL"]
            fig_hyb += ev_counter["HYBRID"]
            fig_ctx += ev_counter["CONTEXTUAL"]
            fig_neu += ev_counter["NEUTRAL"]

            if total_ev:
                gp_pct = gp_ev / total_ev * 100
                rp_pct = rp_ev / total_ev * 100
                tag = "🟢GP" if gp_ev > rp_ev else ("🟡RP" if rp_ev > gp_ev else "🔵=")
                ev_str = (f"fired={total_ev} | GP={gp_ev}({gp_pct:.0f}%) "
                          f"RP={rp_ev}({rp_pct:.0f}%) {tag}")
            else:
                ev_str = "no rules fired"

            row = (age, gt_dom, desc, ev_str, top_gp_rule, top_rp_rule)
            event_rows.append(row)
            print(f"  [Age {str(age):>3}] {gt_dom:<14} {desc[:38]:<38} | {ev_str}")
            if top_gp_rule:
                print(f"           🟢 {top_gp_rule}")
            if top_rp_rule:
                print(f"           🟡 {top_rp_rule}")

        fig_total = fig_gp + fig_rp + fig_hyb + fig_ctx + fig_neu
        gp_tot_pct = (fig_gp + fig_hyb) / fig_total * 100 if fig_total else 0
        rp_tot_pct = (fig_rp + fig_hyb) / fig_total * 100 if fig_total else 0

        profile = ("🟢 FIXED-DOMINANT"       if gp_tot_pct >= 60 else
                   "🟡 CONDITIONAL-DOMINANT" if rp_tot_pct >= 60 else
                   "🔵 BALANCED")

        print(f"\n  SUMMARY: total_rule_fires={fig_total} | "
              f"GP={fig_gp+fig_hyb}({gp_tot_pct:.0f}%) "
              f"RP={fig_rp+fig_hyb}({rp_tot_pct:.0f}%) → {profile}")

        all_fig_stats.append({
            "name": name, "total": fig_total,
            "gp": fig_gp, "rp": fig_rp, "hyb": fig_hyb,
            "ctx": fig_ctx, "neu": fig_neu,
            "gp_pct": gp_tot_pct, "rp_pct": rp_tot_pct,
            "profile": profile,
        })

    # ── Grand summary table ─────────────────────────────────────────────────
    print(f"\n\n{'='*80}")
    print("  GRAND SUMMARY — Domain-Scoped GP vs RP per Figure")
    print(f"  {'Figure':<30} {'Fires':>5}  {'GP':>4}  {'RP':>4}  {'Hyb':>4}  {'GP%':>5}  {'RP%':>5}  Profile")
    print(f"  {'─'*78}")
    for s in all_fig_stats:
        print(f"  {s['name']:<30} {s['total']:>5}  {s['gp']:>4}  {s['rp']:>4}  {s['hyb']:>4}  "
              f"{s['gp_pct']:>4.0f}%  {s['rp_pct']:>4.0f}%  {s['profile']}")

    grand = sum(s["total"] for s in all_fig_stats)
    total_gp  = sum(s["gp"]  for s in all_fig_stats)
    total_rp  = sum(s["rp"]  for s in all_fig_stats)
    total_hyb = sum(s["hyb"] for s in all_fig_stats)

    print(f"\n  Corpus-wide (domain-scoped): {grand} rule fires")
    print(f"  🟢 GP-explainable  : {total_gp+total_hyb:>4}  ({(total_gp+total_hyb)/grand*100:.1f}%)")
    print(f"  🟡 RP-explainable  : {total_rp+total_hyb:>4}  ({(total_rp+total_hyb)/grand*100:.1f}%)")

    profiles = Counter(s["profile"] for s in all_fig_stats)
    print(f"\n  Fate profiles across {len(all_fig_stats)} figures:")
    for p, c in profiles.most_common():
        print(f"    {p}  →  {c} figures")


if __name__ == "__main__":
    run()
