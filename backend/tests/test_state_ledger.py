import pytest
from astroq.lk_prediction.state_ledger import StateLedger

def test_ledger_initialization_and_multipliers():
    ledger = StateLedger()
    sun = ledger.get_planet_state("Sun")
    assert sun.trauma_points == 0
    assert ledger.get_leakage_multiplier("Sun") == 1.0  # Pristine — no trauma

    # Manually set trauma below Sun's leak_threshold (0.8) to stay in decay range
    sun.trauma_points = 1
    # Base decay formula: max(0, 1.0 - (0.1 * trauma_points)) = 1.0 - 0.1 = 0.9
    # Sun's leak_threshold = 0.8 so 1.0 trauma triggers Leaking → multiplier = 0.5
    # Apply via apply_trauma so _update_thresholds runs
    ledger2 = StateLedger()
    ledger2.apply_trauma("Sun", 0.5)  # 0.5 < 0.8 leak_threshold → still in decay range
    assert abs(ledger2.get_leakage_multiplier("Sun") - 0.95) < 0.01  # 1.0 - (0.1*0.5)
