from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.pipeline import LKPredictionPipeline
import json
import os

def verify_pipeline():
    # Use real rules.db
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    db_path = os.path.join(backend_dir, 'data', 'rules.db')
    defaults_path = os.path.join(backend_dir, 'data', 'model_defaults.json')
    
    cfg = ModelConfig(db_path=db_path, defaults_path=defaults_path)
    pipeline = LKPredictionPipeline(cfg)
    
    # Test chart: Sun and Saturn in H1 (Asthma trigger)
    chart = {
        "chart_type": "Birth",
        "chart_period": 0,
        "planets_in_houses": {
            "Sun": {"house": 1, "states": [], "aspects": [], "strength_total": 5.0},
            "Saturn": {"house": 1, "states": [], "aspects": [], "strength_total": 5.0},
            "Moon": {"house": 4, "states": [], "aspects": [], "strength_total": 5.0},
            "Mars": {"house": 3, "states": [], "aspects": [], "strength_total": 5.0},
            "Mercury": {"house": 7, "states": [], "aspects": [], "strength_total": 5.0},
            "Jupiter": {"house": 2, "states": [], "aspects": [], "strength_total": 5.0},
            "Venus": {"house": 8, "states": [], "aspects": [], "strength_total": 5.0},
            "Rahu": {"house": 12, "states": [], "aspects": [], "strength_total": 5.0},
            "Ketu": {"house": 6, "states": [], "aspects": [], "strength_total": 5.0}
        }
    }
    
    predictions = pipeline.generate_predictions(chart)
    
    print(f"Generated {len(predictions)} predictions.")
    health_preds = [p for p in predictions if p.domain.lower() == "health"]
    
    for p in health_preds:
        print(f"[{p.polarity}] {p.prediction_text} (Confidence: {p.confidence})")
        
    if any("respiratory" in p.prediction_text.lower() or "asthma" in p.prediction_text.lower() for p in health_preds):
        print("VERIFICATION SUCCESS: Asthma rule triggered in pipeline.")
    else:
        print("VERIFICATION FAILURE: Asthma rule not found.")

if __name__ == "__main__":
    verify_pipeline()
