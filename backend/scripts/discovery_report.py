"""
High-Fidelity Discovery Report.

Runs a deep exploration of the astronomical space and reports exactly
which Lal Kitab canonical rules were successfully identified in 'wild' skies.
"""

import sys
import os
import sqlite3
from typing import Dict, List

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.pipeline import LKPredictionPipeline
from astroq.lk_prediction.config import ModelConfig
from scripts.auto_research_fuzzer import get_random_dob, get_random_tob

DB_PATH = "backend/data/rules.db"
DEFAULTS_PATH = "backend/data/model_defaults.json"

def generate_discovery_report(iterations=5):
    print(f"=== Generating Discovery Report ({iterations} random natives) ===")
    
    cfg = ModelConfig(db_path=DB_PATH, defaults_path=DEFAULTS_PATH)
    generator = ChartGenerator()
    pipeline = LKPredictionPipeline(cfg)
    
    found_rules = {} # ID -> Description
    
    for i in range(1, iterations + 1):
        dob = get_random_dob()
        tob = get_random_tob()
        system = "kp" if i % 2 == 0 else "vedic"
        
        payload = generator.build_full_chart_payload(
            dob_str=dob, tob_str=tob, place_name="New Delhi",
            latitude=28.6139, longitude=77.2090, utc_string="+05:30",
            chart_system=system
        )
        
        for k, v in payload.items():
            if not k.startswith("chart_"): continue
            preds = pipeline.generate_predictions(v)
            for p in preds:
                for rid in p.source_rules:
                    if rid not in found_rules:
                        found_rules[rid] = p.prediction_text.split(":")[0]
        
        print(f"  Processed native {i}... cumulative rules hit: {len(found_rules)}")

    print(f"\n--- DISCOVERY HIGHLIGHTS ({len(found_rules)} total rules verified) ---")
    
    # Categorize and print a sample
    categories = {} # Domain -> list
    for rid, desc in found_rules.items():
        # Quick query for domain
        conn = sqlite3.connect(DB_PATH)
        cur = conn.execute("SELECT domain FROM deterministic_rules WHERE id=?", (rid,))
        row = cur.fetchone()
        domain = row[0] if row else "general"
        conn.close()
        
        if domain not in categories: categories[domain] = []
        categories[domain].append(desc)

    for domain, rules in categories.items():
        print(f"\n[{domain.upper()}]")
        for r in rules[:5]: # Top 5 per domain
            print(f"  - {r}")
        if len(rules) > 5:
            print(f"  ... and {len(rules)-5} more.")

if __name__ == "__main__":
    generate_discovery_report(5)
