from astroq.quantum_engine.matrix_models import StateVector
from astroq.quantum_engine.config import QuantumConfig
from astroq.quantum_engine.entanglement import apply_masnui_gates

def test_sun_venus_artificial_mercury():
    # Sun + Venus = Artificial Mercury (if they are entangled / in same house)
    sv = StateVector()
    config = QuantumConfig(1, -1, 0)
    
    # Put Sun and Venus in House 2
    sv.set_planet_house("Sun", 2, 1) # Constructive
    sv.set_planet_house("Venus", 2, 1) # Constructive
    
    # Put actual Mercury in House 5 just so it exists
    sv.set_planet_house("Mercury", 5, 0)
    
    new_sv = apply_masnui_gates(sv, config)
    
    # Sun and Venus waves should collapse into Mercury in House 2
    assert new_sv.get_planet_house("Sun") == 0 # "Destroyed" or submerged
    assert new_sv.get_planet_house("Venus") == 0
    assert new_sv.get_planet_house("Mercury") == 2
    
    # The amplitude logic could be config-driven, but we'll assert it isn't 0
    # Actually, Sun+Venus is an "Artificial Mercury". We might represent it as Mercury
    # gaining amplitude in House 2.
    # In Lal Kitab, they "transform into a new single logical entity".
    assert new_sv.vector["Mercury"][1] != 0 # House 2 (index 1) has amplitude
