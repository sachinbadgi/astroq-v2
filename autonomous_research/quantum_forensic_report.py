import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.getcwd(), "backend")))

from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.quantum_engine.chart_generator import QuantumChartGenerator

JSON_PATH = "backend/data/public_figures_ground_truth.json"
CONFIG_PATH = "backend/astroq/quantum_engine/quantum_weights.json"

DOMAIN_KARAKA = {
    "marriage": "Venus",
    "career": "Saturn",
    "career_travel": "Saturn",
    "health": "Mars",
    "progeny": "Jupiter",
    "real_estate": "Mars",
    "finance": "Jupiter"
}

# Lal Kitab logical active houses for each domain (where the karaka creates the event)
ACTIVE_HOUSES = {
    "marriage": [2, 7],               # Venus's own and partner house
    "career": [1, 4, 7, 10, 11],      # Kendras and gains
    "career_travel": [1, 4, 7, 10, 11],
    "health": [6, 8, 12],             # Disease, accident/death, hospital
    "progeny": [5, 9],                # Children and fortune
    "real_estate": [4, 10],           # Property
    "finance": [2, 11]                # Wealth and income
}

def fetch_ground_truth():
    if not os.path.exists(JSON_PATH):
        print(f"Error: {JSON_PATH} not found.")
        return []
        
    with open(JSON_PATH, 'r') as f:
        return json.load(f)

def is_event_triggered(planet_data, domain):
    """Determines if the quantum engine predicts the event based on amplitude and house."""
    if not planet_data: return False
    amp = planet_data.get("amplitude", 0)
    house = planet_data.get("house", 0)
    
    active_houses = ACTIVE_HOUSES.get(domain, [1,4,7,10])
    
    # Triggered if it has constructive amplitude AND is rotated into an active house for that domain
    return amp >= 1 and house in active_houses

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
                utc_string=fig.get('tz', '+05:30')
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
            
            karaka = DOMAIN_KARAKA.get(domain)
            if not karaka: continue
            total_events += 1
            
            report_lines.append(f"FIGURE: {name} | EVENT: {desc}")
            report_lines.append(f"  -> Ground Truth Age: {actual_age} | Domain: {domain} | Karaka: {karaka}")
            
            # --- Check Natal Promise ---
            natal_karaka_data = natal_quantum_chart.get("planets_in_houses", {}).get(karaka)
            has_promise = is_event_triggered(natal_karaka_data, domain)
            if has_promise:
                natal_promises += 1
                n_house = natal_karaka_data.get('house')
                report_lines.append(f"  -> Natal Promise: YES (Karaka sits in active house {n_house})")
            else:
                n_house = natal_karaka_data.get('house') if natal_karaka_data else 'None'
                report_lines.append(f"  -> Natal Promise: NO (Karaka in house {n_house}, inactive for {domain})")
            
            # --- Scan all 75 years for Triggers ---
            predicted_ages = []
            for age in range(1, 76):
                annual_chart = timeline.get(f"chart_{age}", {})
                annual_karaka_data = annual_chart.get("planets_in_houses", {}).get(karaka)
                if is_event_triggered(annual_karaka_data, domain):
                    predicted_ages.append(age)
            
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
