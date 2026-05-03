from typing import Any, List, Optional, Set, Dict
from .lk_constants import STANDARD_PLANETS

class ConditionEvaluator:
    """
    DEEP MODULE: Shared logic for evaluating astrological configurations.
    Leverage: Ensures identical evaluation of 'Placement', 'Conjunction', etc.
    across SQL rules, Pattern dicts, and Grammar modules.
    """

    @staticmethod
    def evaluate_placement(context: Any, planet: str, houses: List[int], chart_type: str = "annual") -> bool:
        """Checks if a planet is in one of the specified houses."""
        get_h = context.get_natal_house if chart_type == "natal" else context.get_house
        actual_house = get_h(planet)
        return actual_house in houses if not isinstance(houses, bool) else (actual_house is not None) == houses

    @staticmethod
    def evaluate_conjunction(context: Any, planets: List[str], chart_type: str = "annual") -> bool:
        """Checks if all listed planets are in the same house."""
        if not planets: return True
        get_h = context.get_natal_house if chart_type == "natal" else context.get_house
        houses = [get_h(p) for p in planets]
        if None in houses: return False
        return len(set(houses)) == 1

    @staticmethod
    def evaluate_house_occupied(context: Any, house: int, occupied: bool = True, chart_type: str = "annual") -> bool:
        """Checks if a house is occupied or empty."""
        get_h = context.get_natal_house if chart_type == "natal" else context.get_house
        any_in = False
        for p in STANDARD_PLANETS:
            if get_h(p) == house:
                any_in = True
                break
        return any_in == occupied

    @staticmethod
    def evaluate_alone(context: Any, planet: str, houses: List[int], chart_type: str = "annual") -> bool:
        """Checks if a planet is in one of the houses and has no other occupants."""
        get_h = context.get_natal_house if chart_type == "natal" else context.get_house
        h = get_h(planet)
        if h not in houses if not isinstance(houses, bool) else (h is not None) != houses:
            return False
        
        count = 0
        for p in STANDARD_PLANETS:
            if get_h(p) == h:
                count += 1
        return count == 1

    @staticmethod
    def evaluate_confrontation(context: Any, p_a: str, p_b: str, chart_type: str = "annual") -> bool:
        """Checks if two planets are in a 1/7 face-to-face relationship."""
        get_h = context.get_natal_house if chart_type == "natal" else context.get_house
        h_a = get_h(p_a)
        h_b = get_h(p_b)
        if h_a is None or h_b is None: return False
        
        # 1/7 check
        diff = abs(h_a - h_b)
        return diff == 6
