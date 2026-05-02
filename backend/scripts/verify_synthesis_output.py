import json
import os
from astroq.lk_prediction.pipeline import LKPredictionPipeline
from astroq.lk_prediction.config import ModelConfig

def verify_synthesis():
    # 1. Setup Pipeline
    config = ModelConfig("mock.db", "backend/data/model_defaults.json")
    pipeline = LKPredictionPipeline(config)
    
    # 2. Mock Natal Chart (Sachin Tendulkar - approx)
    # Jupiter H2, Sun H6, Mars H3, Rahu H6 (Startle Sun)
    natal_chart = {
        "chart_type": "Birth",
        "chart_period": 0,
        "planets_in_houses": {
            "Jupiter": {"house": 2},
            "Sun": {"house": 6},
            "Moon": {"house": 8},
            "Mars": {"house": 3},
            "Mercury": {"house": 5},
            "Venus": {"house": 5},
            "Saturn": {"house": 12},
            "Rahu": {"house": 6},
            "Ketu": {"house": 12}
        }
    }
    
    pipeline.load_natal_baseline(natal_chart)
    
    # 3. Create an Annual Chart for Age 18 (Saturn hit)
    annual_chart = {
        "chart_type": "Yearly",
        "chart_period": 18,
        "planets_in_houses": {
            "Sun": {"house": 1},
            "Saturn": {"house": 8} # Sudden Strike to Sun in H1?
        }
    }
    
    print("\n--- Generating Synthesis Output for Age 18 ---")
    predictions = pipeline.generate_predictions(annual_chart)
    
    for p in predictions:
        print(f"\nDOMAIN: {p.domain}")
        print(f"GRAVITY: {p.gravity_score:.2f}")
        print(f"NARRATIVE: {p.prediction_text}")
        print(f"PROOF: {p.forensic_proof}")
        print(f"VISUAL: {json.dumps(p.visual_manifest, indent=2)}")
        print("-" * 30)

if __name__ == "__main__":
    verify_synthesis()
