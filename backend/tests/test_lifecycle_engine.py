import pytest
from astroq.lk_prediction.lifecycle_engine import LifecycleEngine
from astroq.lk_prediction.state_ledger import StateLedger

def test_lifecycle_sequential_trauma():
    """
    run_75yr_analysis returns Dict[int, StateLedger].
    Each value is a StateLedger snapshot for that age.
    We verify that cumulative trauma accumulates over years via get_planet_state().
    """
    engine = LifecycleEngine()
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

    # Return type is Dict[int, StateLedger]
    assert isinstance(report, dict)
    assert 1 in report
    year_1_ledger = report[1]
    assert isinstance(year_1_ledger, StateLedger), (
        f"Expected StateLedger, got {type(year_1_ledger)}. "
        "run_75yr_analysis returns Dict[int, StateLedger] — not a dict with 'incidents' keys."
    )

    # Trauma can only grow over the lifecycle — check the ledger API
    sun_state_yr1 = year_1_ledger.get_planet_state("Sun")
    assert sun_state_yr1.trauma_points >= 0  # valid float

    # After 75 years of possible strikes, the final ledger must be a StateLedger
    year_75_ledger = report[75]
    assert isinstance(year_75_ledger, StateLedger)
    sun_state_yr75 = year_75_ledger.get_planet_state("Sun")
    # Cumulative trauma must be >= year 1 trauma (monotonically non-decreasing)
    assert sun_state_yr75.trauma_points >= sun_state_yr1.trauma_points

