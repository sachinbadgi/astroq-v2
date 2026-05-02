import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.getcwd(), "backend")))

from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.quantum_engine.chart_generator import QuantumChartGenerator

JSON_PATH = "backend/data/public_figures_ground_truth.json"

DOMAIN_KARAKAS = {
    "marriage": ["Venus", "Mercury"],
    "career": ["Sun", "Mars", "Jupiter", "Saturn"],
    "career_travel": ["Sun", "Mars", "Jupiter", "Saturn", "Rahu", "Ketu"],
    "health": ["Sun", "Mars", "Saturn"],
    "progeny": ["Jupiter", "Ketu"],
    "real_estate": ["Moon", "Saturn", "Mars"],
    "finance": ["Jupiter", "Venus", "Mercury"]
}

ACTIVE_HOUSES = {
    "marriage": [7, 2],               
    "career": [10, 6, 2],      
    "career_travel": [10, 6, 2, 12, 9],
    "health": [1, 6, 8],             
    "progeny": [5],                
    "real_estate": [4, 8],           
    "finance": [2, 11, 9]                
}

PLANET_MATURITY = {
    "Jupiter": 16, "Sun": 22, "Moon": 24, "Venus": 25, 
    "Mars": 28, "Mercury": 34, "Saturn": 36, "Rahu": 42, "Ketu": 48
}

CYCLE_35_YEAR_RANGES = [
    (1, 6, "Saturn"), (7, 12, "Rahu"), (13, 15, "Ketu"),
    (16, 21, "Jupiter"), (22, 23, "Sun"), (24, 24, "Moon"),
    (25, 27, "Venus"), (28, 33, "Mars"), (34, 35, "Mercury"),
    (36, 41, "Saturn"), (42, 47, "Rahu"), (48, 50, "Ketu"),
    (51, 56, "Jupiter"), (57, 58, "Sun"), (59, 59, "Moon"),
    (60, 62, "Venus"), (63, 68, "Mars"), (69, 70, "Mercury"),
    (71, 75, "Saturn")
]

def get_35_year_ruler(age: int) -> str:
    for start, end, planet in CYCLE_35_YEAR_RANGES:
        if start <= age <= end:
            return planet
    return "Unknown"

def is_event_triggered(planet_data, domain, age, karaka_name):
    if not planet_data: return False
    amp = planet_data.get("amplitude", 0)
    house = planet_data.get("house", 0)
    
    active_houses = ACTIVE_HOUSES.get(domain, [1,4,7,10])
    
    if age != 99:
        maturity_age = PLANET_MATURITY.get(karaka_name, 0)
        if age < maturity_age:
            amp *= 0.5
            
        is_ruler = (get_35_year_ruler(age) == karaka_name)
        if not is_ruler:
            # STRICT DORMANT (SOYI HUI) RULE
            # Planet does not exert a 'measurement' until awakened
            amp *= 0.1
        else:
            amp += 1.0
        
    return amp >= 2.0 and house in active_houses

figures = json.load(open(JSON_PATH))
base_generator = ChartGenerator()
q_generator = QuantumChartGenerator("backend/astroq/quantum_engine/quantum_weights.json")

total_hits = 0
total_events = 0
for fig in figures:
    events = fig.get("events", [])
    if not events: continue
    
    payload = base_generator.build_full_chart_payload(
        dob_str=fig['dob'], tob_str=fig.get('tob', '12:00'),
        place_name=fig.get('birth_place', 'New Delhi'),
        latitude=fig.get('lat', 28.61), longitude=fig.get('lon', 77.20),
        utc_string=fig.get('tz', '+05:30'),
        chart_system="vedic"
    )
    natal_data = payload["chart_0"]
    timeline = q_generator.generate_quantum_timeline(natal_data, max_years=75)
    
    for ev in events:
        domain = ev.get("domain", "").lower()
        actual_age = ev.get("age")
        karakas = DOMAIN_KARAKAS.get(domain)
        if not karakas: continue
        total_events += 1
        
        predicted_ages = []
        for age in range(1, 76):
            chart_key = f"chart_{age}"
            annual_chart = timeline.get(chart_key, {})
            for karaka in karakas:
                annual_karaka_data = annual_chart.get("planets_in_houses", {}).get(karaka)
                if is_event_triggered(annual_karaka_data, domain, age, karaka):
                    predicted_ages.append(age)
                    break
        
        if fig['name'] == 'Narendra Modi':
            print(f"MODI | EVENT: {ev['description']} | Actual: {actual_age} | Predicted Array: {predicted_ages}")
            
        for a in predicted_ages:
            if abs(a - actual_age) <= 1:
                total_hits += 1
                break

print(f"\nTotal Events: {total_events}")
print(f"Timing Hits: {total_hits} ({(total_hits/total_events)*100:.2f}%)")
