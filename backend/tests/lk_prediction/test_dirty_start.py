# backend/tests/lk_prediction/test_dirty_start.py
from astroq.lk_prediction.state_ledger import StateLedger

def test_dirty_start_reduces_burst_threshold_for_traumatized_planet():
    ledger = StateLedger()
    ledger.planets["Saturn"].trauma_points = 2.5  # Heavy trauma
    original_threshold = ledger.planets["Saturn"].burst_threshold
    ledger.apply_dirty_start_penalty()
    assert ledger.planets["Saturn"].burst_threshold < original_threshold

def test_clean_planet_unaffected_by_dirty_start():
    ledger = StateLedger()
    # Saturn with 0 trauma — no degradation
    ledger.planets["Saturn"].trauma_points = 0.0
    original_threshold = ledger.planets["Saturn"].burst_threshold
    ledger.apply_dirty_start_penalty()
    assert ledger.planets["Saturn"].burst_threshold == original_threshold
