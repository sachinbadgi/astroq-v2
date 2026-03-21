"""
Test Script: Generate a fully populated JSON chart and predictions from DOB/TOB/POB.

This script uses the newly built Lal Kitab Prediction Model v2 ChartGenerator
and feeds it into our newly built LK Prediction Model v2 Engine.

Usage:
  python generate_test_chart.py

Output:
  A file 'test_output.json' containing the fully populated chart data and the model predictions.
"""

import os
import sys
import json

# 1. Import our newly built Chart Generator v2
from astroq.lk_prediction.chart_generator import ChartGenerator

# 2. Import our newly built Prediction Model v2
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.pipeline import LKPredictionPipeline


def main():
    print("=== Lal Kitab Prediction Model v2 - Manual Accuracy Test ===")
    
    # You can edit these values to test different charts
    dob = "1990-05-15"
    tob = "14:30:00" 
    place = "New Delhi, India"
    chart_system = "kp" # or "vedic"
    client_name = "Test User"

    print(f"1. Generating astronomical full chart payload for {client_name} ({dob} {tob} at {place}) using system '{chart_system}'...")
    
    generator = ChartGenerator()
    full_payload = generator.build_full_chart_payload(
        dob_str=dob,
        tob_str=tob,
        place_name=place,
        chart_system=chart_system
    )
    
    natal_chart = full_payload.get("chart_0")
    if not natal_chart:
        print("Failed to extract `chart_0` from the pipeline payload!")
        sys.exit(1)
        
    print("2. Initializing LK Prediction Engine v2...")
    db_path = os.path.join(os.path.dirname(__file__), "data", "test_config.db")
    defaults_path = os.path.join(os.path.dirname(__file__), "data", "model_defaults.json")
    
    # Optional: ensure an empty sqlite DB so RulesEngine doesn't crash if missing
    import sqlite3
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    con = sqlite3.connect(db_path)
    con.execute('''CREATE TABLE IF NOT EXISTS deterministic_rules (
                    id TEXT PRIMARY KEY, condition TEXT, scoring_type TEXT,
                    scale TEXT, domain TEXT, description TEXT, verdict TEXT,
                    source_page TEXT, success_weight REAL)''')
    con.close()
    
    cfg = ModelConfig(db_path=db_path, defaults_path=defaults_path)
    lk_pipeline = LKPredictionPipeline(cfg)
    
    print("3. Executing Predictions on Natal Chart...")
    lk_pipeline.load_natal_baseline(natal_chart)
    predictions = lk_pipeline.generate_predictions(natal_chart)
    
    print(f"Generated {len(predictions)} predictions for Natal Chart.")
    
    # 4. Output to JSON for manual review
    output_data = {
        "client_name": client_name,
        "dob": dob,
        "tob": tob,
        "place": place,
        "natal_chart_data": natal_chart,
        "lk_predictions_v2": [p.__dict__ for p in predictions]
    }
    
    out_path = "test_output.json"
    with open(out_path, "w") as f:
        json.dump(output_data, f, indent=4)
        
    print(f"\n=> SUCCESS! Fully populated JSON chart and predictions written to '{out_path}'.")
    print("You can open it to manually check the accuracy of raw chart objects and output predictions.")


if __name__ == "__main__":
    main()
