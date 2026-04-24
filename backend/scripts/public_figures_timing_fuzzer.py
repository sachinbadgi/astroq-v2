import os
import sys
import json
import logging

sys.path.append(os.path.join(os.getcwd(), "backend"))

from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.lk_constants import PLANET_PAKKA_GHAR, PLANET_EXALTATION, PLANET_DEBILITATION

# Quick geocode dictionary for public figures
GEO_MAP = {
    "Allahabad, India": (25.4358, 81.8463, "+05:30"),
    "Mumbai, India": (19.0760, 72.8777, "+05:30"),
    "Vadnagar, India": (23.7801, 72.6373, "+05:30"),
    "San Francisco, California, US": (37.7749, -122.4194, "-08:00"),
    "Seattle, Washington, US": (47.6062, -122.3321, "-08:00"),
    "Sandringham, Norfolk, UK": (52.8311, 0.5054, "+00:00"),
    "New Delhi, India": (28.6139, 77.2090, "+05:30"),
    "Gary, Indiana, US": (41.5934, -87.3464, "-06:00"),
    "Pretoria, South Africa": (-25.7479, 28.2293, "+02:00"),
    "Porbandar, India": (21.6417, 69.6293, "+05:30"),
    "Raisen, India": (23.3308, 77.7788, "+05:30"),
    "Madanapalle, India": (13.5562, 78.5020, "+05:30"),
    "Indore, India": (22.7196, 75.8577, "+05:30"),
    "Jamshedpur, India": (22.8046, 86.2029, "+05:30"),
    "Jamaica Hospital, Queens, New York, US": (40.7028, -73.8152, "-05:00"),
    "Honolulu, Hawaii, US": (21.3069, -157.8583, "-10:00"),
    "Scranton, Pennsylvania, US": (41.4090, -75.6624, "-05:00"),
    "Mayfair, London, UK": (51.5100, -0.1458, "+00:00"),
    "Buckingham Palace, London, UK": (51.5014, -0.1419, "+00:00"),
    "Skopje, North Macedonia": (42.0003, 21.4280, "+01:00")
}

def is_doubtful_placement(planet, ppos):
    if planet == "Venus" and ppos.get("Venus") == 4: return True
    if planet == "Sun" and ppos.get("Sun") == 4 and ppos.get("Saturn") == 10: return True
    if planet == "Saturn" and ppos.get("Saturn") == 10 and ppos.get("Sun") == 4: return True
    return False

def check_states(ppos):
    states = []
    for planet, house in ppos.items():
        if house == PLANET_PAKKA_GHAR.get(planet): states.append((planet, "Pakka Ghar"))
        if house in PLANET_EXALTATION.get(planet, []): states.append((planet, "Exalted"))
        if house in PLANET_DEBILITATION.get(planet, []): states.append((planet, "Debilitated"))
        if is_doubtful_placement(planet, ppos): states.append((planet, "Doubtful"))
    return states

def run_public_figures_timing_fuzzer():
    print(f"=== Starting Public Figures Timing Fuzzer ===")
    
    generator = ChartGenerator()
    data_path = os.path.join("backend", "data", "public_figures_ground_truth.json")
    
    with open(data_path, "r") as f:
        figures = json.load(f)
        
    total_events = 0
    confirmed_events = 0
    
    for fig in figures:
        name = fig["name"]
        dob = fig["dob"]
        tob = fig["tob"]
        if len(tob.split(":")) == 2:
            tob = tob + ":00" # pad seconds if missing
            
        place = fig.get("birth_place", "New Delhi, India")
        lat, lon, tz = GEO_MAP.get(place, (28.6139, 77.2090, "+05:30"))
        
        # We only generate charts specifically for the years/ages of the events to save time
        print(f"\\nAnalyzing {name}...")
        
        try:
            payload = generator.build_full_chart_payload(
                dob_str=dob, tob_str=tob, place_name=place, 
                latitude=lat, longitude=lon, utc_string=tz, chart_system="vedic"
            )
        except Exception as e:
            print(f"  Error generating payload for {name}: {e}")
            continue
            
        for event in fig.get("events", []):
            age = event.get("age")
            year = event.get("year")
            desc = event.get("description")
            total_events += 1
            
            # Find the Annual Chart for this age
            annual_chart_key = f"chart_{age}"
            if annual_chart_key not in payload:
                # Some charts might use index offset, let's try finding by age
                found_key = None
                for k, v in payload.items():
                    if k.startswith("chart_") and v.get("chart_type") == "Yearly" and v.get("chart_period") == age:
                        found_key = k
                        break
                if found_key:
                    annual_chart_key = found_key
                else:
                    print(f"  [Event Age {age}] {desc} - Could not find Annual Chart!")
                    continue
                    
            annual_chart = payload[annual_chart_key]
            ppos_annual = {p: d["house"] for p, d in annual_chart["planets_in_houses"].items() if p != "Lagna"}
            annual_states = check_states(ppos_annual)
            
            if not annual_states:
                print(f"  [Age {age}] {desc} - No structural pattern in Annual Chart.")
                continue
                
            # Check Monthly charts
            monthly_charts = []
            for m in range(1, 13):
                m_chart = generator.generate_monthly_chart(annual_chart, m)
                monthly_charts.append({p: d["house"] for p, d in m_chart["planets_in_houses"].items() if p != "Lagna"})
                
            confirmed = False
            confirming_months = []
            confirming_states = []
            
            for planet, state_type in annual_states:
                for m_idx, mc in enumerate(monthly_charts):
                    m_states = check_states(mc)
                    if (planet, state_type) in m_states:
                        confirmed = True
                        confirming_months.append(m_idx + 1)
                        confirming_states.append(f"{planet} ({state_type})")
                        
            if confirmed:
                confirmed_events += 1
                states_str = ", ".join(set(confirming_states))
                months_str = ", ".join(map(str, set(confirming_months)))
                print(f"  [Age {age}] {desc} - ✓ DOUBLE CONFIRMED: {states_str} peaked in Month(s) {months_str}")
            else:
                states_str = ", ".join([f"{p}({s})" for p, s in annual_states])
                print(f"  [Age {age}] {desc} - ✗ Annual pattern {states_str} did not double-confirm.")

    print("\\n" + "="*50)
    print("      PUBLIC FIGURES DOUBLE-CONFIRMATION REPORT")
    print("="*50)
    if total_events > 0:
        rate = (confirmed_events / total_events) * 100
        print(f"Total Life Events Analyzed: {total_events}")
        print(f"Events with Double Confirmation (Pattern peaking in a specific month): {confirmed_events} ({rate:.1f}%)")

if __name__ == "__main__":
    run_public_figures_timing_fuzzer()
