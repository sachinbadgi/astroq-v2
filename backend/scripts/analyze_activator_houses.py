"""
Analyze Canonical Activator Houses
==================================
Investigates if True Positives occur when a planet enters the specific 
Lal Kitab 'Activator House' for the house where the Doubtful planet sits.
"""

import json
import os
import sys
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.normpath(os.path.join(_HERE, ".."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.rashi_phal_evaluator import RashiPhalEvaluator

GROUND_TRUTH_PATH = os.path.join(_BACKEND, "data", "public_figures_ground_truth.json")
REPORT_PATH = os.path.join(_BACKEND, "..", "artifacts", "reports", "doubtful_timing_benchmark_report.json")
NOISE_WINDOW = 3

# Canonical House Activator Mapping (House X is woken up by presence of any planet in House Y)
HOUSE_ACTIVATOR_MAP = {
    1: 7,
    2: 9,
    3: 12,
    4: 2,
    5: 9,
    6: 12,
    7: 1,
    8: 2,
    9: 2,
    10: 5,
    11: 3,
    12: 6
}

def load_missed_events():
    if not os.path.exists(REPORT_PATH):
        sys.exit(1)
    with open(REPORT_PATH, "r") as f:
        report = json.load(f)
    missed = defaultdict(list)
    for figure in report.get("figures", []):
        for event in figure.get("events", []):
            if not event.get("baseline_hit", False):
                missed[figure["name"]].append(event)
    return missed

def main():
    missed_events_map = load_missed_events()
    with open(GROUND_TRUTH_PATH, "r") as f:
        figures = json.load(f)
        
    evaluator = RashiPhalEvaluator()
    
    tp_stats = {"total": 0, "activated": 0}
    fp_stats = {"total": 0, "activated": 0}
    
    print("Analyzing Canonical Activator House matches for TP vs FP...")

    for fig in figures:
        name = fig["name"]
        if name not in missed_events_map:
            continue
            
        try:
            gen = ChartGenerator()
            place = fig.get("birth_place", "India")
            locations = gen.geocode_place(place)
            if not locations:
                lat, lon, utc = 20.0, 77.0, "+05:30"
            else:
                loc = locations[0]
                lat, lon, utc = loc["latitude"], loc["longitude"], loc["utc_offset"]
                
            natal = gen.generate_chart(fig["dob"], fig.get("tob", "12:00"), place, lat, lon, utc, "vedic")
            all_annual = gen.generate_annual_charts(natal, max_years=100)
            
            for event in missed_events_map[name]:
                age = event["age"]
                target_domain = event.get("domain", "")
                
                # True Positive Check
                annual = all_annual.get(f"chart_{age}")
                if annual:
                    a_pos = {p: d["house"] for p, d in annual["planets_in_houses"].items() if p != "Lagna"}
                    triggers = evaluator.evaluate(natal, annual)
                    for trigger in triggers:
                        if trigger["domain"] == target_domain:
                            tp_stats["total"] += 1
                            planet = trigger["triggering_planet"]
                            p_house = a_pos[planet]
                            activator_h = HOUSE_ACTIVATOR_MAP.get(p_house)
                            
                            # Check if ANY planet is in the activator house
                            if any(h == activator_h for p, h in a_pos.items() if p != "Lagna"):
                                tp_stats["activated"] += 1
                            break
                            
                # False Positive Check
                for noise_age in range(max(1, age - NOISE_WINDOW), age + NOISE_WINDOW + 1):
                    if noise_age == age: continue
                    n_annual = all_annual.get(f"chart_{noise_age}")
                    if n_annual:
                        na_pos = {p: d["house"] for p, d in n_annual["planets_in_houses"].items() if p != "Lagna"}
                        n_triggers = evaluator.evaluate(natal, n_annual)
                        for t in n_triggers:
                            if t["domain"] == target_domain:
                                fp_stats["total"] += 1
                                planet = t["triggering_planet"]
                                p_house = na_pos[planet]
                                activator_h = HOUSE_ACTIVATOR_MAP.get(p_house)
                                if any(h == activator_h for p, h in na_pos.items() if p != "Lagna"):
                                    fp_stats["activated"] += 1
                                break
                                
        except Exception as e:
            continue

    print(f"\n===========================================")
    print(f"Canonical Activator House Analysis")
    print(f"===========================================")
    print(f"True Positives: {tp_stats['total']}")
    print(f"  - Activated by Canonical House: {tp_stats['activated']} ({(tp_stats['activated']/max(1, tp_stats['total']))*100:.1f}%)")
    print(f"False Positives: {fp_stats['total']}")
    print(f"  - Activated by Canonical House: {fp_stats['activated']} ({(fp_stats['activated']/max(1, fp_stats['total']))*100:.1f}%)")
    print(f"-------------------------------------------")
    
    tp_p = (tp_stats['activated']/max(1, tp_stats['total']))*100
    fp_p = (fp_stats['activated']/max(1, fp_stats['total']))*100
    print(f"Signal Multiplier: {tp_p/max(0.1, fp_p):.2f}x")

if __name__ == "__main__":
    main()
