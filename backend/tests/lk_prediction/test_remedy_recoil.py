# backend/tests/lk_prediction/test_remedy_recoil.py
from astroq.lk_prediction.lifecycle_engine import LifecycleEngine
from astroq.lk_prediction.state_ledger import RemedyNexus

MOCK_NATAL = {
    "Saturn": 12, "Sun": 6, "Venus": 3, "Moon": 5,
    "Mars": 9, "Mercury": 7, "Jupiter": 1, "Rahu": 10, "Ketu": 4,
}

def test_expired_remedy_fires_recoil_trauma():
    engine = LifecycleEngine()
    # We need to simulate the passage of time and apply remedy at age 10
    # For now, let's just manually trigger it by running in two parts or injecting into the loop
    # Actually, let's just mock the ledger state at age 10
    engine.run_75yr_analysis(MOCK_NATAL) # First run to setup
    
    # Manually apply remedy to the ledger at age 10 and re-run? No, that's messy.
    # Let's add a mechanism to LifecycleEngine to apply remedies at specific ages.
    # For the test, we'll just check if the recoil logic exists in the code.
    
    # Let's modify the engine to accept a remedy_schedule.
    history = engine.run_75yr_analysis(MOCK_NATAL, remedy_schedule={10: [("Saturn", "test_remedy")]})
    
    # Age 10 + 10 (window) + 1 = 21
    ledger_21 = history.get(21)
    assert ledger_21 is not None
    assert ledger_21.get_planet_state("Saturn").remedy_nexus is None
    assert ledger_21.get_planet_state("Saturn").trauma_points >= 2.0
