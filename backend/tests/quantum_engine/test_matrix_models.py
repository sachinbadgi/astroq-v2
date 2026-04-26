from astroq.quantum_engine.matrix_models import StateVector, VarshphalMatrix

def test_state_vector_initialization():
    sv = StateVector()
    assert len(sv.vector) == 9 # 9 planets
    assert all(len(house_dist) == 12 for house_dist in sv.vector.values())

def test_unitary_evolution():
    sv = StateVector()
    # Put Sun in House 1 (amplitude 1)
    sv.set_planet_house("Sun", 1, 1)
    
    # Apply Age 2 transformation (from 1952 Goswami matrix mapping: House 1 -> House 4)
    matrix = VarshphalMatrix()
    new_sv = matrix.apply_transformation(sv, age=2)
    
    # Sun should now be in House 4 with amplitude 1
    assert new_sv.get_planet_house("Sun") == 4
