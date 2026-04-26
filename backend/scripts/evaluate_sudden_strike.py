"""
Evaluate Sudden Strike Rule
===========================
Tests deterministic structural geometries for "Takkar" (1-7 collision) and "Nisht Grah"
(House 8 destruction) to see how many True Positives (malefic events caught) and
False Positives (noise years flagged) it generates across the public figures dataset.
"""

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.normpath(os.path.join(_HERE, ".."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from astroq.lk_prediction.chart_generator import ChartGenerator

GROUND_TRUTH_PATH = os.path.join(_BACKEND, "data", "public_figures_ground_truth.json")
NOISE_WINDOW = 3

def is_sudden_strike(natal_pos: dict, annual_pos: dict):
    """
    Returns (bool, str) indicating if a Sudden Strike geometry exists.
    """
    # 1. Nisht Grah Rule (Natal H8 planet moves to Annual H6, H7, H8)
    for planet, n_house in natal_pos.items():
        if n_house == 8:
            a_house = annual_pos.get(planet)
            if a_house in [6, 7, 8]:
                return True, f"Nisht Grah: {planet} (Natal H8 -> Annual H{a_house})"
                
    # 2. 8th House Malefic Strike (Natal H8 empty, Annual H8 gets a hard malefic)
    natal_h8_empty = not any(h == 8 for p, h in natal_pos.items() if p != "Lagna")
    if natal_h8_empty:
        for malefic in ["Saturn", "Rahu", "Ketu", "Mars"]:
            if annual_pos.get(malefic) == 8:
                return True, f"H8 Strike: {malefic} moved into empty H8"
                
    # 3. 1-7 Takkar (Enemies in 1 and 7)
    # Standard Lal Kitab enemy pairs causing severe sudden clashes
    enemy_pairs = [("Sun", "Saturn"), ("Sun", "Rahu"), ("Moon", "Rahu"), 
                   ("Moon", "Ketu"), ("Jupiter", "Venus"), ("Jupiter", "Rahu")]
    h1_planets = [p for p, h in annual_pos.items() if h == 1 and p != "Lagna"]
    h7_planets = [p for p, h in annual_pos.items() if h == 7 and p != "Lagna"]
    
    for p1 in h1_planets:
        for p2 in h7_planets:
            if (p1, p2) in enemy_pairs or (p2, p1) in enemy_pairs:
                return True, f"1-7 Takkar: {p1} (H1) and {p2} (H7)"
                
    return False, ""

def determine_polarity(description: str, domain: str) -> str:
    desc_lower = description.lower()
    malefic_keywords = ["death", "accident", "fired", "divorce", "loss", "cancer", "arrest", "jail", "collapse", "assassination", "resignation"]
    if any(k in desc_lower for k in malefic_keywords) or domain == "health":
        return "Malefic"
    return "Benefic"

def main():
    with open(GROUND_TRUTH_PATH, "r") as f:
        figures = json.load(f)
        
    total_malefic_events = 0
    true_positives = 0
    tp_reasons = []
    
    total_noise_years = 0
    false_positives = 0
    
    # We will test against the 6 specific "Sudden Strike" misses we found earlier
    missed_target_ages = {
        "Michael Jackson": [51],
        "Salman Khan": [50],
        "Lata Mangeshkar": [93],
        "Queen Elizabeth II": [96],
        "Rajiv Gandhi": [47],
        "Abraham Lincoln": [56]
    }
    targets_caught = []

    print("Generating charts and evaluating Sudden Strike geometry...")
    
    for fig in figures:
        name = fig["name"]
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
            n_pos = {p: d["house"] for p, d in natal["planets_in_houses"].items() if p != "Lagna"}
            
            all_annual = gen.generate_annual_charts(natal, max_years=100)
            
            for event in fig.get("events", []):
                age = event["age"]
                polarity = determine_polarity(event.get("description", ""), event.get("domain", ""))
                
                # Only care about predicting Malefic events with a Malefic rule
                if polarity == "Malefic":
                    total_malefic_events += 1
                    annual = all_annual.get(f"chart_{age}")
                    if annual:
                        a_pos = {p: d["house"] for p, d in annual["planets_in_houses"].items() if p != "Lagna"}
                        hit, reason = is_sudden_strike(n_pos, a_pos)
                        if hit:
                            true_positives += 1
                            tp_reasons.append(f"{name} (Age {age}): {reason}")
                            if name in missed_target_ages and age in missed_target_ages[name]:
                                targets_caught.append(f"{name} (Age {age}): {reason}")
                                
                    # Noise testing around this event (non-event years)
                    for noise_age in range(max(1, age - NOISE_WINDOW), age + NOISE_WINDOW + 1):
                        if noise_age == age:
                            continue
                        n_annual = all_annual.get(f"chart_{noise_age}")
                        if n_annual:
                            total_noise_years += 1
                            na_pos = {p: d["house"] for p, d in n_annual["planets_in_houses"].items() if p != "Lagna"}
                            fp_hit, _ = is_sudden_strike(n_pos, na_pos)
                            if fp_hit:
                                false_positives += 1
                                
        except Exception as e:
            continue

    print(f"\n===========================================")
    print(f"Sudden Strike Pattern Evaluation")
    print(f"===========================================")
    print(f"Total Malefic Events Analyzed: {total_malefic_events}")
    print(f"True Positives (Events Caught): {true_positives} ({(true_positives/max(1, total_malefic_events))*100:.1f}%)")
    print(f"Total Noise Years Analyzed: {total_noise_years}")
    print(f"False Positives (Noise Flagged): {false_positives} ({(false_positives/max(1, total_noise_years))*100:.1f}%)")
    print(f"-------------------------------------------")
    print(f"Did it catch the 6 missed 'Sudden Strikes' from earlier?")
    print(f"Caught {len(targets_caught)} out of 6:")
    for t in targets_caught:
        print(f"  - {t}")

if __name__ == "__main__":
    main()
