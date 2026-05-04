import os
import sys
import json

sys.path.append(os.path.join(os.getcwd(), "backend"))
from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.pipeline import LKPredictionPipeline
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.lk_constants import PLANET_PAKKA_GHAR, PLANET_EXALTATION, PLANET_DEBILITATION

from astroq.lk_prediction.location_provider import GEO_MAP, DEFAULT_GEO

def get_dignity(planet, house):
    if house == PLANET_PAKKA_GHAR.get(planet): return "Pakka Ghar"
    if house in PLANET_EXALTATION.get(planet, []): return "Exalted"
    if house in PLANET_DEBILITATION.get(planet, []): return "Debilitated"
    return "Neutral"

def run_marriage_fuzzer():
    print("=== Marriage Timing Signature Explorer ===")
    
    cfg = ModelConfig(db_path="backend/data/rules.db", defaults_path="backend/data/model_defaults.json")
    generator = ChartGenerator()
    pipeline = LKPredictionPipeline(cfg)
    
    data_path = os.path.join("backend", "data", "public_figures_ground_truth.json")
    with open(data_path, "r") as f: figures = json.load(f)
        
    for fig in figures:
        name = fig["name"]
        
        # Only process figures with a marriage event
        marriage_events = [e for e in fig.get("events", []) if e.get("domain", "") == "marriage"]
        if not marriage_events: continue
            
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
            
        for event in marriage_events:
            age = event.get("age")
            if not age: continue
            
            print(f"\\n--- {name} | MARRIAGE AT AGE {age} ---")
            
            # Analyze a 5-year window around the marriage
            for test_age in range(age - 2, age + 3):
                chart_key = f"chart_{test_age}"
                if chart_key not in payload: continue
                    
                chart = payload[chart_key]
                ppos = {p: d["house"] for p, d in chart["planets_in_houses"].items() if p != "Lagna"}
                
                venus_h = ppos.get("Venus")
                venus_dig = get_dignity("Venus", venus_h)
                moon_h = ppos.get("Moon")
                moon_dig = get_dignity("Moon", moon_h)
                
                # Check for marriage specific rules matching in this annual chart
                preds = pipeline.generate_predictions(chart)
                marriage_rules = []
                for p in preds:
                    if "marriage" in p.prediction_text.lower() or "wife" in p.prediction_text.lower() or "husband" in p.prediction_text.lower():
                        marriage_rules.append(p.source_rules[0])
                        
                marker = "⭐ EVENT YEAR ⭐" if test_age == age else "               "
                
                rule_str = f"Matches {len(marriage_rules)} Marriage Rules" if marriage_rules else "No Marriage Rules"
                print(f"  {marker} Age {test_age} | Venus: H{venus_h} ({venus_dig}) | Moon: H{moon_h} ({moon_dig}) | {rule_str}")

if __name__ == "__main__":
    run_marriage_fuzzer()
