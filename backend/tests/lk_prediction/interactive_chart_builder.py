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
        
        target_age_input = input("Enter Target Age (e.g., '34', '30-35') or leave empty for just Natal: ").strip()
        
        chart_system = input("Enter Chart System (kp/vedic) [default: kp]: ").strip().lower()
        if not chart_system:
            chart_system = "kp"
            
        if chart_system not in ["kp", "vedic"]:
            print(f"\nError: Invalid chart system '{chart_system}'. Use 'kp' or 'vedic'.")
            sys.exit(1)
        
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)

    if not all([client_name, dob, tob, place]):
        print("\nError: All fields are required except Target Age!")
        sys.exit(1)

    print(f"\n[1/3] Generating astronomical chart for {client_name}...")
    
    try:
        generator = ChartGenerator()
        annual_basis = input("Enter Annual Basis (kp/vedic) [default: vedic]: ").strip().lower()
        if not annual_basis:
            annual_basis = "vedic"

        full_payload = generator.build_full_chart_payload(
            dob_str=dob,
            tob_str=tob,
            place_name=place,
            chart_system=chart_system,
            annual_basis=annual_basis
        )
        
        natal_chart = full_payload.get("chart_0")
        if not natal_chart:
            print("Error: Failed to generate base chart data.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\nError generating chart: {e}")
        sys.exit(1)
        
    # Initialize the prediction engine
    # Preference: 1. data/rules.db (Production), 2. data/test_config.db
    real_db_path = os.path.join(parent_dir, "data", "rules.db")
    test_db_path = os.path.join(parent_dir, "data", "test_config.db")
    
    db_path = real_db_path if os.path.exists(real_db_path) else test_db_path
    defaults_path = os.path.join(parent_dir, "data", "model_defaults.json")
    
    # Ensure at least an empty DB exists if none found
    if not os.path.exists(db_path):
        import sqlite3
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        con = sqlite3.connect(db_path)
        con.execute('''CREATE TABLE IF NOT EXISTS deterministic_rules (
                        id TEXT PRIMARY KEY, condition TEXT, scoring_type TEXT,
                        scale TEXT, domain TEXT, description TEXT, verdict TEXT,
                        source_page TEXT, success_weight REAL)''')
        con.close()
    
    print(f"[2/3] Initializing Prediction Engine (DB: {os.path.basename(db_path)})...")
    
    cfg = ModelConfig(db_path=db_path, defaults_path=defaults_path)
    lk_pipeline = LKPredictionPipeline(cfg)
    
    print("[3/3] Executing Predictions...")
    
    # Determine which charts to process
    charts_to_process = [(0, natal_chart)]
    if target_age_input:
        if "-" in target_age_input:
            start_str, end_str = target_age_input.split("-")
            start_age = int(start_str.strip())
            end_age   = int(end_str.strip())
            for age in range(start_age, end_age + 1):
                chart_key = f"chart_{age}"
                if chart_key in full_payload:
                    charts_to_process.append((age, full_payload[chart_key]))
        else:
            age = int(target_age_input.strip())
            chart_key = f"chart_{age}"
            if chart_key in full_payload:
                charts_to_process.append((age, full_payload[chart_key]))

    try:
        lk_pipeline.load_natal_baseline(natal_chart)
        
        # Format output data
        output_data = {
            "client_name": client_name,
            "dob": dob,
            "tob": tob,
            "place": place,
            "chart_system": chart_system,
            "natal_chart_data": natal_chart,
            "predictions_by_age": {}
        }
        
        total_predictions = 0
        domain_audit_results = {} # age -> {domain: score}
        
        for age, chart in charts_to_process:
            print(f"  -> Predicting for age {age}..." if age > 0 else "  -> Predicting Natal chart...")
            
            # 1. Standard Predictions
            predictions = lk_pipeline.generate_predictions(chart)
            predictions = [p for p in predictions if p.confidence != "UNLIKELY"]
            total_predictions += len(predictions)
            
            # 2. Domain Audit Scores (New logic)
            domain_scores = lk_pipeline.generate_domain_scores(chart)
            domain_audit_results[age] = domain_scores
            
            # Print remedies nicely
            remedied = [p for p in predictions if p.remedy_applicable]
            if remedied:
                print(f"    [Remedies Generated for {len(remedied)} malefic events!]")
                for i, p in enumerate(remedied[:2]): 
                    planet_name = p.source_planets[0] if p.source_planets else "Unknown"
                    print(f"      * {planet_name}:")
                    for hint in p.remedy_hints:
                        print(f"        - {hint}")
                if len(remedied) > 2:
                    print(f"      * ...and {len(remedied)-2} more planet events.")
            
            # Map predictions to dict
            output_data["predictions_by_age"][f"age_{age}"] = [p.__dict__ for p in predictions]
            output_data["domain_scores_by_age"] = output_data.get("domain_scores_by_age", {})
            output_data["domain_scores_by_age"][f"age_{age}"] = domain_scores

        # --- Display Domain Audit Table ---
        if len(charts_to_process) > 1:
            print("\n" + "="*60)
            print("        DOMAIN PERFORMANCE AUDIT (DYNAMIC SIGNALS)        ")
            print("="*60)
            
            # Find all domains present
            all_domains = set()
            for age in domain_audit_results:
                all_domains.update(domain_audit_results[age].keys())
            
            sorted_domains = sorted(list(all_domains))
            
            # Print Header
            header = "Age | " + " | ".join([f"{d[:8]:8}" for d in sorted_domains])
            print(header)
            print("-" * len(header))
            
            for age in sorted(domain_audit_results.keys()):
                scores = domain_audit_results[age]
                row = f"{age:3} | "
                for d in sorted_domains:
                    domain_result = scores.get(d, {})
                    # Handle both legacy flat scores and new detailed dicts
                    score = domain_result.get("score", 0.0) if isinstance(domain_result, dict) else float(domain_result or 0.0)
                    
                    # ASCII-friendly indicators for terminal compatibility
                    bar = "*" if score > 0.7 else "o" if score > 0.4 else " "
                    row += f"{score:0.2f}{bar} | "
                print(row)
            print("="*60)
            print("Legend: * High (>0.7), o Moderate (>0.4)")
            print("="*60 + "\n")
            
    except Exception as e:
        print(f"\nError running predictions: {e}")
        sys.exit(1)
    
    
    # Save to file
    filename = f"{sanitize_filename(client_name)}_predictions.json"
    with open(filename, "w") as f:
        json.dump(output_data, f, indent=4)
        
    # --- Generate Gemini Optimization Payload ---
    llm_payload_file = f"{sanitize_filename(client_name)}_gemini_payload.json"
    print(f"\n[4/4] Generating Gemini-optimized correlation payload...")
    
    # Bundle natal and annual charts for the pipeline
    annual_charts_dict = {}
    for age, chart in charts_to_process:
        if age > 0:
            annual_charts_dict[age] = chart
            
    llm_payload = lk_pipeline.generate_llm_payload(natal_chart, annual_charts_dict)
    
    with open(llm_payload_file, "w") as f:
        json.dump(llm_payload, f, indent=4)
        
    print(f"\n=> SUCCESS! Detailed JSON predictions written to '{filename}'.")
    print(f"=> SUCCESS! Gemini LLM Payload written to '{llm_payload_file}'.")
    print(f"You can now feed '{llm_payload_file}' into Gemini to get a narrative summary.")

if __name__ == "__main__":
    main()
