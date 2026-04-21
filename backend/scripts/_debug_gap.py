"""
Pattern Debugger: Analyzing the ~3% Gap
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
from astroq.lk_prediction.lk_constants import PLANET_PAKKA_GHAR, PLANET_EXALTATION

DB_PATH = "backend/data/rules.db"
DEFAULTS_PATH = "backend/data/model_defaults.json"

def get_random_dob():
    start_date = datetime.date(1940, 1, 1)
    end_date = datetime.date(2025, 12, 31)
    return (start_date + datetime.timedelta(days=random.randrange((end_date - start_date).days))).strftime("%Y-%m-%d")

def run_debug():
    cfg = ModelConfig(db_path=DB_PATH, defaults_path=DEFAULTS_PATH)
    generator = ChartGenerator()
    pipeline = LKPredictionPipeline(cfg)
    rules_engine = RulesEngine(cfg)
    rule_map = {r.get("id") or r.get("rule_id"): r for r in rules_engine._rules_cache}
    
    missed_uchha_cases = []
    missed_pakka_cases = []
    
    for i in range(100): # Small batch to find anomalies
        payload = generator.build_full_chart_payload(
            dob_str=get_random_dob(), tob_str=f"{random.randint(0,23):02d}:{random.randint(0,59):02d}", 
            place_name="New Delhi", latitude=28.6139, longitude=77.2090, utc_string="+05:30", chart_system="vedic"
        )
        
        chart_data = payload.get("chart_0")
        if not chart_data: continue
            
        ppos = {p: d["house"] for p, d in chart_data["planets_in_houses"].items() if p != "Lagna"}
        
        pakka_planets = [p for p in ppos if ppos[p] == PLANET_PAKKA_GHAR.get(p)]
        uchha_planets = [p for p in ppos if ppos[p] in PLANET_EXALTATION.get(p, [])]
        
        predictions = pipeline.generate_predictions(chart_data)
        
        has_major_boost = False
        penalty_rules = []
        for pred in predictions:
            for rid in pred.source_rules:
                if rid in rule_map:
                    rule = rule_map[rid]
                    if rule.get("scale") in ["major", "extreme"] and rule.get("scoring_type") == "boost":
                        has_major_boost = True
                    if rule.get("scoring_type") == "penalty":
                        penalty_rules.append(rule.get("description", ""))
        
        if len(pakka_planets) > 0 and not has_major_boost:
            missed_pakka_cases.append({"pakka": pakka_planets, "chart": ppos, "penalties": penalty_rules[:3]})
            
        if len(uchha_planets) > 0 and not has_major_boost:
            missed_uchha_cases.append({"uchha": uchha_planets, "chart": ppos, "penalties": penalty_rules[:3]})
            
        if len(missed_pakka_cases) >= 5 and len(missed_uchha_cases) >= 5:
            break
            
    print("=== DEBUGGING PAKKA GHAR MISSES ===")
    for c in missed_pakka_cases[:2]:
        print(f"Pakka Planet(s): {c['pakka']}")
        print(f"Chart: {c['chart']}")
        print(f"Penalties overriding boost: {c['penalties']}")
        print("-" * 50)
        
    print("=== DEBUGGING UCHHA MISSES ===")
    for c in missed_uchha_cases[:2]:
        print(f"Uchha Planet(s): {c['uchha']}")
        print(f"Chart: {c['chart']}")
        print(f"Penalties overriding boost: {c['penalties']}")
        print("-" * 50)

if __name__ == "__main__":
    run_debug()
