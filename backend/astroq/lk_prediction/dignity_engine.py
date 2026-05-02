from typing import Dict, List, Optional
from .lk_constants import (
    PLANET_PAKKA_GHAR,
    PLANET_EXALTATION,
    PLANET_DEBILITATION,
    VARSHPHAL_YEAR_MATRIX,
    ENEMIES
)

class DignityEngine:
    """
    Unified engine for calculating planetary dignity multipliers and scores.
    Centralizes logic used by RulesEngine and StrengthEngine.
    """
    
    def __init__(self, config=None):
        self.config = config

    def get_annual_dignity_multiplier(self, planet: str, natal_house: int, age: int) -> float:
        """
        Calculates the annual dignity multiplier for a planet land in Varshphal rotation.
        Used by RulesEngine to scale rule magnitudes.
        """
        year_map = VARSHPHAL_YEAR_MATRIX.get(age)
        if not year_map or not natal_house:
            return 1.0

        annual_house = year_map.get(natal_house)
        if not annual_house:
            return 1.0

        # Pakka Ghar — strongest positive signal
        if PLANET_PAKKA_GHAR.get(planet) == annual_house:
            return 1.25

        # Exaltation — peak performance
        if annual_house in PLANET_EXALTATION.get(planet, []):
            return 1.15

        # Debilitation — planet struggling
        if annual_house in PLANET_DEBILITATION.get(planet, []):
            return 0.75

        # Enemy territory
        for enemy in ENEMIES.get(planet, []):
            if PLANET_PAKKA_GHAR.get(enemy) == annual_house:
                return 0.85

        return 1.0

    def get_dignity_score(self, planet: str, house: int, states: List[str], weights: Dict[str, float]) -> float:
        """
        Calculates the absolute dignity score for a planet in a house.
        Used by StrengthEngine for base strength calculation.
        """
        from .lk_constants import FIXED_HOUSE_LORDS
        
        dignity = 0.0
        
        # Pakka Ghar check
        if PLANET_PAKKA_GHAR.get(planet) == house:
            dignity += weights.get("pakka_ghar", 2.20)

        # Exaltation check
        ex_houses = PLANET_EXALTATION.get(planet, [])
        if "Exalted" in states or house in ex_houses:
            dignity += weights.get("exalted", 5.00)

        # Debilitation check
        deb_houses = PLANET_DEBILITATION.get(planet, [])
        if "Debilitated" in states or house in deb_houses:
            dignity += weights.get("debilitated", -5.00)

        # Fixed House Lord check
        if planet in FIXED_HOUSE_LORDS.get(house, []):
            dignity += weights.get("fixed_house_lord", 1.50)

        return dignity
