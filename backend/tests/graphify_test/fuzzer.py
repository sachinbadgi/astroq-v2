import random
import json
from typing import List, Dict, Any, Optional

class ConstraintAwareFuzzer:
    """
    Generates synthetic ChartData to satisfy astrological rule constraints.
    """
    
    PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]

    ENEMIES = {
        "Sun": ["Venus", "Saturn", "Rahu"],
        "Moon": ["Ketu"],
        "Mars": ["Mercury", "Ketu"],
        "Mercury": ["Moon"],
        "Jupiter": ["Venus", "Mercury"],
        "Venus": ["Sun", "Moon", "Rahu"],
        "Saturn": ["Sun", "Moon", "Mars"],
        "Rahu": ["Sun", "Venus", "Mars"],
        "Ketu": ["Moon", "Mars"]
    }

    def __init__(self, coverage_map_path: str):
        with open(coverage_map_path, "r") as f:
            self.rules = json.load(f)

    def generate_chart_for_rule(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates a ChartData dictionary satisfying the rule's constraints.
        """
        planets_in_houses = {}
        
        # 1. Satisfy specific constraints
        constraints = rule.get("constraints", [])

        for c in constraints:
            planet = c["planet"]
            houses = c["houses"]
            chart_type = c["chart_type"]
            
            target_house = random.choice(houses)
            
            if planet not in planets_in_houses:
                planets_in_houses[planet] = {
                    "house": target_house,
                    "house_natal": target_house,
                    "states": []
                }
            
            if chart_type == "natal":
                planets_in_houses[planet]["house_natal"] = target_house
            else:
                planets_in_houses[planet]["house"] = target_house

        # 2. Fill in remaining planets randomly with CONFLICT AVOIDANCE
        # We want to avoid placing an enemy 180 degrees away from a target planet.
        danger_zones = {} # house -> set of enemy planets to avoid placing there
        for p_name, data in planets_in_houses.items():
            h = data["house"]
            opp_h = h + 6
            if opp_h > 12: opp_h -= 12
            
            p_enemies = self.ENEMIES.get(p_name, [])
            if opp_h not in danger_zones:
                danger_zones[opp_h] = set()
            danger_zones[opp_h].update(p_enemies)

        for planet in self.PLANETS:
            if planet not in planets_in_houses:
                # Find a house that isn't a danger zone for this planet
                available_houses = [h for h in range(1, 13) if planet not in danger_zones.get(h, set())]
                if not available_houses:
                    available_houses = list(range(1, 13))
                
                target_house = random.choice(available_houses)
                planets_in_houses[planet] = {
                    "house": target_house,
                    "house_natal": target_house,
                    "states": []
                }

        return {
            "chart_type": "Birth",
            "chart_period": 0,
            "chart_system": "kp",
            "birth_time": "2026-05-04T00:00:00",
            "planets_in_houses": planets_in_houses
        }

    def get_rule_by_id(self, rule_id: str) -> Optional[Dict[str, Any]]:
        for r in self.rules:
            if r["rule_id"] == rule_id:
                return r
        return None
