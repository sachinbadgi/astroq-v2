import pytest
from astroq.lk_prediction.state_ledger import StateLedger

def test_remedy_nexus_recoil_multiplier():
    ledger = StateLedger()
    planet = "Saturn"
    
    # 1. Apply a remedy at age 30
    ledger.apply_remedy(planet, age=30, remedy_id="shift_to_H2")
    
    # 2. Check at age 35 (within maintenance window - assume 5 years for now)
    # If we haven't defined the window, let's assume it requires maintenance every 10 years
    # Recoil applies if age gap > 10
    assert ledger.get_recoil_multiplier(planet, current_age=35) == 1.0
    
    # 3. Check at age 45 (maintenance expired)
    # The gear shatters if not maintained
    assert ledger.get_recoil_multiplier(planet, current_age=45) == 2.0

def test_remedy_reset_recoil():
    ledger = StateLedger()
    planet = "Jupiter"
    
    # Apply remedy at 30
    ledger.apply_remedy(planet, age=30, remedy_id="donate_turmeric")
    
    # At 45, recoil is active
    assert ledger.get_recoil_multiplier(planet, current_age=45) == 2.0
    
    # Perform maintenance at 45
    ledger.apply_remedy(planet, age=45, remedy_id="donate_turmeric")
    
    # Recoil is reset
    assert ledger.get_recoil_multiplier(planet, current_age=46) == 1.0
