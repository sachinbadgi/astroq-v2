# backend/tests/lk_prediction/test_state_ledger.py
from astroq.lk_prediction.state_ledger import StateLedger

def test_scapegoat_exhaustion_after_three_hits():
    ledger = StateLedger()
    ledger.record_scapegoat_hit("Ketu")
    ledger.record_scapegoat_hit("Ketu")
    ledger.record_scapegoat_hit("Ketu")
    assert ledger.is_scapegoat_exhausted("Ketu") is True

def test_scapegoat_not_exhausted_below_threshold():
    ledger = StateLedger()
    ledger.record_scapegoat_hit("Venus")
    assert ledger.is_scapegoat_exhausted("Venus") is False
