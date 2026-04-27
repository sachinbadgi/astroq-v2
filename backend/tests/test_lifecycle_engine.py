import pytest
from astroq.lk_prediction.lifecycle_engine import LifecycleEngine

def test_lifecycle_sequential_trauma():
    engine = LifecycleEngine()
    # Natal: Sun in H1, Ketu in H9, Moon in H4
    # Year 1: Ketu (H6) hits Sun (H1) -> 1 trauma
    # Year 2: Moon (H9) hits Sun (H4) -> +1 trauma (Total 2)
    natal_positions = {
        "Sun": 1,
        "Ketu": 9,
        "Moon": 4,
        "Mars": 3,
        "Mercury": 7,
        "Jupiter": 2,
        "Venus": 11,
        "Saturn": 10,
        "Rahu": 12
    }
    
    report = engine.run_75yr_analysis(natal_positions)
    
    # Year 1 state check
    year_1 = report[1]
    assert any(i.type == "Takkar" and i.target == "Sun" for i in year_1["incidents"])
    assert year_1["planetary_states"]["Sun"].trauma_points == 1
    
    # Year 2 state check (Cumulative)
    year_2 = report[2]
    assert year_2["planetary_states"]["Sun"].trauma_points == 2
    # Multiplier: 1.0 + (0.1 * 2) = 1.2
    assert abs(year_2["multipliers"]["Sun"] - 1.2) < 0.01
