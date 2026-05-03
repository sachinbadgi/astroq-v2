from typing import Any, Dict, List, Set, Protocol, Optional
from .lk_constants import STANDARD_PLANETS

from .condition_evaluator import ConditionEvaluator as CE

class Condition(Protocol):
    def evaluate(self, context: Any, chart_type: str = "annual") -> bool:
        ...

class PlanetInHouseCondition:
    def __init__(self, planet: str, houses: List[int]):
        self.planet = planet
        self.houses = houses

    def evaluate(self, context: Any, chart_type: str = "annual") -> bool:
        return CE.evaluate_placement(context, self.planet, self.houses, chart_type)

class ConjunctionCondition:
    def __init__(self, planets: List[str]):
        self.planets = planets

    def evaluate(self, context: Any, chart_type: str = "annual") -> bool:
        return CE.evaluate_conjunction(context, self.planets, chart_type)

class HouseOccupiedCondition:
    def __init__(self, house: int, occupied: bool = True):
        self.house = house
        self.occupied = occupied

    def evaluate(self, context: Any, chart_type: str = "annual") -> bool:
        return CE.evaluate_house_occupied(context, self.house, self.occupied, chart_type)

class PlanetAloneCondition:
    def __init__(self, planet: str, houses: List[int]):
        self.planet = planet
        self.houses = houses

    def evaluate(self, context: Any, chart_type: str = "annual") -> bool:
        return CE.evaluate_alone(context, self.planet, self.houses, chart_type)

class ReturnCondition:
    def __init__(self, planets: List[str]):
        self.planets = planets

    def evaluate(self, context: Any, chart_type: str = "annual") -> bool:
        # Return only makes sense as a comparison between annual and natal
        for p in self.planets:
            if context.get_house(p) != context.get_natal_house(p):
                return False
        return True

class HouseSetCondition:
    def __init__(self, houses: List[int], mode: str = "any_occupied"):
        self.houses = houses
        self.mode = mode # any_occupied, all_empty

    def evaluate(self, context: Any, chart_type: str = "annual") -> bool:
        if self.mode == "any_occupied":
            return any(CE.evaluate_house_occupied(context, h, True, chart_type) for h in self.houses)
        if self.mode == "all_empty":
            return all(CE.evaluate_house_occupied(context, h, False, chart_type) for h in self.houses)
        return False


class OrCondition:
    def __init__(self, conditions: List[Condition]):
        self.conditions = conditions

    def evaluate(self, context: Any, chart_type: str = "annual") -> bool:
        return any(c.evaluate(context, chart_type) for c in self.conditions)


class PatternMatcher:
    """
    Deep Module: Compiles static trigger definitions into executable Condition trees.
    """
    PLANET_MAP = {
        "Sat": "Saturn", "Ket": "Ketu", "Mer": "Mercury", "Mon": "Moon", 
        "Jup": "Jupiter", "Sun": "Sun", "Rah": "Rahu", "Ven": "Venus", "Mar": "Mars"
    }

    def __init__(self):
        self._cache: Dict[str, List[Condition]] = {}

    def compile_rule(self, rule: Dict[str, Any]) -> List[Condition]:
        conditions = []
        for key, val in rule.items():
            if key in ["desc", "polarity", "outcome", "target", "is_blocked", "is_premature", "sustenance_factor"]:
                continue
            
            chart_type = "natal" if key.startswith("natal_") else "annual"
            sub_key = key.replace("natal_", "").replace("annual_", "")

            # 1. Conjunctions (e.g., sun_sat_conjoined)
            if sub_key.endswith("_conjoined"):
                planets_abbr = sub_key.replace("_conjoined", "").split("_")
                planets = [self.PLANET_MAP.get(p.capitalize()) for p in planets_abbr if self.PLANET_MAP.get(p.capitalize())]
                if planets:
                    conditions.append((ConjunctionCondition(planets), chart_type))
            
            # 2. Alone (e.g., mer_alone)
            elif sub_key.endswith("_alone"):
                p_abbr = sub_key.replace("_alone", "").capitalize()
                planet = self.PLANET_MAP.get(p_abbr)
                if planet:
                    conditions.append((PlanetAloneCondition(planet, val), chart_type))

            # 3. Returns (e.g., ven_mer_return)
            elif sub_key.endswith("_return"):
                planets_abbr = sub_key.replace("_return", "").split("_")
                planets = [self.PLANET_MAP.get(p.capitalize()) for p in planets_abbr if self.PLANET_MAP.get(p.capitalize())]
                if planets:
                    conditions.append((ReturnCondition(planets), "annual"))

            # 4. Special House Sets (e.g., 2_7_blank)
            elif sub_key == "2_7_blank":
                mode = "all_empty" if val else "any_occupied"
                conditions.append((HouseSetCondition([2, 7], mode), chart_type))

            # 5. Enemies (e.g., enemies_in_2_7)
            elif sub_key == "enemies_in_2_7":
                # Sun, Moon, Rahu are the relevant enemies here (per old logic)
                for p in ["Sun", "Moon", "Rahu"]:
                    conditions.append((PlanetInHouseCondition(p, [2, 7]), chart_type))

            # 6. House Occupancy (e.g., 8_empty, 5_occupied)
            elif "_occupied" in sub_key or "_empty" in sub_key:
                h_str = sub_key.split("_")[0]
                if h_str.isdigit():
                    house = int(h_str)
                    occupied = "_occupied" in sub_key
                    if not occupied and "_empty" in sub_key:
                        occupied = not val if isinstance(val, bool) else False
                    conditions.append((HouseOccupiedCondition(house, occupied), chart_type))

            # 7. Combined keys (e.g., ket_sat_rah)
            elif "_" in sub_key:
                planets_abbr = sub_key.split("_")
                planets = [self.PLANET_MAP.get(p.capitalize()) for p in planets_abbr if self.PLANET_MAP.get(p.capitalize())]
                if planets:
                    # SPECIAL CASE: ven_mer is typically an "OR" condition in Lal Kitab logic
                    if sub_key == "ven_mer":
                        from .pattern_matcher import HouseSetCondition as HSC
                        # We use a custom lambda or similar? No, let's add an OrCondition.
                        conditions.append((OrCondition([PlanetInHouseCondition(p, val) for p in planets]), chart_type))
                    else:
                        # In combined keys, usually means ALL must be in the target houses
                        for p in planets:
                            conditions.append((PlanetInHouseCondition(p, val), chart_type))

            # 8. Standard single planet (e.g., sat, sun)
            else:
                p_abbr = sub_key.capitalize()
                planet = self.PLANET_MAP.get(p_abbr)
                if planet:
                    conditions.append((PlanetInHouseCondition(planet, val), chart_type))
                    
        return conditions

    def matches(self, rule: Dict[str, Any], context: Any) -> bool:
        # Simple cache for compiled rules
        rule_id = rule.get("desc", str(rule))
        if rule_id not in self._cache:
            self._cache[rule_id] = self.compile_rule(rule)
        
        compiled_conditions = self._cache[rule_id]
        for cond, chart_type in compiled_conditions:
            if not cond.evaluate(context, chart_type):
                return False
        return True
