import json
import os
from dataclasses import dataclass

@dataclass
class QuantumConfig:
    exaltation_amplitude: int
    debilitation_amplitude: int
    superposed_amplitude: int
    masnui_entanglement_multiplier: float
    annual_rotation_boost: float

def load_quantum_weights(filepath=None) -> QuantumConfig:
    if not filepath:
        filepath = os.path.join(os.path.dirname(__file__), 'quantum_weights.json')
    with open(filepath, 'r') as f:
        data = json.load(f)
    amps = data.get("amplitudes", {})
    multipliers = data.get("multipliers", {})
    return QuantumConfig(
        exaltation_amplitude=amps.get("exaltation", 1),
        debilitation_amplitude=amps.get("debilitation", -1),
        superposed_amplitude=amps.get("superposed", 0),
        masnui_entanglement_multiplier=multipliers.get("masnui_entanglement", 1.0),
        annual_rotation_boost=multipliers.get("annual_rotation", 1.0)
    )
