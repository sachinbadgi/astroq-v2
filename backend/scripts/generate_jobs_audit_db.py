import sys
import os
import sqlite3
import json

# Ensure backend is in path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.pipeline import LKPredictionPipeline

def generate_audit():
    db_path = "backend/data/astroq_gt.db"
    defaults_path = "backend/data/model_defaults.json"
    audit_db_path = "/tmp/jobs_audit_v2.db"
    
    # Remove existing audit db if it exists
    if os.path.exists(audit_db_path):
        try:
            os.remove(audit_db_path)
        except PermissionError:
            print(f"Warning: Could not remove {audit_db_path}, appending instead.")
        
    audit_conn = sqlite3.connect(audit_db_path)
    audit_cur = audit_conn.cursor()
    
    # Create tables
    audit_cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_scores (
            age INTEGER,
            domain TEXT,
            score REAL,
            prediction_text TEXT
        )
    """)
    audit_cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_rules (
            age INTEGER,
            rule_id TEXT,
            description TEXT,
            domain TEXT
        )
    """)
    
    config = ModelConfig(db_path=db_path, defaults_path=defaults_path)
    generator = ChartGenerator()
    pipeline = LKPredictionPipeline(config)
    
    # 1. Birth Data for Steve Jobs
    person_dob = "1955-02-24"
    person_tob = "19:15"
    person_place = "San Francisco, California"
    person_lat = 37.7749
    person_lon = -122.4194
    person_tz = "-08:00"
    
    # 2. Generate Chart Payload
    print("Generating charts...")
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
    
    # 4. Process all 75 years
    print("Processing years 0 to 75...")
    for age in range(0, 76):
        if age % 10 == 0: print(f"  Age {age}...")
        
        chart = natal_chart if age == 0 else annual_charts[f"chart_{age}"]
        
        # Capture Rules directly to be comprehensive (before translation/filtering)
        # We need to build the context same as pipeline._build_rules_context
        # But for audit, we can just run the pipeline and look at result.source_rules
        predictions = pipeline.generate_predictions(chart)
        
        # Insert Scores
        for p in predictions:
            audit_cur.execute(
                "INSERT INTO audit_scores (age, domain, score, prediction_text) VALUES (?, ?, ?, ?)",
                (age, p.domain, p.probability, p.prediction_text)
            )
            # Insert Rules for this prediction
            for rule_desc in p.source_rules:
                # Prediction doesn't have rule_id or etc, so we just use the text.
                # In more advanced audit, we'd reach into the engine.
                audit_cur.execute(
                    "INSERT INTO audit_rules (age, rule_id, description, domain) VALUES (?, ?, ?, ?)",
                    (age, "N/A", rule_desc, p.domain)
                )
    
    audit_conn.commit()
    audit_conn.close()
    print(f"Audit Complete. Database stored at: {audit_db_path}")

if __name__ == "__main__":
    generate_audit()
