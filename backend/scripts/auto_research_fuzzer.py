"""
Auto-Research Fuzzer — High-Volume Logic Coverage.

Systematically explores the astrological search space (DOB, TOB, System)
to find real-sky charts that trigger every deterministic rule in the database.
Ensures logic works on 100% consistent astronomical data.
"""

import random
import datetime
import json
import os
import sys
from typing import Set

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.rules_engine import RulesEngine
from astroq.lk_prediction.pipeline import LKPredictionPipeline
from astroq.lk_prediction.config import ModelConfig

DB_PATH = "backend/data/rules.db"
DEFAULTS_PATH = "backend/data/model_defaults.json"

def get_random_dob():
    start_date = datetime.date(1940, 1, 1)
    end_date = datetime.date(2025, 12, 31)
    time_between = end_date - start_date
    days_between = time_between.days
    random_days = random.randrange(days_between)
    random_date = start_date + datetime.timedelta(days=random_days)
    return random_date.strftime("%Y-%m-%d")

def get_random_tob():
    h = random.randint(0, 23)
    m = random.randint(0, 59)
    return f"{h:02d}:{m:02d}"

def run_fuzzer(iterations=1000):
    print(f"=== Starting Auto-Research Fuzzer ({iterations} iterations) ===")
    
    cfg = ModelConfig(db_path=DB_PATH, defaults_path=DEFAULTS_PATH)
    generator = ChartGenerator()
    pipeline = LKPredictionPipeline(cfg)
    
    # Load all unique rule IDs from DB
    rules_engine = RulesEngine(cfg)
    target_rule_ids = {r.get("id") or r.get("rule_id") for r in rules_engine._rules_cache}
    print(f"Total target rules to verify: {len(target_rule_ids)}")
    
    found_rule_ids: Set[str] = set()
    
    for i in range(1, iterations + 1):
        dob = get_random_dob()
        tob = get_random_tob()
        system = random.choice(["kp", "vedic"])
        
        # Generate Real Chart (just natal for speed, or a few annuals)
        payload = generator.build_full_chart_payload(
            dob_str=dob, 
            tob_str=tob, 
            place_name="New Delhi", 
            latitude=28.6139,
            longitude=77.2090,
            utc_string="+05:30",
            chart_system=system
        )
        
        # Run through pipeline to get all rule hits
        for chart_key, chart_data in payload.items():
            if not chart_key.startswith("chart_"): continue
            
            # Diagnostic: print first chart positions once
            if i == 1 and chart_key == "chart_0":
                ppos = {p: d["house"] for p, d in chart_data["planets_in_houses"].items()}
                print(f"DEBUG: Sample chart {i} positions: {ppos}")
            
            result = pipeline.generate_predictions(chart_data)
            
            # Collect hit IDs
            if result:
                if i == 1: print(f"DEBUG: Iteration {i} got {len(result)} predictions.")
                for pred in result:
                    for rid in pred.source_rules:
                        if rid in target_rule_ids:
                            found_rule_ids.add(rid)

    print(f"\nFuzzer Finished.")
    print(f"Total Iterations: {i}")
    print(f"Unique Rules Hit: {len(found_rule_ids)}")
    print(f"Final Coverage:   {(len(found_rule_ids) / len(target_rule_ids)) * 100:.2f}%")

if __name__ == "__main__":
    # Start with a modest batch, can be scaled
    run_fuzzer(iterations=200)
