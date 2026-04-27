import logging
from typing import Dict, Any, List

from .lk_constants import HOUSE_ASPECT_TARGETS
from .doubtful_timing_engine import DoubtfulTimingEngine
from .dormancy_engine import DormancyEngine

logger = logging.getLogger(__name__)

class RashiPhalEvaluator:
    """
    An isolated deterministic evaluator designed specifically to predict life events
    for "Doubtful Promises" (Rashi Phal planets) based purely on thermodynamic state changes.
    """

    def __init__(self):
        self.doubtful_engine = DoubtfulTimingEngine()
        self.baseline_engine = VarshphalTimingEngine()
        self.dormancy_engine = DormancyEngine()

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

        # 2. Check the thermodynamic state (Activation) in the Annual Chart
        annual_pos = self._get_planetary_positions(annual_chart)

        for planet in volatile_planets:
            house = annual_pos.get(planet)
            if not house:
                continue

            # THE TRIGGER: Planetary Activation (Wake-Up)
            is_awake = self.dormancy_engine.is_awake(planet, house, annual_pos)
            
            if is_awake:
                # Filter 1: The "Dead Zone" Houses (Statistical Noise)
                if house in [4, 5, 10]:
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
