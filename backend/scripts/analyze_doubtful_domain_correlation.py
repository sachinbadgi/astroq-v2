"""
Analyze Doubtful Domain Correlation
===================================
Checks if a Doubtful Promise planet moves into a house related to the event domain.
"""

import json
import os
import sys
from collections import defaultdict
from typing import Any, Dict, List

_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.normpath(os.path.join(_HERE, ".."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.doubtful_timing_engine import DoubtfulTimingEngine

GROUND_TRUTH_PATH = os.path.join(_BACKEND, "data", "public_figures_ground_truth.json")
NOISE_WINDOW = 3

DOMAIN_HOUSES = {
    "marriage": [7, 2],
    "health": [6, 8, 12, 1],
    "career_travel": [10, 9, 3, 12],
    "progeny": [5, 9],
    "finance": [2, 11]
}

def load_ground_truth() -> List[Dict[str, Any]]:
    with open(GROUND_TRUTH_PATH, "r") as f:
        return json.load(f)

def is_planet_in_domain_houses(planet: str, annual_pos: dict, domain: str) -> bool:
    house = annual_pos.get(planet)
    return house in DOMAIN_HOUSES.get(domain, [])

def main():
    figures = load_ground_truth()
    engine = DoubtfulTimingEngine()
    
    event_stats = defaultdict(int)
    noise_stats = defaultdict(int)
    total_events = 0
    total_noise = 0
    
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
                continue
                
            all_annual = gen.generate_annual_charts(natal, max_years=100)
            
            for event in figure.get("events", []):
                event_age = event["age"]
                domain = event.get("domain", "")
                
                if f"chart_{event_age}" in all_annual:
                    annual_chart = all_annual[f"chart_{event_age}"]
                    annual_pos = engine._get_planetary_positions(annual_chart)
                    total_events += 1
                    
                    for promise in doubtful_promises:
                        for planet in promise["planets"]:
                            if is_planet_in_domain_houses(planet, annual_pos, domain):
                                event_stats["in_domain_house"] += 1
                                    
                for noise_age in range(max(1, event_age - NOISE_WINDOW), event_age + NOISE_WINDOW + 1):
                    if noise_age == event_age:
                        continue
                    if f"chart_{noise_age}" in all_annual:
                        annual_chart = all_annual[f"chart_{noise_age}"]
                        annual_pos = engine._get_planetary_positions(annual_chart)
                        total_noise += 1
                        
                        for promise in doubtful_promises:
                            for planet in promise["planets"]:
                                if is_planet_in_domain_houses(planet, annual_pos, domain):
                                    noise_stats["in_domain_house"] += 1
        except Exception:
            continue

    print(f"\n===========================================")
    print(f"Domain House Correlation")
    print(f"===========================================")
    print(f"Total Event Years analyzed: {total_events}")
    print(f"Total Noise Years analyzed: {total_noise}")
    
    event_freq = (event_stats["in_domain_house"] / max(1, total_events)) * 100
    noise_freq = (noise_stats["in_domain_house"] / max(1, total_noise)) * 100
    delta = event_freq - noise_freq
    
    print(f"  in_domain_house | Event: {event_freq:5.1f}% | Noise: {noise_freq:5.1f}% | Delta: {delta:+5.1f}%")

if __name__ == "__main__":
    main()
