
import os
import sys
import json
import sqlite3
from collections import Counter, defaultdict

sys.path.append(os.path.join(os.getcwd(), "backend"))

from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.rules_engine import RulesEngine

DB_PATH = os.path.join(os.getcwd(), "backend/data/rules.db")

from astroq.lk_prediction.location_provider import GEO_MAP, DEFAULT_GEO

GT_TO_DB_DOMAINS = {
    "career_travel": ["profession"],
    "career":        ["profession"],
    "finance":       ["wealth"],
    "wealth":        ["wealth"],
    "health":        ["health"],
    "marriage":      ["marriage"],
    "progeny":       ["progeny"],
    "legal":         ["health"],
    "other":         ["profession"],
}

def load_fate_map():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, fate_type FROM deterministic_rules")
    res = {r[0]: (r[1] or "NEUTRAL") for r in cur.fetchall()}
    conn.close()
    return res

def run():
    print("=== Final Predictive Audit: Natal Promise vs Varshphal Timing ===\n")
    
    fate_map = load_fate_map()
    generator = ChartGenerator()
    engine = RulesEngine(DB_PATH)

    gt_path = os.path.join(os.getcwd(), "backend/data/public_figures_ground_truth.json")
    with open(gt_path) as f:
        figures = json.load(f)

    total_events = 0
    natal_promise_confirmed = 0
    gp_events = 0
    rp_events = 0
    varshphal_timed_hits = 0

    for fig in figures:
        name = fig["name"]
        dob = fig["dob"]
        tob = fig["tob"]
        if len(tob.split(":")) == 2: tob += ":00"
        place = fig.get("birth_place", "New Delhi, India")
        lat, lon, tz = GEO_MAP.get(place, (28.6139, 77.2090, "+05:30"))

        try:
            payload = generator.build_full_chart_payload(
                dob_str=dob, tob_str=tob, place_name=place,
                latitude=lat, longitude=lon, utc_string=tz,
                chart_system="vedic"
            )
        except: continue

        natal_chart = payload.get("chart_0")
        if not natal_chart: continue

        for event in fig.get("events", []):
            age = event.get("age")
            if not isinstance(age, int): continue
            
            total_events += 1
            gt_dom = event.get("domain", "career_travel")
            db_doms = GT_TO_DB_DOMAINS.get(gt_dom, ["profession"])

            # 1. Natal Promise Check
            natal_hits = engine.evaluate_chart(natal_chart)
            domain_natal_hits = [h for h in natal_hits if h.domain in db_doms]
            
            has_promise = len(domain_natal_hits) > 0
            if has_promise:
                natal_promise_confirmed += 1
                
                fts = [fate_map.get(h.rule_id, "NEUTRAL") for h in domain_natal_hits]
                is_gp = any(ft == "GRAHA_PHAL" for ft in fts)
                is_rp = any(ft in ("RASHI_PHAL", "HYBRID") for ft in fts)
                
                if is_gp:
                    gp_events += 1
                elif is_rp:
                    rp_events += 1
                
                # If an event has BOTH GP and RP hits, it's currently counted in gp_events.
                # Let's track pure RP events (conditional only).

            # 2. Varshphal Timing Check
            annual_key = f"chart_{age}"
            annual_chart = payload.get(annual_key)
            if annual_chart:
                annual_hits = engine.evaluate_chart(annual_chart)
                domain_annual_hits = [h for h in annual_hits if h.domain in db_doms]
                
                if len(domain_annual_hits) > 0:
                    varshphal_timed_hits += 1

    print(f"Total Events Analyzed: {total_events}")
    print(f"Natal Promise Confirmed: {natal_promise_confirmed} ({natal_promise_confirmed/total_events*100:.1f}%)")
    print(f"  - Graha Phal (Fixed): {gp_events}")
    print(f"  - Rashi Phal (Conditional/Hybrid): {rp_events}")
    print(f"Varshphal Timing Hits: {varshphal_timed_hits} ({varshphal_timed_hits/total_events*100:.1f}%)")

if __name__ == "__main__":
    run()
