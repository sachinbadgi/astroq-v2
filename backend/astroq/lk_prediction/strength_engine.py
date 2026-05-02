"""
Module 2: Strength Engine.

Calculates the total strength for each planet in a chart through a 4-step
pipeline:

    Step 1  Raw Aspect Calculation (via AspectEngine)
    Step 2  Dignity Scoring (Pakka Ghar, Exalted, Debilitated, FHL, Sign Lord)
    Step 3  Scapegoat Distribution
    Step 4  Natal → Annual Additive Merge (annual charts only)

All weights are loaded from :class:`ModelConfig`.
"""

from __future__ import annotations

import copy
import logging
from typing import Any, Optional

from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.lk_constants import SCAPEGOATS
from astroq.lk_prediction.dignity_engine import DignityEngine
from astroq.lk_prediction.aspect_engine import AspectEngine

logger = logging.getLogger(__name__)

class StrengthEngine:
    """
    Calculates planet strengths from raw chart data.
    """

    def __init__(self, config: ModelConfig) -> None:
        self._cfg = config
        self.dignity_engine = DignityEngine(config)
        self.aspect_engine = AspectEngine(config)

    def calculate_chart_strengths(self, chart: dict, natal_chart: Optional[dict] = None) -> dict[str, Any]:
        """
        Run the full strength pipeline for every planet in *chart*.
        """
        planets_data = chart.get("planets_in_houses", {})
        if not planets_data:
            return {}

        chart_type = chart.get("chart_type", "Birth")
        enriched: dict[str, Any] = {}

        # Pre-calculate Achanak Chot Triggers if it's a Yearly chart
        if chart_type == "Yearly" and natal_chart:
            natal_pairs = self.aspect_engine.find_achanak_chot_potential_pairs(natal_chart)
            achanak_triggers = self.aspect_engine.detect_annual_achanak_triggers(natal_pairs, chart)
            chart["achanak_chot_triggers"] = achanak_triggers

        # Step 1 + 2: Aspects + Dignity per planet
        for planet, data in planets_data.items():
            house = data.get("house", 0)

            # --- Step 1: Raw Aspect Calculation ---
            aspects = self.aspect_engine.calculate_planet_aspects(planet, house, planets_data)
            # Persist aspects back to the chart data for downstream rule engines
            data["aspects"] = aspects
            
            raw_aspect_strength = self.aspect_engine.calculate_total_aspect_strength(aspects)

            # --- Step 2: Dignity Scoring ---
            dignity = self._calculate_dignity(planet, house, data, chart_type)

            # Build initial strength = aspects + dignity
            strength_total = raw_aspect_strength + dignity

            enriched[planet] = {
                "house": house,
                "raw_aspect_strength": raw_aspect_strength,
                "dignity_score": dignity,
                "scapegoat_adjustment": 0.0,
                "strength_total": strength_total,
                "aspects": aspects,
                "strength_breakdown": {
                    "aspects": raw_aspect_strength,
                    "dignity": dignity,
                    "scapegoat": 0.0,
                },
            }

        # --- Step 3: Scapegoat Distribution ---
        self._distribute_scapegoats(enriched)

        return enriched

    def merge_natal_annual(
        self, natal: dict[str, Any], annual: dict[str, Any]
    ) -> dict[str, Any]:
        """Additive merge: annual_strength += natal_strength."""
        merged = copy.deepcopy(annual)
        for planet in merged:
            if planet in natal:
                natal_total = natal[planet].get("strength_total", 0.0)
                merged[planet]["strength_total"] = merged[planet].get("strength_total", 0.0) + natal_total
        return merged

    def _calculate_dignity(
        self, planet: str, house: int, data: dict, chart_type: str
    ) -> float:
        """Compute dignity adjustments based on planet position and states."""
        weights = {
            "pakka_ghar": self._cfg.get("strength.natal.pakka_ghar", fallback=2.20),
            "exalted": self._cfg.get("strength.natal.exalted", fallback=5.00),
            "debilitated": self._cfg.get("strength.natal.debilitated", fallback=-5.00),
            "fixed_house_lord": self._cfg.get("strength.natal.fixed_house_lord", fallback=1.50),
        }
        annual_factor = self._cfg.get("strength.annual_dignity_factor", fallback=0.50)

        dignity = self.dignity_engine.get_dignity_score(planet, house, data.get("states", []), weights)

        if chart_type == "Yearly":
            dignity *= annual_factor

        return dignity

    def _distribute_scapegoats(self, enriched: dict[str, Any]) -> None:
        """Redistribute negative strength from a planet to its scapegoats."""
        for planet in list(enriched.keys()):
            total = float(enriched[planet]["strength_total"])
            if total >= 0:
                continue

            scapegoats = SCAPEGOATS.get(planet, {})
            if not scapegoats:
                continue

            distributed_total = 0.0
            for target, proportion in scapegoats.items():
                if target in enriched:
                    amount = total * proportion
                    enriched[target]["strength_total"] += amount
                    enriched[target]["strength_breakdown"]["scapegoat"] = enriched[target]["strength_breakdown"].get("scapegoat", 0.0) + amount
                    distributed_total += amount

            enriched[planet]["scapegoat_adjustment"] = -distributed_total
            old_total = float(enriched[planet]["strength_total"])
            enriched[planet]["strength_total"] = 0.0
            enriched[planet]["strength_breakdown"]["scapegoat"] = -old_total
