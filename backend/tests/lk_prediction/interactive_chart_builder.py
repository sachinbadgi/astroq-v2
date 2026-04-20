"""
Interactive Chart Builder - Simplified Edition

Generates a unified JSON payload for NotebookLM based on the new 
deterministic rule-based architecture.
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
    return re.sub(r'[^a-zA-Z0-9\s]', '', name).strip().replace(' ', '_').lower()

def main():
    print("=========================================================")
    print("      Lal Kitab Engine - Simplified Data Gen           ")
    print("=========================================================\n")
    
    try:
        client_name = input("Enter Person's Name: ").strip()
        dob = input("Enter Date of Birth (YYYY-MM-DD): ").strip()
        tob = input("Enter Time of Birth (HH:MM): ").strip()
        place = input("Enter Place of Birth: ").strip()
        chart_system = input("Chart System (kp/vedic) [default: vedic]: ").strip().lower() or "vedic"
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)

    print(f"\n[1/2] Generating Astronomical Data...")
    try:
        generator = ChartGenerator()
        full_payload = generator.build_full_chart_payload(
            dob_str=dob, tob_str=tob, place_name=place,
            chart_system=chart_system, annual_basis="vedic"
        )
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f"[2/2] Running Rule Engine & Synthesis...")
    db_path = os.path.join(parent_dir, "data", "rules.db")
    defaults_path = os.path.join(parent_dir, "data", "model_defaults.json")
    cfg = ModelConfig(db_path=db_path, defaults_path=defaults_path)
    pipeline = LKPredictionPipeline(cfg)

    # Flatten the charts into a list for the pipeline
    charts_list = []
    for k, v in full_payload.items():
        if isinstance(k, str) and k.startswith("chart_"):
            charts_list.append(v)

    final_payload = pipeline.generate_full_payload(client_name, dob, charts_list)
    filename = f"{sanitize_filename(client_name)}_predictions.json"
    
    with open(filename, "w") as f:
        json.dump(final_payload, f, indent=4)
        
    print(f"\n=> SUCCESS! Optimized predictions generated: '{filename}'")
    print(f"This file is the single source of truth for NotebookLM/Gemini.")

if __name__ == "__main__":
    main()
