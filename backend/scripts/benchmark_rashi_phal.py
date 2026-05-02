"""
Benchmark Rashi Phal Evaluator
==============================
Tests the deterministic thermodynamic (Loss of Dormancy) logic of the RashiPhalEvaluator
against the 25 events missed by the Fixed Fate baseline.
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
from astroq.lk_prediction.astrological_context import UnifiedAstrologicalContext
from astroq.lk_prediction.state_ledger import StateLedger

GROUND_TRUTH_PATH = os.path.join(_BACKEND, "data", "public_figures_ground_truth.json")
REPORT_PATH = os.path.join(_BACKEND, "..", "artifacts", "reports", "doubtful_timing_benchmark_report.json")
NOISE_WINDOW = 3

def determine_polarity(description: str, domain: str) -> str:
    desc_lower = description.lower()
    malefic_keywords = ["death", "accident", "fired", "divorce", "loss", "cancer", "arrest", "jail", "collapse", "assassination", "resignation"]
    if any(k in desc_lower for k in malefic_keywords) or domain == "health":
        return "Malefic"
    return "Benefic"

def load_missed_events():
    """Load the events that the baseline engine missed."""
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
        
    evaluator = VarshphalTimingEngine()
    
    total_missed_events = sum(len(e) for e in missed_events_map.values())
    true_positives = 0
    tp_details = []
    
    total_noise_years = 0
    false_positives = 0
    
    print(f"Loaded {total_missed_events} missed events. Running Rashi Phal Evaluation...")

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
            # Accept both dict and ChartData for compatibility
            try:
                from astroq.lk_prediction.data_contracts import ChartData
                natal_cd = ChartData(**natal) if not hasattr(natal, 'data') else natal
            except Exception:
                natal_cd = natal
            all_annual = gen.generate_annual_charts(natal, max_years=100)
            for event in missed_events_map[name]:
                age = event["age"]
                target_domain = event.get("domain", "")
                annual = all_annual.get(f"chart_{age}")
                if annual:
                    try:
                        annual_cd = ChartData(**annual) if not hasattr(annual, 'data') else annual
                    except Exception:
                        annual_cd = annual
                    context = UnifiedAstrologicalContext(natal_cd, annual_cd, StateLedger(), age)
                    triggers = evaluator.evaluate_rashi_phal_triggers(context, target_domain)
                    caught = len(triggers) > 0
                    if caught:
                        tp_details.append(f"{name} (Age {age} | {target_domain.upper()}): {triggers[0]['desc']}")
                        true_positives += 1
                # Noise testing
                for noise_age in range(max(1, age - NOISE_WINDOW), age + NOISE_WINDOW + 1):
                    if noise_age == age:
                        continue
                    n_annual = all_annual.get(f"chart_{noise_age}")
                    if n_annual:
                        try:
                            n_annual_cd = ChartData(**n_annual) if not hasattr(n_annual, 'data') else n_annual
                        except Exception:
                            n_annual_cd = n_annual
                        context = UnifiedAstrologicalContext(natal_cd, n_annual_cd, StateLedger(), noise_age)
                        n_triggers = evaluator.evaluate_rashi_phal_triggers(context, target_domain)
                        if len(n_triggers) > 0:
                            false_positives += 1
                                
        except Exception as e:
            print(f"Error on {name}: {e}")
            continue

    print(f"\n===========================================")
    print(f"Rashi Phal Evaluator Benchmark")
    print(f"===========================================")
    print(f"Total Missed Events Analyzed: {total_missed_events}")
    print(f"True Positives (Events Caught): {true_positives} ({(true_positives/max(1, total_missed_events))*100:.1f}%)")
    print(f"Total Noise Years Analyzed: {total_noise_years}")
    print(f"False Positives (Noise Flagged): {false_positives} ({(false_positives/max(1, total_noise_years))*100:.1f}%)")
    print(f"-------------------------------------------")
    print(f"Successfully Recovered Events:")
    for d in tp_details:
        print(f"  - {d}")

if __name__ == "__main__":
    main()
