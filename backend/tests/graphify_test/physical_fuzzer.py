import random
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.condition_evaluator import ConditionEvaluator as CE

logger = logging.getLogger(__name__)

class PhysicalChartFuzzer:
    """
    DEEP TEST: Generates PHYSICALLY REAL charts that satisfy astrological rule constraints.
    Instead of mocking house positions, it searches for a date/time that produces the target geometry.
    """
    
    PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]

    # Fixed location: Delhi, India
    LAT = 28.6139
    LON = 77.2090
    TZ = "+05:30"
    PLACE = "Delhi, India"

    def __init__(self, coverage_map_path: str):
        with open(coverage_map_path, "r") as f:
            self.rules = json.load(f)
        self.generator = ChartGenerator()

    def find_chart_for_rule(self, rule: Dict[str, Any], max_attempts: int = 1000) -> Optional[Dict[str, Any]]:
        """
        Searches for a real date/time that satisfies the rule's constraints.
        Uses 'Rotational Search' (scanning hours within a day) to find house matches.
        """
        constraints = rule.get("constraints", [])
        if not constraints:
            # Generate a random real chart
            return self.generator.generate_chart(
                "1990-01-01", "12:00", self.PLACE, self.LAT, self.LON, self.TZ
            )

        # 1. Strategy: 
        #   - Pick a random day in the last 100 years.
        #   - Within that day, scan every 30 minutes (48 charts).
        #   - This rotates the entire chart through all 12 houses.
        
        attempts = 0
        while attempts < max_attempts:
            # Pick a random date between 1940 and 2024
            year = random.randint(1940, 2024)
            month = random.randint(1, 12)
            day = random.randint(1, 28)
            dob_str = f"{year}-{month:02d}-{day:02d}"
            
            # Scan hours to rotate the Lagna
            for hour in range(0, 24):
                for minute in [0, 30]:
                    attempts += 1
                    tob_str = f"{hour:02d}:{minute:02d}"
                    
                    try:
                        chart = self.generator.generate_chart(
                            dob_str, tob_str, self.PLACE, self.LAT, self.LON, self.TZ, 
                            chart_system="kp" # Standard for LK annuals
                        )
                    except Exception:
                        continue
                    
                    if self._check_constraints(chart, constraints):
                        return chart
            
            if attempts > max_attempts:
                break
                
        return None

    def _check_constraints(self, chart: Dict[str, Any], constraints: List[Dict[str, Any]]) -> bool:
        """
        Verifies if the physical chart satisfies the rule constraints, 
        including complex relationships like 'conjoined', 'alone', and 'return'.
        """
        # We need a mock context for relationship lookups
        class MockContext:
            def __init__(self, data):
                self.data = data
                self.planets = data["planets_in_houses"]
            def get_house(self, p):
                return self.planets.get(p, {}).get("house")
            def get_natal_house(self, p):
                return self.planets.get(p, {}).get("house_natal")

        ctx = MockContext(chart)
        
        # 1. Standard Placement Checks
        for c in constraints:
            planet = c["planet"]
            houses = c["houses"]
            chart_type = c["chart_type"]
            rel = c.get("relationship", "placement")
            
            actual_house = ctx.get_natal_house(planet) if chart_type == "natal" else ctx.get_house(planet)
            if actual_house not in houses:
                return False
        
        # 2. Relationship Checks
        conjoined_groups = {} # house -> set of planets
        for c in constraints:
            if c.get("relationship") == "conjoined":
                planet = c["planet"]
                house = ctx.get_house(planet)
                if house not in conjoined_groups: conjoined_groups[house] = set()
                conjoined_groups[house].add(planet)

        # Verify all conjoined planets are actually in the SAME house
        # (Though our loop above already checks placement, we need to ensure they grouped up)
        all_conjoined_planets = [c["planet"] for c in constraints if c.get("relationship") == "conjoined"]
        if all_conjoined_planets:
            first_p = all_conjoined_planets[0]
            target_h = ctx.get_house(first_p)
            for p in all_conjoined_planets:
                if ctx.get_house(p) != target_h:
                    return False

        # Alone Check
        for c in constraints:
            if c.get("relationship") == "alone":
                planet = c["planet"]
                house = ctx.get_house(planet)
                # Count occupants in that house
                occupants = [p for p, data in chart["planets_in_houses"].items() if data["house"] == house]
                if len(occupants) > 1:
                    return False
        
        # Return Check
        for c in constraints:
            if c.get("relationship") == "return":
                planet = c["planet"]
                if ctx.get_house(planet) != ctx.get_natal_house(planet):
                    return False
                
        return True

    def get_rule_by_id(self, rule_id: str) -> Optional[Dict[str, Any]]:
        for r in self.rules:
            if r["rule_id"] == rule_id:
                return r
        return None
