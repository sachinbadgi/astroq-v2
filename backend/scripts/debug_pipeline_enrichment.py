from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.pipeline import LKPredictionPipeline
from astroq.lk_prediction.grammar_analyser import GrammarAnalyser
import json
import os

def debug_pipeline():
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    db_path = os.path.join(backend_dir, 'data', 'rules.db')
    defaults_path = os.path.join(backend_dir, 'data', 'model_defaults.json')
    
    cfg = ModelConfig(db_path=db_path, defaults_path=defaults_path)
    pipeline = LKPredictionPipeline(cfg)
    grammar = GrammarAnalyser(cfg)
    
    chart = {
        "chart_type": "Birth",
        "chart_period": 0,
        "planets_in_houses": {
            "Sun": {"house": 1, "states": [], "aspects": [], "strength_total": 5.0},
            "Saturn": {"house": 1, "states": [], "aspects": [], "strength_total": 5.0},
        }
    }
    
    print("--- Before Enrichment ---")
    print(f"Planets: {list(chart['planets_in_houses'].keys())}")
    
    # Initialize enriched dict as pipeline does
    enriched = {p: {"house": d["house"]} for p, d in chart["planets_in_houses"].items()}
    
    grammar.apply_grammar_rules(chart, enriched)
    print("--- After Enrichment ---")
    print(f"Planets in enriched: {list(enriched.keys())}")
    for p, d in enriched.items():
        print(f"{p}: House {d.get('house')}")
        
    predictions = pipeline.generate_predictions(chart)
    print(f"--- Predictions ({len(predictions)}) ---")
    for p in predictions:
        print(f"Domain: {p.domain}, Text: {p.prediction_text}")

if __name__ == "__main__":
    debug_pipeline()
