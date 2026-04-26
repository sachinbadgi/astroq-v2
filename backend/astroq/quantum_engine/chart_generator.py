from astroq.quantum_engine.matrix_models import StateVector, VarshphalMatrix, PLANETS
from astroq.quantum_engine.config import load_quantum_weights
from astroq.quantum_engine.entanglement import apply_masnui_gates

class QuantumChartGenerator:
    def __init__(self, config_path=None):
        self.config = load_quantum_weights(config_path)
        self.matrix_operator = VarshphalMatrix()
        
    def _dict_to_vector(self, chart_data: dict) -> StateVector:
        """Converts standard ChartData format into a Quantum StateVector."""
        sv = StateVector()
        planets_data = chart_data.get("planets_in_houses", {})
        
        for planet in PLANETS:
            if planet in planets_data:
                # Get the house
                house = planets_data[planet].get("house", 1)
                
                # Determine amplitude based on dignity
                states = planets_data[planet].get("states", [])
                
                if "Exalted" in states or "Fixed House Lord" in states:
                    amplitude = self.config.exaltation_amplitude
                elif "Debilitated" in states:
                    amplitude = self.config.debilitation_amplitude
                else:
                    # Normal planet
                    amplitude = 1
                
                sv.set_planet_house(planet, house, amplitude)
                
        return sv
        
    def _vector_to_dict(self, sv: StateVector, age: int) -> dict:
        """Converts a Quantum StateVector back into a ChartData format dict."""
        chart_dict = {
            "chart_period": age,
            "chart_type": "Birth" if age == 0 else "Yearly",
            "planets_in_houses": {}
        }
        
        for planet in PLANETS:
            house = sv.get_planet_house(planet)
            if house != 0:
                # Find the amplitude
                amplitude = sv.vector[planet][house - 1]
                chart_dict["planets_in_houses"][planet] = {
                    "house": house,
                    "amplitude": amplitude
                }
                
        return chart_dict

    def generate_quantum_timeline(self, natal_data: dict, max_years: int = 120) -> dict:
        """
        Generates the full timeline of charts using matrix unitary evolution.
        """
        results = {}
        
        # 1. Base Natal Vector
        natal_sv = self._dict_to_vector(natal_data)
        
        # 2. Entangle the Natal Vector
        natal_entangled_sv = apply_masnui_gates(natal_sv, self.config)
        results["chart_0"] = self._vector_to_dict(natal_entangled_sv, 0)
        
        # 3. Apply Unitary Operations for all years
        for age in range(1, max_years + 1):
            # Rotate
            annual_sv = self.matrix_operator.apply_transformation(natal_sv, age)
            # Entangle in the new positions
            annual_entangled_sv = apply_masnui_gates(annual_sv, self.config)
            
            results[f"chart_{age}"] = self._vector_to_dict(annual_entangled_sv, age)
            
        return results
