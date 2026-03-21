"""
Interactive Chart Builder

This script prompts the user for name, date of birth, time of birth, and place of birth.
It then generates the Lal Kitab ChartData and Predictions, saving the output
to a JSON file named after the user.

Usage:
  python interactive_chart_builder.py
"""

import os
import sys
import json
import re

# Add backend directory to path so astroq imports work
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.pipeline import LKPredictionPipeline

def sanitize_filename(name):
    """Keep only alphanumeric characters and spaces, then replace spaces with underscores."""
    s = re.sub(r'[^a-zA-Z0-9\s]', '', name)
    return s.strip().replace(' ', '_').lower()

def main():
    print("=========================================================")
    print("      Lal Kitab Prediction Model v2 - Chart Builder      ")
    print("=========================================================\n")
    
    try:
        client_name = input("Enter Person's Name: ").strip()
        dob = input("Enter Date of Birth (YYYY-MM-DD): ").strip()
        tob = input("Enter Time of Birth (HH:MM): ").strip()
        place = input("Enter Place of Birth (e.g., 'New Delhi, India'): ").strip()
        
        # Defaulting to KP system for the Lal Kitab engine base
        chart_system = "kp"
        
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)

    if not all([client_name, dob, tob, place]):
        print("\nError: All fields are required!")
        sys.exit(1)

    print(f"\n[1/3] Generating astronomical chart for {client_name}...")
    
    try:
        generator = ChartGenerator()
        full_payload = generator.build_full_chart_payload(
            dob_str=dob,
            tob_str=tob,
            place_name=place,
            chart_system=chart_system
        )
        
        natal_chart = full_payload.get("chart_0")
        if not natal_chart:
            print("Error: Failed to generate base chart data.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\nError generating chart: {e}")
        sys.exit(1)
        
    print("[2/3] Initializing Prediction Engine...")
    
    # Initialize the prediction engine
    db_path = os.path.join(parent_dir, "data", "test_config.db")
    defaults_path = os.path.join(parent_dir, "data", "model_defaults.json")
    
    # Ensure DB exists for Rules Engine
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
    
    print("[3/3] Executing Predictions...")
    try:
        lk_pipeline.load_natal_baseline(natal_chart)
        predictions = lk_pipeline.generate_predictions(natal_chart)
    except Exception as e:
        print(f"\nError running predictions: {e}")
        sys.exit(1)
    
    # Format output data
    output_data = {
        "client_name": client_name,
        "dob": dob,
        "tob": tob,
        "place": place,
        "chart_system": chart_system,
        "natal_chart_data": natal_chart,
        "lk_predictions_v2": [p.__dict__ for p in predictions]
    }
    
    # Save to file
    filename = f"{sanitize_filename(client_name)}_chart.json"
    
    with open(filename, "w") as f:
        json.dump(output_data, f, indent=4)
        
    print(f"\n=> SUCCESS! Fully populated JSON chart and {len(predictions)} predictions written to '{filename}'.")
    print(f"You can open '{filename}' to manually check the accuracy.")

if __name__ == "__main__":
    main()
