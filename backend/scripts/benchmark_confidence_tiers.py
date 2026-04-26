"""
Benchmark Rashi Phal Evaluator with Confidence Tiers
====================================================
Tests the deterministic thermodynamic logic and reports success/noise by confidence tier.
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

def load_missed_events():
    if not os.path.exists(REPORT_PATH):
        print(f"Report not found at {REPORT_PATH}")
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
    
    # Tiered stats: {confidence: {"tp": count, "fp": count}}
    stats = defaultdict(lambda: {"tp": 0, "fp": 0})
    total_missed = sum(len(e) for e in missed_events_map.values())
    total_noise_years = 0
    
    tp_details = []

    print(f"Running Confidence-Tiered Benchmark...")

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
                
                annual = all_annual.get(f"chart_{age}")
                if annual:
                    triggers = evaluator.evaluate(natal, annual)
                    for t in triggers:
                        if t["domain"] == target_domain:
                            conf = t["confidence"]
                            stats[conf]["tp"] += 1
                            tp_details.append(f"{name} (Age {age} | {target_domain}): {conf}")
                            break
                            
                for noise_age in range(max(1, age - NOISE_WINDOW), age + NOISE_WINDOW + 1):
                    if noise_age == age: continue
                    n_annual = all_annual.get(f"chart_{noise_age}")
                    if n_annual:
                        total_noise_years += 1
                        n_triggers = evaluator.evaluate(natal, n_annual)
                        seen_domains = set()
                        for nt in n_triggers:
                            if nt["domain"] == target_domain and target_domain not in seen_domains:
                                conf = nt["confidence"]
                                stats[conf]["fp"] += 1
                                seen_domains.add(target_domain)
                                
        except Exception as e:
            continue

    print(f"\n===========================================")
    print(f"Rashi Phal Confidence Tier Analysis")
    print(f"===========================================")
    print(f"Total Missed Events: {total_missed}")
    print(f"Total Noise Years:   {total_noise_years}")
    print(f"-------------------------------------------")
    
    for conf, data in sorted(stats.items()):
        tp_rate = (data["tp"] / total_missed) * 100
        fp_rate = (data["fp"] / total_noise_years) * 100
        print(f"{conf:<30} | TP: {data['tp']} ({tp_rate:.1f}%) | FP: {data['fp']} ({fp_rate:.1f}%)")

if __name__ == "__main__":
    main()
