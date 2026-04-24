import os
import sys
import json

sys.path.append(os.path.join(os.getcwd(), "backend"))

from astroq.lk_prediction.pipeline import LKPredictionPipeline
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.chart_generator import ChartGenerator
from scripts.verify_pipeline_timing import GEO_MAP

def check_false_positives():
    cfg = ModelConfig(db_path="backend/data/rules.db", defaults_path="backend/data/defaults.json")
    pipeline = LKPredictionPipeline(cfg)
    generator = ChartGenerator()
    
    data_path = os.path.join("backend", "data", "public_figures_ground_truth.json")
    with open(data_path, "r") as f:
        figures = json.load(f)
        
    total_person_years = 0
    true_positives = 0
    false_positives = 0
    true_negatives = 0
    false_negatives = 0
    
    print("Calculating False Positive Rate across all 75 years for all figures...")
    
    for fig in figures:
        name = fig["name"]
        events = fig.get("events", [])
        if not events: continue
        
        # Create a set of all event ages (with +/- 1 year window)
        event_ages = set()
        for ev in events:
            age = ev.get("age")
            if age:
                event_ages.add(age - 1)
                event_ages.add(age)
                event_ages.add(age + 1)
                
        dob = fig["dob"]
        tob = fig["tob"]
        if len(tob.split(":")) == 2: tob += ":00"
        place = fig.get("birth_place", "New Delhi, India")
        lat, lon, tz = GEO_MAP.get(place, (28.6139, 77.2090, "+05:30"))
        
        try:
            payload = generator.build_full_chart_payload(
                dob_str=dob, tob_str=tob, place_name=place, 
                latitude=lat, longitude=lon, utc_string=tz, chart_system="vedic"
            )
        except Exception as e:
            continue
            
        charts = list(payload.values())
        report = pipeline.generate_full_payload(name, dob, charts)
        
        for annual_data in report["annual_timeline"]:
            age = annual_data["age"]
            if age > 75: continue
            
            total_person_years += 1
            
            # Check if pipeline fired a timing signal
            fired = False
            for p_text in annual_data["predictions"]:
                if "[HIGH]" in p_text or "[MEDIUM]" in p_text:
                    fired = True
                    break
                    
            had_event = age in event_ages
            
            if fired and had_event:
                true_positives += 1
            elif fired and not had_event:
                false_positives += 1
            elif not fired and not had_event:
                true_negatives += 1
            elif not fired and had_event:
                false_negatives += 1

    print(f"\\n{'='*50}")
    print(f"FALSE POSITIVE ANALYSIS REPORT")
    print(f"{'='*50}")
    print(f"Total Person-Years Analyzed: {total_person_years}")
    print(f"True Positives (Signal + Event): {true_positives}")
    print(f"False Positives (Signal, No Event): {false_positives}")
    print(f"True Negatives (No Signal, No Event): {true_negatives}")
    print(f"False Negatives (No Signal, Event): {false_negatives}")
    
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    fpr = false_positives / (false_positives + true_negatives) if (false_positives + true_negatives) > 0 else 0
    
    print(f"\\nFalse Positive Rate (FPR): {fpr*100:.2f}% (Years without events that were incorrectly flagged)")
    print(f"Precision: {precision*100:.2f}% (When the engine fires, how often is there an event?)")
    print(f"Total Noise Reduction: Out of {total_person_years} years, the engine correctly remained silent for {true_negatives} years!")

if __name__ == "__main__":
    check_false_positives()
