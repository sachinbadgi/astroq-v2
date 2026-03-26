import logging
import sys
import os
from datetime import datetime
from pprint import pprint

# Ensure backend is in path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.lse_orchestrator import LSEOrchestrator
from astroq.lk_prediction.data_contracts import LifeEventLog

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("test_lse_person")

# --- TEST DATA ---
PERSON_DETAILS = {
    "name": "Sachin Tendulkar",
    "dob": "1973-04-24",
    "tob": "16:20:00",
    "place": "Mumbai, India",
    "lat": 18.97,
    "lon": 72.82,
    "tz": "+05:30"
}

LIFE_EVENTS: LifeEventLog = [
    {"age": 16, "domain": "profession", "description": "International Debut", "is_verified": True},
    {"age": 22, "domain": "marriage", "description": "Marriage to Anjali", "is_verified": True},
    {"age": 31, "domain": "health", "description": "Tennis Elbow", "is_verified": True},
    {"age": 38, "domain": "profession", "description": "100th Century", "is_verified": True}
]

def get_interactive_input():
    print("\n--- ENTER PERSON DETAILS ---")
    name = input("Enter Name: ")
    dob = input("Enter Birthday (YYYY-MM-DD): ")
    tob = input("Enter Birth Time (HH:MM:SS): ")
    place = input("Enter Birth Location (e.g. Mumbai, India): ")
    
    lat_in = input("Enter Latitude (optional, press enter to lookup): ")
    lat = float(lat_in) if lat_in else None
    
    lon_in = input("Enter Longitude (optional, press enter to lookup): ")
    lon = float(lon_in) if lon_in else None
    
    tz = input("Enter Timezone (e.g. +05:30): ")

    print("\n--- ENTER LIFE EVENTS (type 'done' to finish) ---")
    life_events = []
    while True:
        age_in = input("\nAge of event: ")
        if age_in.lower() == 'done':
            break
        try:
            age = int(age_in)
            domain = input("Domain (career, marriage, health): ")
            desc = input("Description: ")
            life_events.append({
                "age": age,
                "domain": domain.lower(),
                "description": desc,
                "is_verified": True
            })
        except ValueError:
            print("Invalid age, try again.")
            
    return {
        "name": name,
        "dob": dob,
        "tob": tob,
        "place": place,
        "lat": lat,
        "lon": lon,
        "tz": tz,
        "events": life_events
    }

def test_person_lse():
    """
    Test the LSE feature with a specific person's details and known life events.
    """
    # Ask for input
    choice = input("Run with (1) Interactive Input or (2) Hardcoded Example? [1/2]: ")
    
    if choice == '1':
        details = get_interactive_input()
        person_name = details["name"]
        person_dob = details["dob"]
        person_tob = details["tob"]
        person_place = details["place"]
        person_lat = details["lat"]
        person_lon = details["lon"]
        person_tz = details["tz"]
        events = details["events"]
    else:
        person_name = PERSON_DETAILS["name"]
        person_dob = PERSON_DETAILS["dob"]
        person_tob = PERSON_DETAILS["tob"]
        person_place = PERSON_DETAILS["place"]
        person_lat = PERSON_DETAILS["lat"]
        person_lon = PERSON_DETAILS["lon"]
        person_tz = PERSON_DETAILS["tz"]
        events = LIFE_EVENTS

    # Initialize ModelConfig with correct paths
    config = ModelConfig(
        db_path="backend/data/rules.db",
        defaults_path="backend/data/model_defaults.json"
    )
    
    orchestrator = LSEOrchestrator(config)
    
    # 3. GENERATE CHARTS
    generator = ChartGenerator()
    
    try:
        logger.info(f"Generating full chart payload for {person_name}...")
        full_payload = generator.build_full_chart_payload(
            dob_str=person_dob,
            tob_str=person_tob,
            place_name=person_place,
            latitude=person_lat,
            longitude=person_lon,
            utc_string=str(person_tz) if person_tz else None
        )
        
        natal_chart = full_payload["chart_0"]
        annual_charts = {int(k.split("_")[1]): v for k, v in full_payload.items() if k.startswith("chart_") and k != "chart_0"}
        
        logger.info(f"Generated natal chart and {len(annual_charts)} annual charts.")

        # 4. RUN LSE ORCHESTRATOR
        logger.info("Running LSE Personalization Loop...")
        result = orchestrator.solve_chart(
            birth_chart=natal_chart,
            annual_charts=annual_charts,
            life_event_log=events,
            figure_id=person_name
        )

        # 5. OUTPUT RESULTS
        print("\n" + "="*60)
        print(f"LSE RESULTS FOR: {person_name}")
        print("="*60)
        
        if result.chart_dna:
            dna = result.chart_dna
            print(f"Hit Rate: {dna.back_test_hit_rate * 100:.1f}%")
            print(f"Confidence Score: {dna.confidence_score:.2f}")
            print(f"Mean Offset: {dna.mean_offset_years:.2f} years")
            print(f"Iterations Run: {result.iterations_run}")
            print(f"Converged: {result.converged}")
            
            print("\nDelay Constants Applied:")
            for k, v in dna.delay_constants.items():
                print(f"  - {k}: {v} years")
        else:
            print("No personalization (DNA) generated.")

        print("\n" + "-"*60)
        print("GAP REPORT (HITS)")
        print("-"*60)
        
        max_age = max(e["age"] for e in events) if events else 100
        
        for pred in result.future_predictions:
            if pred.peak_age <= max_age:
                matched_event = next((e for e in events if e["age"] == pred.peak_age and e["domain"] in pred.domain.lower()), None)
                if matched_event:
                    print(f"HIT! Age {pred.peak_age} [{pred.domain}]")
                    print(f"  Matched to: {matched_event['description']}")
                    print(f"  Rule: {pred.source_rules[0] if pred.source_rules else 'N/A'}")
                    print("-" * 30)

    except Exception as e:
        logger.exception(f"Error testing LSE: {e}")

if __name__ == "__main__":
    test_person_lse()
