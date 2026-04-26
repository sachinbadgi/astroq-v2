import logging
from typing import Dict, Any, List

from .lk_constants import HOUSE_ASPECT_TARGETS
from .doubtful_timing_engine import DoubtfulTimingEngine
from .varshphal_timing_engine import VarshphalTimingEngine

logger = logging.getLogger(__name__)

class RashiPhalEvaluator:
    """
    An isolated deterministic evaluator designed specifically to predict life events
    for "Doubtful Promises" (Rashi Phal planets) based purely on thermodynamic state changes.
    """

    def __init__(self):
        self.doubtful_engine = DoubtfulTimingEngine()
        self.baseline_engine = VarshphalTimingEngine()

        # Strict Karaka Domain Mapping
        self.karaka_domain_map = {
            "Venus": ["marriage"],
            "Jupiter": ["career_travel", "progeny", "finance"],
            "Mercury": ["career_travel", "finance"],
            "Sun": ["career_travel", "health"],
            "Moon": ["health", "marriage"],
            "Mars": ["health", "career_travel"],
            "Saturn": ["career_travel", "health"],
            "Rahu": ["health", "career_travel"],
            "Ketu": ["progeny", "health"]
        }

    def evaluate(self, natal_chart: Dict[str, Any], annual_chart: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Evaluate a given year for deterministic Rashi Phal triggers.
        Returns a list of predicted events (domains) with High confidence if triggered.
        """
        triggers = []
        
        # 1. Identify Doubtful (Rashi Phal) planets in Natal
        doubtful_promises = self.doubtful_engine._identify_doubtful_natal_promises(natal_chart)
        if not doubtful_promises:
            return triggers

        volatile_planets = set()
        for p in doubtful_promises:
            for planet in p.get("planets", []):
                volatile_planets.add(planet)

        # 2. Check the thermodynamic state (Dormancy) in the Annual Chart
        annual_pos = self._get_planetary_positions(annual_chart)

        for planet in volatile_planets:
            is_dormant, woken_by_fwd, woken_by_aspect = self._check_dormancy_state(planet, annual_pos)
            
            # THE TRIGGER: Loss of Dormancy (Wake-Up)
            if not is_dormant:
                house = annual_pos.get(planet)
                
                # Filter 1: The "Dead Zone" Houses (Statistical Noise)
                if house in [1, 4, 5, 10]:
                    continue
                    
                # Filter 2: The Confidence Multipliers
                confidence = "High"
                if woken_by_fwd and woken_by_aspect:
                    confidence = "Highest (Double Strike)"
                if planet == "Venus" and house == 7:
                    confidence = "Highest (H7 Super-Trigger)"

                domains = self.karaka_domain_map.get(planet, [])
                for domain in domains:
                    triggers.append({
                        "domain": domain,
                        "confidence": confidence,
                        "triggering_planet": planet,
                        "reason": f"Rashi Phal Evaluator: Doubtful {planet} lost dormancy and woke up in House {house}."
                    })

        return triggers

    def _get_planetary_positions(self, chart: Dict) -> Dict[str, int]:
        """Extract planetary positions, ignoring Lagna."""
        if not chart or "planets_in_houses" not in chart:
            return {}
        return {
            p: d["house"] for p, d in chart["planets_in_houses"].items() if p != "Lagna"
        }

    def _check_dormancy_state(self, planet: str, ppos: Dict[str, int]) -> tuple[bool, bool, bool]:
        """
        Calculates if a planet is Dormant (Soyi Hui) based on canonical Lal Kitab rules.
        Returns: (is_dormant, woken_by_forward_planet, woken_by_aspect)
        """
        house = ppos.get(planet)
        if not house:
            return False, False, False

        # Rule 1: Houses 1 to 6 from the planet's house must be empty
        woken_by_fwd = False
        for offset in range(1, 7):
            target_house = ((house - 1 + offset) % 12) + 1
            if any(h == target_house for p, h in ppos.items() if p != planet):
                woken_by_fwd = True
                break

        # Rule 2: Planet must not be aspected by any other planet
        woken_by_aspect = False
        aspecting_houses = []
        for h1, targets in HOUSE_ASPECT_TARGETS.items():
            if house in targets:
                aspecting_houses.append(h1)

        for p, h in ppos.items():
            if p != planet and h in aspecting_houses:
                woken_by_aspect = True
                break

        is_dormant = not woken_by_fwd and not woken_by_aspect
        return is_dormant, woken_by_fwd, woken_by_aspect
