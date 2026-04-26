from astroq.quantum_engine.matrix_models import StateVector
from astroq.quantum_engine.config import QuantumConfig
import copy

# Canonical Masnui (Artificial Planet) formation rules from lk_constants.txt MASNUI_FORMATION_RULES
# Format: (planet_a, planet_b, artificial_planet_name, mapped_standard_planet)
# mapped_standard_planet = which planet's house in StateVector gets the composite amplitude boost
#
# Key design decision (Quantum model):
#   - Masnui formation creates an ADDITIONAL quantum signal, it does NOT erase the original planets.
#   - The original planets continue to exert their natal karaka influence independently.
#   - The Masnui adds a combined "bonus" amplitude to the resulting planet (like constructive interference).
#   - Erasing Venus whenever Sun+Venus are conjunct was destroying marriage predictions for 22% of charts.
#
# Supported rules (subset — highest structural impact):
MASNUI_RULES = [
    # (planet_a, planet_b, composite_boost_planet, amplitude_factor)
    ("Sun",     "Venus",   "Jupiter", 1.0),   # Sun+Venus → Artificial Jupiter (wealth/wisdom boost)
    ("Jupiter", "Rahu",    "Mercury", 0.8),   # Jupiter+Rahu → Artificial Mercury (intellect, but debased)
    ("Sun",     "Jupiter", "Moon",    1.0),   # Sun+Jupiter → Artificial Moon (emotional/mind boost)
    ("Sun",     "Mercury", "Mars",    0.7),   # Sun+Mercury → Artificial Mars (Auspicious)
    ("Venus",   "Jupiter", "Saturn",  0.6),   # Venus+Jupiter → Artificial Saturn (Like Ketu)
    ("Mars",    "Mercury", "Saturn",  0.5),   # Mars+Mercury → Artificial Saturn (Like Rahu)
]


def apply_masnui_gates(state_vector: StateVector, config: QuantumConfig) -> StateVector:
    """
    Applies Masnui Grah (Artificial Planet) entanglement logic.
    
    Per canonical Lal Kitab rules (lk_constants.txt MASNUI_FORMATION_RULES):
    - When two specific planets share a house, they create an ADDITIONAL composite planet.
    - The original planets RETAIN their individual amplitudes and karaka roles.
    - The composite creates a constructive interference boost to the resulting planet.
    
    This corrects the previous implementation which was incorrectly:
    1. Erasing Venus when Sun+Venus shared a house (destroying 22% of marriage predictions)
    2. Using Sun+Venus → Artificial Mercury (wrong; canonical rule is → Artificial Jupiter)
    """
    new_sv = copy.deepcopy(state_vector)
    
    for house_idx in range(12):
        house_num = house_idx + 1
        
        for planet_a, planet_b, composite_planet, factor in MASNUI_RULES:
            amp_a = state_vector.vector[planet_a][house_idx]
            amp_b = state_vector.vector[planet_b][house_idx]
            
            # Both planets must be in this house with positive amplitude
            if amp_a > 0 and amp_b > 0:
                # Composite amplitude = geometric mean * factor (constructive interference)
                composite_amp = ((amp_a * amp_b) ** 0.5) * factor
                
                # ADD to the composite planet's amplitude (don't replace — multiple rules may apply)
                current = new_sv.vector[composite_planet][house_idx]
                new_sv.vector[composite_planet][house_idx] = current + composite_amp
                
                # NOTE: Original planet amplitudes are preserved — they continue to exert
                # their individual karaka influence independently of the Masnui formation.
    
    return new_sv
