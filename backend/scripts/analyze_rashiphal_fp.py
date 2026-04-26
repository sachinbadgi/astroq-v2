"""
Analyze Rashi Phal False Positives
==================================
Investigates the thermodynamic "Wake-Up" (Loss of Dormancy) triggers
to find geometric or dignified patterns that separate True Positives from False Positives.
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
from astroq.lk_prediction.lk_constants import HOUSE_ASPECT_TARGETS, PLANET_EXALTATION, PLANET_DEBILITATION, PLANET_PAKKA_GHAR

GROUND_TRUTH_PATH = os.path.join(_BACKEND, "data", "public_figures_ground_truth.json")
REPORT_PATH = os.path.join(_BACKEND, "..", "artifacts", "reports", "doubtful_timing_benchmark_report.json")
NOISE_WINDOW = 3

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

def analyze_wakeup_state(planet: str, ppos: dict) -> dict:
    """Analyzes the state of the planet in the Annual Chart right as it wakes up."""
    house = ppos.get(planet)
    
    # 1. Why did it wake up?
    woken_by_forward = False
    for offset in range(1, 7):
        target_house = ((house - 1 + offset) % 12) + 1
        if any(h == target_house for p, h in ppos.items() if p != planet and p != "Lagna"):
            woken_by_forward = True
            break

    woken_by_aspect = False
    aspecting_houses = []
    for h1, targets in HOUSE_ASPECT_TARGETS.items():
        if house in targets:
            aspecting_houses.append(h1)
    for p, h in ppos.items():
        if p != planet and p != "Lagna" and h in aspecting_houses:
            woken_by_aspect = True
            break
            
    # 2. Dignity
    is_debilitated = house in PLANET_DEBILITATION.get(planet, [])
    is_exalted = house in PLANET_EXALTATION.get(planet, [])
    is_pakka = house == PLANET_PAKKA_GHAR.get(planet)
    
    return {
        "house": house,
        "woken_by_forward": woken_by_forward,
        "woken_by_aspect": woken_by_aspect,
        "is_debilitated": is_debilitated,
        "is_exalted": is_exalted,
        "is_pakka": is_pakka,
        "woken_by_both": woken_by_forward and woken_by_aspect
    }

def main():
    missed_events_map = load_missed_events()
    with open(GROUND_TRUTH_PATH, "r") as f:
        figures = json.load(f)
        
    evaluator = RashiPhalEvaluator()
    
    tp_stats = []
    fp_stats = []
    
    print("Gathering thermodynamic state metrics for True Positives and False Positives...")

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
                
                # True Positive check
                annual = all_annual.get(f"chart_{age}")
                if annual:
                    a_pos = {p: d["house"] for p, d in annual["planets_in_houses"].items() if p != "Lagna"}
                    triggers = evaluator.evaluate(natal, annual)
                    for trigger in triggers:
                        if trigger["domain"] == target_domain:
                            planet = trigger["triggering_planet"]
                            tp_stats.append(analyze_wakeup_state(planet, a_pos))
                            break
                            
                # False Positive check
                for noise_age in range(max(1, age - NOISE_WINDOW), age + NOISE_WINDOW + 1):
                    if noise_age == age: continue
                    n_annual = all_annual.get(f"chart_{noise_age}")
                    if n_annual:
                        na_pos = {p: d["house"] for p, d in n_annual["planets_in_houses"].items() if p != "Lagna"}
                        n_triggers = evaluator.evaluate(natal, n_annual)
                        for t in n_triggers:
                            if t["domain"] == target_domain:
                                planet = t["triggering_planet"]
                                fp_stats.append(analyze_wakeup_state(planet, na_pos))
                                break
                                
        except Exception as e:
            continue

    print(f"\n===========================================")
    print(f"Rashi Phal False Positive Forensic Analysis")
    print(f"===========================================")
    
    total_tp = len(tp_stats)
    total_fp = len(fp_stats)
    print(f"Total True Positives analyzed: {total_tp}")
    print(f"Total False Positives analyzed: {total_fp}")
    print(f"-------------------------------------------")
    
    def print_stat(key, label):
        tp_rate = (sum(1 for x in tp_stats if x[key]) / max(1, total_tp)) * 100
        fp_rate = (sum(1 for x in fp_stats if x[key]) / max(1, total_fp)) * 100
        delta = tp_rate - fp_rate
        print(f"  {label:<20} | TP: {tp_rate:5.1f}% | FP: {fp_rate:5.1f}% | Diff: {delta:+5.1f}%")

    print_stat("woken_by_forward", "Woken by Forward H.")
    print_stat("woken_by_aspect", "Woken by Aspect")
    print_stat("woken_by_both", "Woken by BOTH")
    print_stat("is_debilitated", "Is Debilitated")
    print_stat("is_exalted", "Is Exalted")
    print_stat("is_pakka", "Is Pakka Ghar")
    
    # House analysis
    print("\n  Top Houses where planet woke up (TP vs FP):")
    tp_houses = defaultdict(int)
    for x in tp_stats: tp_houses[x["house"]] += 1
    fp_houses = defaultdict(int)
    for x in fp_stats: fp_houses[x["house"]] += 1
    
    for house in range(1, 13):
        tp_h_rate = (tp_houses[house] / max(1, total_tp)) * 100
        fp_h_rate = (fp_houses[house] / max(1, total_fp)) * 100
        if tp_h_rate > 0 or fp_h_rate > 0:
            print(f"    House {house:2} | TP: {tp_h_rate:5.1f}% | FP: {fp_h_rate:5.1f}% | Diff: {(tp_h_rate - fp_h_rate):+5.1f}%")

if __name__ == "__main__":
    main()
