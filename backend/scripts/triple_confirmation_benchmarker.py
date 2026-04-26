"""
Triple Confirmation Benchmarker
==============================
Enforces the Thermodynamic 'Wake-Up' requirement on the baseline Grah Phal engine
to eliminate repetitive geometric False Positives.
Logic: Predicted = (Natal + Annual Geometry) AND (Annual Wake-Up)
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
    
    print(f"Running Triple-Confirmation Benchmarker...")

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
            all_annual = gen.generate_annual_charts(natal, max_years=100)
            
            gt_events = defaultdict(set)
            for event in fig.get("events", []):
                gt_events[event["age"]].add(event["domain"])
                
            for age in range(1, 101):
                annual = all_annual.get(f"chart_{age}")
                if not annual: continue
                
                annual_pos = {p: d["house"] for p, d in annual["planets_in_houses"].items() if p != "Lagna"}
                
                # Rashi triggers (Already include wake-up logic)
                rashi_triggers = rashi_evaluator.evaluate(natal, annual)
                rashi_domains = {t["domain"] for t in rashi_triggers}
                
                for domain in all_domains:
                    is_actual = domain in gt_events[age]
                    is_predicted = False
                    
                    # 1. Baseline Confidence
                    conf_info = baseline_engine.get_timing_confidence(natal, annual, age, domain)
                    if conf_info["confidence"] in ["High", "Medium"]:
                        # TRIPLE CONFIRMATION CHECK:
                        # Extract the triggering planet from the raw matches
                        triggers = conf_info.get("raw_matches", [])
                        if not triggers:
                            # If it's a generic domain rule without a specific planet, 
                            # we treat it as High confidence for now
                            is_predicted = True
                        else:
                            # If ANY triggering planet is 'Awake', allow the prediction
                            any_awake = False
                            for t in triggers:
                                # We need to identify the planet. The engine uses abbreviations.
                                # Let's check for standard planet names in the trigger desc
                                for p_name in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]:
                                    if p_name in t.get("desc", ""):
                                        is_dormant, _, _ = rashi_evaluator._check_dormancy_state(p_name, annual_pos)
                                        if not is_dormant:
                                            any_awake = True
                                            break
                                if any_awake: break
                            
                            if any_awake:
                                is_predicted = True
                    
                    # 2. Rashi Trigger (The deterministic "wake-up" for Doubtful)
                    if domain in rashi_domains:
                        is_predicted = True
                        
                    # Confusion Matrix logic
                    if is_predicted and is_actual:
                        matrix["TP"] += 1
                    elif is_predicted and not is_actual:
                        matrix["FP"] += 1
                    elif not is_predicted and not is_actual:
                        matrix["TN"] += 1
                    elif not is_predicted and is_actual:
                        matrix["FN"] += 1
                        
        except Exception as e:
            continue

    total_samples = sum(matrix.values())
    precision = matrix["TP"] / max(1, matrix["TP"] + matrix["FP"])
    recall = matrix["TP"] / max(1, matrix["TP"] + matrix["FN"])
    accuracy = (matrix["TP"] + matrix["TN"]) / total_samples

    print(f"\n===========================================")
    print(f"TRIPLE-CONFIRMATION ENGINE PERFORMANCE")
    print(f"===========================================")
    print(f"Total Samples: {total_samples}")
    print(f"-------------------------------------------")
    print(f"True Positives (TP):  {matrix['TP']}")
    print(f"False Positives (FP): {matrix['FP']}")
    print(f"True Negatives (TN):  {matrix['TN']}")
    print(f"False Negatives (FN): {matrix['FN']}")
    print(f"-------------------------------------------")
    print(f"Precision: {precision:.3f}")
    print(f"Recall:    {recall:.3f}")
    print(f"Accuracy:  {accuracy:.1%}")
    print(f"===========================================")

if __name__ == "__main__":
    main()
