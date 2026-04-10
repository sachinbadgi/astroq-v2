import sys
import os
import sqlite3
import json

# Ensure backend is in path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.pipeline import LKPredictionPipeline

def audit_jobs():
    db_path = "backend/data/astroq_gt.db"
    defaults_path = "backend/data/model_defaults.json"
    
    config = ModelConfig(db_path=db_path, defaults_path=defaults_path)
    generator = ChartGenerator()
    pipeline = LKPredictionPipeline(config)
    
    # 1. Birth Data for Steve Jobs
    person_dob = "1955-02-24"
    person_tob = "19:15"
    person_place = "San Francisco, California"
    person_lat = 37.7749
    person_lon = -122.4194
    person_tz = "-08:00" # PST
    
    # 2. Generate Chart Payload
    natal_chart = generator.generate_chart(
        dob_str=person_dob,
        tob_str=person_tob,
        place_name=person_place,
        latitude=person_lat,
        longitude=person_lon,
        utc_string=person_tz
    )
    annual_charts = generator.generate_annual_charts(natal_chart, max_years=75)
    
    # 3. Load Natal Baseline
    pipeline.load_natal_baseline(natal_chart)
    
    # 4. Audit Ages 20 to 30
    print(f"\n{'Age':<5} | {'Domain':<15} | {'Score':<6} | {'Rules'}")
    print("-" * 80)
    
    for age in range(20, 31):
        chart_key = f"chart_{age}"
        if age == 0:
             predictions = pipeline.generate_predictions(natal_chart)
        else:
             predictions = pipeline.generate_predictions(annual_charts[chart_key])
             
        # Filter and print
        for p in predictions:
            # We show all predictions with prob > 0.4 to see the "noise"
            rules_str = ", ".join(p.source_rules[:3])
            if len(p.source_rules) > 3: rules_str += "..."
            
            print(f"{age:<5} | {p.domain:<15} | {p.probability:.2f} | {rules_str}")

if __name__ == "__main__":
    audit_jobs()
