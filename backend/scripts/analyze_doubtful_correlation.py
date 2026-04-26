"""
Analyze Doubtful Correlation
============================

This script analyzes the correlation between actual life events (from the ground truth dataset)
and the Varshphal (Annual) states of planets involved in "Doubtful Promises" from the Natal Chart.

It aims to answer: When a person has a "Doubtful" natal setup (e.g., Rahu H5), and a major
event occurs in their life, what is the annual state of Rahu? Is it more likely to be exalted?
debilitated? dormant? compared to random non-event years?
"""

import json
import os
import sys
from collections import defaultdict
from typing import Any, Dict, List

# Ensure backend is importable
_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.normpath(os.path.join(_HERE, ".."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.doubtful_timing_engine import DoubtfulTimingEngine

GROUND_TRUTH_PATH = os.path.join(_BACKEND, "data", "public_figures_ground_truth.json")
NOISE_WINDOW = 3 # years before and after event to use as noise


def load_ground_truth() -> List[Dict[str, Any]]:
    with open(GROUND_TRUTH_PATH, "r") as f:
        return json.load(f)

def get_planet_annual_state(engine: DoubtfulTimingEngine, planet: str, natal_pos: dict, annual_pos: dict) -> dict:
    """Returns a dict of boolean states for a planet in a given annual chart."""
    from astroq.lk_prediction.lk_constants import PLANET_PAKKA_GHAR, PLANET_EXALTATION, PLANET_DEBILITATION
    
    annual_house = annual_pos.get(planet)
    if not annual_house:
        return {}

    states = {
        "is_pakka_ghar": PLANET_PAKKA_GHAR.get(planet) == annual_house,
        "is_exalted": annual_house in PLANET_EXALTATION.get(planet, []),
        "is_debilitated": annual_house in PLANET_DEBILITATION.get(planet, []),
        "is_180_blocked": engine._has_180_degree_block(planet, annual_house, annual_pos),
        "is_dormant": engine._is_planet_dormant(planet, annual_house, annual_pos),
        "is_nisht_h8_strike": natal_pos.get(planet) == 8 and annual_house in [6, 7, 8],
    }
    return states

def main():
    print("Loading figures...")
    figures = load_ground_truth()
    engine = DoubtfulTimingEngine()
    
    event_stats = defaultdict(int)
    noise_stats = defaultdict(int)
    total_events_with_doubtful = 0
    total_noise_with_doubtful = 0
    
    for figure in figures:
        try:
            gen = ChartGenerator()
            place = figure.get("birth_place", "India")
            locations = gen.geocode_place(place)
            if not locations:
                lat, lon, utc = 20.0, 77.0, "+05:30"
            else:
                loc = locations[0]
                lat, lon, utc = loc["latitude"], loc["longitude"], loc["utc_offset"]
            
            natal = gen.generate_chart(figure["dob"], figure.get("tob", "12:00"), place, lat, lon, utc, "vedic")
            natal_pos = engine._get_planetary_positions(natal)
            
            doubtful_promises = engine._identify_doubtful_natal_promises(natal)
            if not doubtful_promises:
                continue # Skip figures without any doubtful setups
                
            all_annual = gen.generate_annual_charts(natal, max_years=100)
            
            for event in figure.get("events", []):
                event_age = event["age"]
                
                # Check event year
                if f"chart_{event_age}" in all_annual:
                    annual_chart = all_annual[f"chart_{event_age}"]
                    annual_pos = engine._get_planetary_positions(annual_chart)
                    total_events_with_doubtful += 1
                    
                    # Accumulate states for planets involved in doubtful promises
                    for promise in doubtful_promises:
                        for planet in promise["planets"]:
                            states = get_planet_annual_state(engine, planet, natal_pos, annual_pos)
                            for state_name, is_true in states.items():
                                if is_true:
                                    event_stats[state_name] += 1
                                    
                # Check noise years
                for noise_age in range(max(1, event_age - NOISE_WINDOW), event_age + NOISE_WINDOW + 1):
                    if noise_age == event_age:
                        continue
                    if f"chart_{noise_age}" in all_annual:
                        annual_chart = all_annual[f"chart_{noise_age}"]
                        annual_pos = engine._get_planetary_positions(annual_chart)
                        total_noise_with_doubtful += 1
                        
                        for promise in doubtful_promises:
                            for planet in promise["planets"]:
                                states = get_planet_annual_state(engine, planet, natal_pos, annual_pos)
                                for state_name, is_true in states.items():
                                    if is_true:
                                        noise_stats[state_name] += 1
        except Exception as e:
            # Skip errors
            continue

    print(f"\n===========================================")
    print(f"Doubtful Promise Correlation Analysis")
    print(f"===========================================")
    print(f"Total Event Years analyzed (w/ Doubtful Promise): {total_events_with_doubtful}")
    print(f"Total Noise Years analyzed (w/ Doubtful Promise): {total_noise_with_doubtful}")
    print("\nState Frequencies (per year, averaged across involved planets):")
    
    all_states = set(event_stats.keys()).union(set(noise_stats.keys()))
    for state in sorted(all_states):
        event_freq = (event_stats[state] / max(1, total_events_with_doubtful)) * 100
        noise_freq = (noise_stats[state] / max(1, total_noise_with_doubtful)) * 100
        delta = event_freq - noise_freq
        
        print(f"  {state:<20} | Event: {event_freq:5.1f}% | Noise: {noise_freq:5.1f}% | Delta: {delta:+5.1f}%")

if __name__ == "__main__":
    main()
