"""
Integrated Timing Benchmarker (Revised)
=======================================
Combines Grah Phal (Baseline) and Rashi Phal (Thermodynamic) logic to evaluate
the total predictive fidelity across the public figures dataset.
Outputs: TP, FP, TN, FN summary.
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
from astroq.lk_prediction.varshphal_timing_engine import VarshphalTimingEngine
from astroq.lk_prediction.rashi_phal_evaluator import RashiPhalEvaluator

GROUND_TRUTH_PATH = os.path.join(_BACKEND, "data", "public_figures_ground_truth.json")

def main():
    with open(GROUND_TRUTH_PATH, "r") as f:
        figures = json.load(f)
        
    baseline_engine = VarshphalTimingEngine()
    rashi_evaluator = RashiPhalEvaluator()
    gen = ChartGenerator()
    
    # Global Confusion Matrix
    matrix = {"TP": 0, "FP": 0, "TN": 0, "FN": 0}
    
    # Domain Mapping
    all_domains = ["career_travel", "marriage", "health", "finance", "progeny"]
    
    print(f"Running Integrated Benchmarker on {len(figures)} figures...")

    for fig in figures:
        name = fig["name"]
        try:
            place = fig.get("birth_place", "India")
            locations = gen.geocode_place(place)
            if not locations:
                lat, lon, utc = 20.0, 77.0, "+05:30"
            else:
                loc = locations[0]
                lat, lon, utc = loc["latitude"], loc["longitude"], loc["utc_offset"]
                
            natal = gen.generate_chart(fig["dob"], fig.get("tob", "12:00"), place, lat, lon, utc, "vedic")
            # We evaluate years 1 to 100
            all_annual = gen.generate_annual_charts(natal, max_years=100)
            
            # Ground truth: {age: set(domains)}
            gt_events = defaultdict(set)
            for event in fig.get("events", []):
                gt_events[event["age"]].add(event["domain"])
                
            for age in range(1, 101):
                annual = all_annual.get(f"chart_{age}")
                if not annual: continue
                
                # Rashi triggers for this year
                rashi_triggers = rashi_evaluator.evaluate(natal, annual)
                rashi_domains = {t["domain"] for t in rashi_triggers}
                
                for domain in all_domains:
                    is_actual = domain in gt_events[age]
                    
                    # Prediction Logic:
                    # 1. Baseline Confidence
                    conf_info = baseline_engine.get_timing_confidence(natal, annual, age, domain)
                    is_baseline_pred = conf_info["confidence"] in ["High", "Medium"]
                    
                    # 2. Rashi Trigger
                    is_rashi_pred = domain in rashi_domains
                    
                    is_predicted = is_baseline_pred or is_rashi_pred
                    
                    # Update Confusion Matrix
                    if is_predicted and is_actual:
                        matrix["TP"] += 1
                    elif is_predicted and not is_actual:
                        matrix["FP"] += 1
                    elif not is_predicted and not is_actual:
                        matrix["TN"] += 1
                    elif not is_predicted and is_actual:
                        matrix["FN"] += 1
                        
        except Exception as e:
            # print(f"Error on {name}: {e}")
            continue

    total_samples = sum(matrix.values())
    if total_samples == 0:
        print("No samples were processed.")
        return
        
    precision = matrix["TP"] / max(1, matrix["TP"] + matrix["FP"])
    recall = matrix["TP"] / max(1, matrix["TP"] + matrix["FN"])
    accuracy = (matrix["TP"] + matrix["TN"]) / total_samples
    f1 = 2 * (precision * recall) / max(0.0001, precision + recall)

    print(f"\n===========================================")
    print(f"INTEGRATED TIMING ENGINE (GRAH + RASHI PHAL)")
    print(f"===========================================")
    print(f"Total Samples (Year-Domains): {total_samples}")
    print(f"-------------------------------------------")
    print(f"True Positives (TP):  {matrix['TP']}")
    print(f"False Positives (FP): {matrix['FP']}")
    print(f"True Negatives (TN):  {matrix['TN']}")
    print(f"False Negatives (FN): {matrix['FN']}")
    print(f"-------------------------------------------")
    print(f"Precision: {precision:.3f}")
    print(f"Recall (Sensitivity): {recall:.3f}")
    print(f"Accuracy:  {accuracy:.1%}")
    print(f"F1-Score:  {f1:.3f}")
    print(f"===========================================")

if __name__ == "__main__":
    main()
