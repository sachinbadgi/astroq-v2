from astroq.quantum_engine.config import load_quantum_weights, QuantumConfig

def test_load_default_weights():
    config = load_quantum_weights()
    assert isinstance(config, QuantumConfig)
    assert config.exaltation_amplitude == 1
    assert config.debilitation_amplitude == -1
    assert config.superposed_amplitude == 0
