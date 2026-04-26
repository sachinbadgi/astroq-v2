import json
import os
import sys
import re

sys.path.append(os.path.abspath(os.path.join(os.getcwd(), "backend")))

from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.quantum_engine.chart_generator import QuantumChartGenerator
from astroq.quantum_engine.config import load_quantum_weights, QuantumConfig

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
    "career_travel": [10, 6, 2, 12, 9], # combined career and foreign
    "health": [1, 6, 8],             
    "progeny": [5],                
    "real_estate": [4, 8],           
    "finance": [2, 11, 9]                
}

PLANET_MATURITY = {
    "Jupiter": 16,
    "Sun": 22,
    "Moon": 24,
    "Venus": 25,
    "Mars": 28,
    "Mercury": 34,
    "Saturn": 36,
    "Rahu": 42,
    "Ketu": 48
}

def fetch_ground_truth():
    if not os.path.exists(JSON_PATH):
        print(f"Error: {JSON_PATH} not found.")
        return []
        
    with open(JSON_PATH, 'r') as f:
        return json.load(f)

def update_config(masnui_multiplier, annual_rotation):
    """Writes a new config to JSON to be picked up by the generator."""
    data = {
      "amplitudes": {
        "exaltation": 2,
        "debilitation": -1,
        "superposed": 0
      },
      "multipliers": {
        "masnui_entanglement": masnui_multiplier,
        "annual_rotation": annual_rotation
      }
    }
    with open(CONFIG_PATH, 'w') as f:
        json.dump(data, f, indent=2)

def calculate_quantum_whr(timeline: dict, ground_truth_events: list, amp_threshold: float = 1.0) -> float:
    score = 0.0
    total = len(ground_truth_events)
    if total == 0: return 0.0
    
    for gt in ground_truth_events:
        gt_age = gt["age"]
        gt_domain = gt["domain"].lower()
        karakas = DOMAIN_KARAKAS.get(gt_domain, [])
        active_houses = ACTIVE_HOUSES.get(gt_domain, [1,4,7,10])
        
        if not karakas:
            continue
            
        # Check the timeline at that age and nearby ages
        target_ages = [gt_age, gt_age - 1, gt_age + 1]
        
        hit_found = False
        for age in target_ages:
            chart_key = f"chart_{age}"
            if chart_key in timeline:
                annual_chart = timeline[chart_key]
                
                # Check ALL key planets for the domain
                for karaka in karakas:
                    p_data = annual_chart.get("planets_in_houses", {}).get(karaka)
                    
                    if p_data:
                        amp = p_data.get("amplitude", 0)
                        house = p_data.get("house", 0)
                        
                        # Apply maturity multiplier
                        maturity_age = PLANET_MATURITY.get(karaka, 0)
                        if age < maturity_age:
                            amp *= 0.5  # dampen signal before maturity
                        
                        if amp >= amp_threshold and house in active_houses:
                            if age == gt_age:
                                score += 1.0
                            else:
                                score += 0.5
                            hit_found = True
                            break # break out of karaka loop
                if hit_found:
                    break # break out of age loop
                        
    return score / total

def run_optimization():
    print("Loading Public Figures...")
    figures = fetch_ground_truth()
    print(f"Loaded {len(figures)} figures with ground truth events.")
    
    if not figures:
        return

    # To avoid re-fetching charts from the web/SWISS ephemeris every loop, we pre-calculate the base natal charts once.
    print("Pre-calculating base natal charts using ChartGenerator (this may take a moment)...")
    base_generator = ChartGenerator()
    for fig in figures:
        # Avoid geocoding issues if lat/lon not present by passing 0.0
        try:
            payload = base_generator.build_full_chart_payload(
                dob_str=fig['dob'],
                tob_str=fig.get('tob', '12:00'),
                place_name=fig.get('birth_place', 'New Delhi, India'),
                latitude=fig.get('lat', 28.6139),
                longitude=fig.get('lon', 77.2090),
                utc_string=fig.get('tz', '+05:30')
            )
            fig['natal_data'] = payload["chart_0"]
        except Exception as e:
            print(f"Warning: Failed to generate base chart for {fig['name']} ({e})")
            fig['natal_data'] = None

    # Filter out figures that failed
    figures = [f for f in figures if f.get('natal_data') is not None]

    # Define grid to search
    masnui_grid = [0.5, 1.0, 1.5]
    annual_grid = [0.8, 1.0, 1.2]
    amp_grid = [0.5, 1.0, 1.5, 2.0]
    
    best_score = -1
    best_params = {}
    
    print("Starting Auto-Research Grid Search...")
    for masnui in masnui_grid:
        for annual in annual_grid:
            update_config(masnui, annual)
            
            generator = QuantumChartGenerator(CONFIG_PATH)
            
            # Pre-generate timelines to save time across amp_grid
            timelines = []
            for fig in figures:
                timeline = generator.generate_quantum_timeline(fig["natal_data"], max_years=75)
                timelines.append({"timeline": timeline, "events": fig["events"]})
                
            for amp in amp_grid:
                total_whr = 0.0
                for item in timelines:
                    whr = calculate_quantum_whr(item["timeline"], item["events"], amp_threshold=amp)
                    total_whr += whr
                    
                avg_score = total_whr / len(figures)
                print(f"  Params [masnui={masnui}, annual={annual}, amp_thresh={amp}] => WHR Score: {avg_score:.4f}")
                
                if avg_score > best_score:
                    best_score = avg_score
                    best_params = {"masnui_entanglement": masnui, "annual_rotation": annual, "amp_threshold": amp}
                
    print("\n=========================================")
    print(f"BEST CONFIGURATION FOUND:")
    print(f"  Masnui Entanglement Multiplier: {best_params['masnui_entanglement']}")
    print(f"  Annual Rotation Boost: {best_params['annual_rotation']}")
    print(f"  Optimal Amplitude Threshold: {best_params['amp_threshold']}")
    print(f"  Maximized WHR Score: {best_score:.4f}")
    print("=========================================")
    
    # Save the best parameters back
    print("Saving optimal configuration to quantum_weights.json...")
    update_config(best_params['masnui_entanglement'], best_params['annual_rotation'])

if __name__ == "__main__":
    run_optimization()
