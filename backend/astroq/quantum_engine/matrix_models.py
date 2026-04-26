import copy

# Using standard lists for minimal dependency overhead, representing a 12x9 state matrix.
# We map planets to indices for easier matrix-like operations if needed.

PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]

class StateVector:
    def __init__(self):
        # A dictionary mapping planet -> list of 12 houses (amplitudes)
        # Index 0 corresponds to House 1, Index 11 corresponds to House 12
        self.vector = {p: [0] * 12 for p in PLANETS}
        
    def set_planet_house(self, planet: str, house: int, amplitude: int):
        """Set the quantum amplitude (-1, 0, 1) for a planet in a specific house (1-12)"""
        if planet in self.vector and 1 <= house <= 12:
            self.vector[planet][house - 1] = amplitude
            
    def get_planet_house(self, planet: str) -> int:
        """Helper to find which house has the non-zero amplitude (returns 1-12)"""
        if planet in self.vector:
            for i, amp in enumerate(self.vector[planet]):
                if amp != 0:
                    return i + 1
        return 0

from astroq.lk_prediction.chart_generator import ChartGenerator

class VarshphalMatrix:
    # Use the authentic 120-Year Goswami Matrix loaded from the main engine
    YEAR_MATRIX = ChartGenerator.YEAR_MATRIX
    
    def apply_transformation(self, natal_sv: StateVector, age: int) -> StateVector:
        """Applies the Unitary Operator for a given age to rotate the state vector."""
        mapping = self.YEAR_MATRIX.get(age, {})
        new_sv = StateVector()
        
        for planet in PLANETS:
            natal_distribution = natal_sv.vector[planet]
            for house_index, amplitude in enumerate(natal_distribution):
                natal_house = house_index + 1
                if amplitude != 0:
                    # Apply rotation
                    annual_house = mapping.get(natal_house, natal_house)
                    new_sv.set_planet_house(planet, annual_house, amplitude)
                    
        return new_sv
