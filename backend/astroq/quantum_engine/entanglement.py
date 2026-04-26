from astroq.quantum_engine.matrix_models import StateVector
from astroq.quantum_engine.config import QuantumConfig
import copy

def apply_masnui_gates(state_vector: StateVector, config: QuantumConfig) -> StateVector:
    """
    Applies Entanglement logic (Masnui Grah).
    If certain planets share a house (are entangled), they collapse into a new composite state.
    """
    new_sv = copy.deepcopy(state_vector)
    
    # We will iterate through houses to find entanglements
    for house_idx in range(12):
        house_num = house_idx + 1
        
        # Check for Sun + Venus = Mercury
        sun_amp = state_vector.vector["Sun"][house_idx]
        venus_amp = state_vector.vector["Venus"][house_idx]
        
        if sun_amp != 0 and venus_amp != 0:
            # They are entangled in this house
            # Sun and Venus waves collapse (destroy individual identities)
            new_sv.vector["Sun"][house_idx] = 0
            new_sv.vector["Venus"][house_idx] = 0
            
            # Form Artificial Mercury. Amplitude logic can be tuned. We use a sum.
            # But Mercury's original state in another house might need to be overridden or merged.
            # For this simple gate, we just place the artificial planet in this house.
            new_sv.set_planet_house("Mercury", house_num, sun_amp + venus_amp)
            
    return new_sv
