# backend/tests/lk_prediction/test_lifecycle_scapegoat.py
from astroq.lk_prediction.lifecycle_engine import LifecycleEngine

MOCK_NATAL = {
    "Saturn": 12, "Sun": 6, "Venus": 3, "Moon": 5,
    "Mars": 9, "Mercury": 7, "Jupiter": 1, "Rahu": 10, "Ketu": 4,
}

def test_rashi_phal_routes_to_scapegoat():
    engine = LifecycleEngine()
    # Venus (Saturn's scapegoat) should accumulate trauma if Saturn is RASHI_PHAL
    history = engine.run_75yr_analysis(MOCK_NATAL, dignity_overrides={"Saturn": "RASHI_PHAL"})
    
    # Check if any scapegoat hit count was recorded for Venus
    venus_hit = False
    for age in range(1, 76):
        if history[age].get_planet_state("Venus").scapegoat_hit_count > 0:
            venus_hit = True
            break
    assert venus_hit is True

def test_run_accepts_dignity_overrides_kwarg():
    engine = LifecycleEngine()
    # Should not raise TypeError
    history = engine.run_75yr_analysis(MOCK_NATAL, dignity_overrides={})
    assert isinstance(history, dict)
