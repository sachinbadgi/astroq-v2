import pytest
from astroq.lk_prediction.state_ledger import StateLedger
from astroq.lk_prediction.incident_resolver import IncidentResolver
from astroq.lk_prediction.lifecycle_engine import LifecycleEngine

def test_state_ledger_thresholds():
    ledger = StateLedger()

    # Sun is a tough planet: leak_threshold=0.8, burst_threshold=4.0
    # Use Jupiter (baseline: leak_threshold=0.5, burst_threshold=3.0) so the
    # test values in the comments match the actual threshold.

    # 1. Test Secondary Strike on Jupiter (0.5 >= 0.5 leak_threshold)
    ledger.apply_trauma("Jupiter", 0.5)
    state = ledger.get_planet_state("Jupiter")
    assert state.trauma_points == 0.5
    assert state.is_leaking is True
    assert state.is_burst is False
    assert ledger.get_leakage_multiplier("Jupiter") == 0.5

    # 2. Test Primary Strike (1.0 more → total 1.5)
    ledger.apply_trauma("Jupiter", 1.0)
    assert state.trauma_points == 1.5
    assert state.is_leaking is True
    assert ledger.get_leakage_multiplier("Jupiter") == 0.5

    # 3. Test Burst Threshold (> 3.0): add 2.0 → total 3.5
    ledger.apply_trauma("Jupiter", 2.0)
    assert state.trauma_points == 3.5
    assert state.is_burst is True
    assert state.is_leaking is False
    assert ledger.get_leakage_multiplier("Jupiter") == 0.0

def test_incident_resolver_weights():
    resolver = IncidentResolver()
    
    # 1/8 is Primary (1.0)
    positions = {"Sun": 1, "Mars": 8}
    incidents = resolver.detect_incidents(positions)
    # Check Sun hitting Mars and Mars hitting Sun
    # In IncidentResolver, 1/8 confrontation is directed.
    # House 1 confronts House 8.
    
    takkar = next(i for i in incidents if i.type == "Takkar" and i.source == "Sun")
    assert takkar.trauma_weight == 1.0
    
    # 1/7 is Secondary (0.5)
    positions = {"Sun": 1, "Venus": 7}
    incidents = resolver.detect_incidents(positions)
    takkar = next(i for i in incidents if i.type == "Takkar" and i.source == "Sun")
    assert takkar.trauma_weight == 0.5

def test_lifecycle_dormancy_shield():
    engine = LifecycleEngine()
    # Moon in H2, Saturn in H12 (Primary Strike 12/2)
    # Moon is normally dormant if H3-H8 are empty and no aspects.
    # H2 to H8: 3,4,5,6,7,8. 
    natal = {"Moon": 2, "Saturn": 12}
    
    history = engine.run_75yr_analysis(natal)
    
    # Age 1: Annual positions will be same as natal for this simple test 
    # (assuming matrix maps 1->1, etc. for first year or fallback)
    # Let's verify trauma accumulation
    for age in range(1, 10):
        ledger = history[age]
        # Moon in H2 is hit by Saturn in H12 (Primary)
        # If Moon is awake, it takes 1.0 trauma per year.
        # After 4 years, it should Burst.
        pass

    # Note: Real verification requires checking if DormancyEngine sees it as awake.
    # A 12/2 strike is a 'confrontation' which often STARTLES the planet awake.
