import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from .lk_constants import (
    ASPECT_STRENGTH_DATA,
    HOUSE_ASPECT_DATA,
    FRIENDS,
    ENEMIES,
    SUDDEN_STRIKE_HOUSE_PAIRS as SUDDEN_STRIKE_HOUSE_SETS
)

logger = logging.getLogger(__name__)

class AspectEngine:
    """
    DEEP MODULE: Encapsulates all Lal Kitab aspect calculation logic.
    Centralizes the detection of:
    1. 100%, 50%, 25% Aspects.
    2. Special Aspects: Foundation, Confrontation, Sudden Strike, etc.
    3. Annual Achanak Chot (Sudden Strike) triggers.
    """
    
    def __init__(self, config=None):
        self.config = config

    def calculate_planet_aspects(self, planet: str, house: int, all_planets: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Calculates all aspects for a given planet in its current house.
        Returns a list of aspect metadata dicts.
        """
        aspects = []
        if house <= 0:
            return aspects

        house_aspects = HOUSE_ASPECT_DATA.get(house, {})
        for aspect_type, target_houses in house_aspects.items():
            if target_houses is None:
                continue
                
            target_list = [target_houses] if isinstance(target_houses, int) else target_houses
            
            for target_h in target_list:
                # Find planets in the target house
                for p_b, d_b in all_planets.items():
                    if d_b.get("house") == target_h:
                        # We found an aspected planet
                        p_b_name = p_b.split(" ")[-1] if "Masnui" in p_b else p_b
                        p_a_name = planet.split(" ")[-1] if "Masnui" in planet else planet
                        
                        aspect_str = ASPECT_STRENGTH_DATA.get(p_a_name, {}).get(p_b_name, 0.0)
                        
                        # Determine relationship
                        if p_b_name in FRIENDS.get(p_a_name, []):
                            rel = "friend"
                        elif p_b_name in ENEMIES.get(p_a_name, []):
                            rel = "enemy"
                        else:
                            rel = "equal"
                            
                        # Tag Takkar (1-8 opposition axis) aspects explicitly
                        # 1-8 pairs: {1,8},{2,9},{3,10},{4,11},{5,12},{6,7}
                        is_takkar = frozenset({house, target_h}) in (
                            frozenset({1,8}), frozenset({2,9}), frozenset({3,10}),
                            frozenset({4,11}), frozenset({5,12}), frozenset({6,7})
                        )
                        aspects.append({
                            "target": p_b_name,
                            "target_house": target_h,
                            "aspect_strength": aspect_str,
                            "aspect_type": aspect_type,
                            "relationship": rel,
                            "aspecting_planet": planet,
                            "axis_type": "TAKKAR" if is_takkar else None,
                        })
        return aspects

    def calculate_total_aspect_strength(self, aspects: List[Dict[str, Any]]) -> float:
        """Sums aspect contributions based on type and relationship."""
        total = 0.0
        for aspect in aspects:
            strength = aspect.get("aspect_strength", 0.0)
            aspect_type = aspect.get("aspect_type", "")
            relationship = aspect.get("relationship", "equal")

            # Confrontation / Sudden Strike are always negative
            if aspect_type in ("Confrontation", "Sudden Strike"):
                total -= abs(float(strength))
            # Foundation / Outside Help / Joint Wall / Deception are always positive/growth
            elif aspect_type in ("Foundation", "Out Side help", "Outside Help", "Joint Wall", "Deception"):
                total += abs(float(strength))
            # Others depend on relationship
            else:
                if relationship == "friend":
                    total += abs(float(strength))
                elif relationship == "enemy":
                    total -= abs(float(strength))
                else:
                    total += float(strength)  # equal — use as-is
        return total

    def find_achanak_chot_potential_pairs(self, chart_data: Dict[str, Any]) -> List[Tuple[Tuple[str, str], Tuple[int, int]]]:
        """Identifies natal potential for Sudden Strike."""
        planets_data = chart_data.get("planets_in_houses", {})
        all_planets = list(planets_data.keys())
        potential_pairs = []

        for i in range(len(all_planets)):
            p1 = all_planets[i]
            h1 = planets_data[p1].get("house")
            if not h1: continue

            for j in range(i + 1, len(all_planets)):
                p2 = all_planets[j]
                h2 = planets_data[p2].get("house")
                if not h2: continue
                if h1 == h2: continue

                house_set = {h1, h2}
                for strike_set in SUDDEN_STRIKE_HOUSE_SETS:
                    if house_set == strike_set:
                        potential_pairs.append((tuple(sorted((p1, p2))), tuple(sorted((h1, h2)))))
                        break
        return potential_pairs

    def detect_annual_achanak_triggers(self, potential_pairs: List, annual_chart: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Checks if potential pairs from Birth significantly aspect each other in Annual."""
        annual_planets = annual_chart.get("planets_in_houses", {})
        triggers = []
        significant_types = {"100 Percent", "50 Percent", "25 Percent"}

        for (p1_name, p2_name), birth_houses in potential_pairs:
            p1_annual = annual_planets.get(p1_name)
            p2_annual = annual_planets.get(p2_name)

            if not p1_annual or not p2_annual:
                continue

            triggered = False
            # Check p1 -> p2 aspects
            for aspect in p2_annual.get("aspects", []):
                if aspect.get("aspect_type") in significant_types and aspect.get("aspecting_planet") == p1_name:
                    triggered = True
                    break
            
            if not triggered:
                # Check p2 -> p1 aspects
                for aspect in p1_annual.get("aspects", []):
                    if aspect.get("aspect_type") in significant_types and aspect.get("aspecting_planet") == p2_name:
                        triggered = True
                        break
            
            if triggered:
                triggers.append({
                    "planets": [p1_name, p2_name],
                    "birth_houses": list(birth_houses),
                    "annual_houses": [p1_annual["house"], p2_annual["house"]]
                })
        return triggers
