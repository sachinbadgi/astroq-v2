"""
Debug the remaining 60% of Malefic Penalties to categorize their focus.
"""
import random
import datetime
import os
import sys

sys.path.append(os.path.join(os.getcwd(), "backend"))
from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.rules_engine import RulesEngine
from astroq.lk_prediction.pipeline import LKPredictionPipeline
from astroq.lk_prediction.config import ModelConfig

DB_PATH = "backend/data/rules.db"
DEFAULTS_PATH = "backend/data/model_defaults.json"

def run_debug_transference():
    cfg = ModelConfig(db_path=DB_PATH, defaults_path=DEFAULTS_PATH)
    generator = ChartGenerator()
    pipeline = LKPredictionPipeline(cfg)
    rules_engine = RulesEngine(cfg)
    rule_map = {r.get("id") or r.get("rule_id"): r for r in rules_engine._rules_cache}
    
    biological_terms = {"mother", "father", "son", "daughter", "sister", "brother", "eye", "eyesight", "teeth", "health", "disease", "body", "wife", "spouse", "child", "children"}
    
    non_biological_penalties = set()
    
    for i in range(100):
        start_date = datetime.date(1940, 1, 1)
        end_date = datetime.date(2025, 12, 31)
        dob = (start_date + datetime.timedelta(days=random.randrange((end_date - start_date).days))).strftime("%Y-%m-%d")
        tob = f"{random.randint(0,23):02d}:{random.randint(0,59):02d}"
        
        payload = generator.build_full_chart_payload(dob, tob, "New Delhi", 28.6139, 77.2090, "+05:30", "vedic")
        chart_data = payload.get("chart_0")
        if not chart_data: continue
            
        predictions = pipeline.generate_predictions(chart_data)
        for pred in predictions:
            for rid in pred.source_rules:
                if rid in rule_map:
                    rule = rule_map[rid]
                    if rule.get("scoring_type") == "penalty":
                        desc = rule.get("description", "").lower()
                        if not any(term in desc for term in biological_terms):
                            non_biological_penalties.add(rule.get("description", ""))
                            
        if len(non_biological_penalties) > 20: break
        
    print("=== NON-BIOLOGICAL MALEFIC PENALTIES ===")
    for desc in list(non_biological_penalties)[:20]:
        print("-", desc)

if __name__ == "__main__":
    run_debug_transference()
