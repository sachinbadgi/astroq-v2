import sys
import os
import json

# Ensure backend is in path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from astroq.lk_prediction.rules_engine import RulesEngine
from astroq.lk_prediction.config import ModelConfig

def debug():
    db_path = "backend/data/astroq_gt.db"
    defaults_path = "backend/data/model_defaults.json"
    config = ModelConfig(db_path=db_path, defaults_path=defaults_path)
    engine = RulesEngine(config)
    
    # Dummy chart
    chart = {
        "chart_period": 22,
        "planets_in_houses": {
            "Sun": {"house": 4}
        }
    }
    
    # Test a simple placement rule manually
    rule_cond = {"type": "AND", "conditions": [{"type": "placement", "planet": "Sun", "houses": [4]}]}
    match, spec, targ, hs = engine._evaluate_node(rule_cond, chart["planets_in_houses"], chart)
    print(f"Manual Placement Match: {match}, targets: {targ}")
    
    # Test age rule
    age_cond = {"type": "AND", "conditions": [{"type": "current_age", "age": 22}]}
    match, spec, targ, hs = engine._evaluate_node(age_cond, chart["planets_in_houses"], chart)
    print(f"Manual Age Match: {match}")
    
    # Run full engine
    hits = engine.evaluate_chart(chart)
    print(f"Total Hits found by engine: {len(hits)}")
    for h in hits:
        print(f"  Hit: {h.rule_id} - {h.description}")

if __name__ == "__main__":
    debug()
