from dataclasses import dataclass

@dataclass
class PlanetaryState:
    base_state: str = "Dormant"
    modifier: str = "None" # None, Startled, Supported
    trauma_points: int = 0
    remedy_count: int = 0
    remedy_active_until: int = 0
    is_manda: bool = False

class StateLedger:
    def __init__(self):
        self.planets = {p: PlanetaryState() for p in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]}
    
    def get_planet_state(self, name: str):
        return self.planets[name]
        
    def get_leakage_multiplier(self, name: str) -> float:
        p = self.planets[name]
        if p.modifier == "Startled":
            return 1.5 + (0.2 * p.trauma_points)
        return 1.0 + (0.1 * p.trauma_points)
