import sys
import os
sys.path.append(os.path.join(os.getcwd(), "backend"))

from astroq.lk_prediction.dignity_engine import DignityEngine
from astroq.lk_prediction.rules_engine import RulesEngine
from astroq.lk_prediction.strength_engine import StrengthEngine
from astroq.lk_prediction.config import ModelConfig

def test_unification():
    # Setup
    config = ModelConfig("mock.db", "backend/data/model_defaults.json")
    rules_engine = RulesEngine(config)
    strength_engine = StrengthEngine(config)
    
    planet = "Sun"
    natal_house = 1
    age = 1 # Year 1 matrix for Sun in H1 -> Annual House 1
    
    # 1. Test Annual Multiplier (RulesEngine style)
    engine_mult = DignityEngine.get_annual_dignity_multiplier(planet, natal_house, age)
    print(f"DignityEngine Multiplier (Sun in H1, Age 1): {engine_mult}")
    
    # Mock chart for RulesEngine
    chart = {
        "chart_period": age,
        "_natal_positions": {planet: natal_house},
        "planets_in_houses": {planet: {"house": 1}}
    }
    hits = rules_engine.evaluate_chart(chart)
    # If magnitude scaling is working, we should see it in the hits if a rule for Sun fired
    
    # 2. Test Absolute Score (StrengthEngine style)
    weights = {"pakka_ghar": 2.2, "exalted": 5.0, "debilitated": -5.0, "fixed_house_lord": 1.5}
    engine_score = DignityEngine.get_dignity_score(planet, 1, ["Exalted"], weights)
    print(f"DignityEngine Score (Sun in H1, Exalted, FHL): {engine_score}")
    
    # Verify StrengthEngine uses it
    data = {"house": 1, "states": ["Exalted"]}
    strength_score = strength_engine._calculate_dignity(planet, 1, data, "Birth")
    print(f"StrengthEngine calculated score: {strength_score}")
    
    # Sun in H1 is Pakka Ghar (2.2) and Exalted (5.0) and FHL (1.5) -> 8.7
    assert engine_score == 8.7
    assert strength_score == 8.7
    print("SUCCESS: Dignity unification verified.")

if __name__ == "__main__":
    test_unification()
