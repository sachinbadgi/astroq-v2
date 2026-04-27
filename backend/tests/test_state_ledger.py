import pytest
from astroq.lk_prediction.state_ledger import StateLedger

def test_ledger_initialization_and_multipliers():
    ledger = StateLedger()
    sun = ledger.get_planet_state("Sun")
    assert sun.trauma_points == 0
    assert ledger.get_leakage_multiplier("Sun") == 1.0 # Pristine
    
    sun.trauma_points = 1
    # Scarring rule: 1.0 + (0.1 * trauma)
    assert abs(ledger.get_leakage_multiplier("Sun") - 1.1) < 0.01
