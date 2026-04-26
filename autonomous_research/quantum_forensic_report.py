import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.getcwd(), "backend")))

from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.quantum_engine.chart_generator import QuantumChartGenerator

JSON_PATH = "backend/data/public_figures_ground_truth.json"
CONFIG_PATH = "backend/astroq/quantum_engine/quantum_weights.json"

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
    (25, 27, "Venus"), (28, 33, "Mars"), (34, 35, "Mercury")
]

def get_35_year_ruler(age):
    period = (age - 1) % 35 + 1
    for start, end, planet in CYCLE_35_YEAR_RANGES:
        if start <= period <= end:
            return planet
    return None

def is_event_triggered(planet_data, domain, age, karaka_name):
    """Determines if the quantum engine predicts the event based on amplitude, maturity, 35-year cycle, and house."""
    if not planet_data: return False
    amp = planet_data.get("amplitude", 0)
    house = planet_data.get("house", 0)
    
    active_houses = ACTIVE_HOUSES.get(domain, [1,4,7,10])
    
    if age != 99:
        maturity_age = PLANET_MATURITY.get(karaka_name, 0)
        if age < maturity_age:
            amp *= 0.5
            
        # The 35-Year Cycle "Awakening" Trigger
        if get_35_year_ruler(age) == karaka_name:
            amp += 1.0
        
    return amp >= 1.5 and house in active_houses

def fetch_ground_truth():
    if not os.path.exists(JSON_PATH):
        print(f"Error: {JSON_PATH} not found.")
        return []
        
    with open(JSON_PATH, 'r') as f:
        return json.load(f)

def generate_forensic_report():
    print("Loading Public Figures Data...")
    figures = fetch_ground_truth()
    if not figures: return

    print("Initializing Quantum Engine...")
    base_generator = ChartGenerator()
    quantum_generator = QuantumChartGenerator(CONFIG_PATH)
    
    total_events = 0
    natal_promises = 0
    annual_hits = 0
    
    report_lines = []
    
    report_lines.append("==================================================================")
    report_lines.append("           QUANTUM ENGINE FORENSIC TIMING REPORT                  ")
    report_lines.append("==================================================================\n")

    for fig in figures:
        name = fig.get("name", "Unknown")
        events = fig.get("events", [])
        if not events: continue

        try:
            payload = base_generator.build_full_chart_payload(
                dob_str=fig['dob'], tob_str=fig.get('tob', '12:00'),
                place_name=fig.get('birth_place', 'New Delhi'),
                latitude=fig.get('lat', 28.61), longitude=fig.get('lon', 77.20),
                utc_string=fig.get('tz', '+05:30'),
                chart_system="vedic"
            )
            natal_data = payload["chart_0"]
        except Exception as e:
            continue
            
        timeline = quantum_generator.generate_quantum_timeline(natal_data, max_years=75)
        natal_quantum_chart = timeline.get("chart_0", {})
        
        for ev in events:
            actual_age = ev.get("age")
            domain = ev.get("domain", "").lower()
            desc = ev.get("description", "")
            
            karakas = DOMAIN_KARAKAS.get(domain)
            if not karakas: continue
            total_events += 1
            
            report_lines.append(f"FIGURE: {name} | EVENT: {desc}")
            report_lines.append(f"  -> Ground Truth Age: {actual_age} | Domain: {domain} | Karakas: {karakas}")
            
            # --- Check Natal Promise ---
            has_promise = False
            for karaka in karakas:
                natal_karaka_data = natal_quantum_chart.get("planets_in_houses", {}).get(karaka)
                # Pass 99 as age for natal chart to bypass maturity dampening (natal promise is a lifetime potential)
                if is_event_triggered(natal_karaka_data, domain, 99, karaka):
                    has_promise = True
                    natal_promises += 1
                    n_house = natal_karaka_data.get('house')
                    report_lines.append(f"  -> Natal Promise: YES (Karaka {karaka} sits in active house {n_house})")
                    break
            
            if not has_promise:
                report_lines.append(f"  -> Natal Promise: NO (No Karaka in structurally active house)")
            
            # --- Scan all 75 years for Triggers ---
            predicted_ages = []
            for age in range(1, 76):
                annual_chart = timeline.get(f"chart_{age}", {})
                for karaka in karakas:
                    annual_karaka_data = annual_chart.get("planets_in_houses", {}).get(karaka)
                    if is_event_triggered(annual_karaka_data, domain, age, karaka):
                        predicted_ages.append(age)
                        break
            
            report_lines.append(f"  -> Predicted Trigger Ages: {predicted_ages}")
            
            # --- Check Match ---
            # Hit if the engine predicted the event in the exact year, or +/- 1 year
            if actual_age in predicted_ages or (actual_age - 1) in predicted_ages or (actual_age + 1) in predicted_ages:
                annual_hits += 1
                report_lines.append(f"  -> Match with Ground Truth: YES! (Engine successfully hit the window)")
            else:
                report_lines.append(f"  -> Match with Ground Truth: NO.")
                
            report_lines.append("-" * 66)

    # Summary
    report_lines.append("\n==================================================================")
    report_lines.append("                          SUMMARY STATS                           ")
    report_lines.append("==================================================================")
    report_lines.append(f"Total Events Analyzed        : {total_events}")
    report_lines.append(f"Natal Promise Confirmed      : {natal_promises} ({(natal_promises/total_events)*100 if total_events else 0:.2f}%)")
    report_lines.append(f"Accurate Timing Match (+/-1) : {annual_hits} ({(annual_hits/total_events)*100 if total_events else 0:.2f}%)")
    report_lines.append("==================================================================")

    output_file = "autonomous_research/forensic_output.txt"
    with open(output_file, "w") as f:
        f.write("\n".join(report_lines))
        
    print(f"\nDetailed forensic report generated and saved to: {output_file}")
    print("\n" + "\n".join(report_lines[-8:]))

if __name__ == "__main__":
    generate_forensic_report()
