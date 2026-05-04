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
from typing import Any, Optional, Dict

from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.lk_constants import SCAPEGOATS, KARAKA_DOMAIN_MAP
from astroq.lk_prediction.dignity_engine import DignityEngine
from astroq.lk_prediction.aspect_engine import AspectEngine
from astroq.lk_prediction.natal_fate_view import NatalFateView

logger = logging.getLogger(__name__)

class StrengthEngine:
    """
    Calculates planet strengths from raw chart data.
    """

    def __init__(self, config: ModelConfig) -> None:
        self._cfg = config
        self.dignity_engine = DignityEngine(config)
        self.aspect_engine = AspectEngine(config)
        self.fate_view = NatalFateView()

    def calculate_chart_strengths(
        self, 
        chart: dict, 
        natal_chart: Optional[dict] = None,
        ledger: Optional[Any] = None
    ) -> dict[str, Any]:
        """
        Run the full strength pipeline for every planet in *chart*.
        If *ledger* is provided, scapegoat redistribution honors exhaustion states.
        """
        planets_data = chart.get("planets_in_houses", {})
        if not planets_data:
            return {}

        chart_type = chart.get("chart_type", "Birth")
        enriched: dict[str, Any] = {}

        # Pre-calculate fate types for all planets if natal_chart is provided
        fate_map = {}
        if natal_chart:
            fate_entries = self.fate_view.evaluate(natal_chart)
            domain_fate = {e["domain"]: e["fate_type"] for e in fate_entries}
            
            for planet in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]:
                domains = KARAKA_DOMAIN_MAP.get(planet, [])
                if domains:
                    # Use the primary domain's fate
                    fate_map[planet] = domain_fate.get(domains[0], "RASHI_PHAL")
                else:
                    fate_map[planet] = "RASHI_PHAL"

        # Pre-calculate Achanak Chot Triggers if it's a Yearly chart
        if chart_type == "Yearly" and natal_chart:
            natal_pairs = self.aspect_engine.find_achanak_chot_potential_pairs(natal_chart)
            achanak_triggers = self.aspect_engine.detect_annual_achanak_triggers(natal_pairs, chart)
            chart["achanak_chot_triggers"] = achanak_triggers

        # Step 1 + 2: Aspects + Dignity per planet
        for planet, data in planets_data.items():
            house = data.get("house", 0)
            fate_type = fate_map.get(planet, "RASHI_PHAL")

            # --- Step 1: Raw Aspect Calculation ---
            aspects = self.aspect_engine.calculate_planet_aspects(planet, house, planets_data)
            # Persist aspects back to the chart data for downstream rule engines
            data["aspects"] = aspects
            
            raw_aspect_strength = self.aspect_engine.calculate_total_aspect_strength(aspects)

            # --- Step 2: Dignity Scoring ---
            dignity = self._calculate_dignity(planet, house, data, chart_type)

            # ── STEEL VS GLASS LOGIC ──────────────────────────────────────────
            # GRAHA_PHAL (Fixed Fate) is "Steel" — dampened by 80% to ignore noise.
            # RASHI_PHAL (Doubtful Fate) is "Glass" — takes full impact.
            effective_aspect_strength = raw_aspect_strength
            if fate_type == "GRAHA_PHAL":
                effective_aspect_strength = raw_aspect_strength * 0.20
            
            strength_total = dignity + effective_aspect_strength

            enriched[planet] = {
                "house": house,
                "fate_type": fate_type,
                "raw_aspect_strength": raw_aspect_strength,
                "effective_aspect_strength": effective_aspect_strength,
                "dignity_score": dignity,
                "scapegoat_adjustment": 0.0,
                "strength_total": strength_total,
                "aspects": aspects,
                "strength_breakdown": {
                    "aspects": effective_aspect_strength,
                    "dignity": dignity,
                    "scapegoat": 0.0,
                },
            }

        # --- Step 3: Scapegoat Distribution ---
        # User requested consistency: Scapegoat rule applies to both Fixed and Doubtful.
        self._distribute_scapegoats(enriched, ledger)

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

    def _distribute_scapegoats(self, enriched: dict[str, Any], ledger: Optional[Any] = None) -> None:
        """
        Redistribute negative strength from a planet to its scapegoats.
        If ledger is present, only transfers to non-exhausted targets.
        Source planet remains negative if debt cannot be fully transferred.
        """
        for planet in list(enriched.keys()):
            total = float(enriched[planet]["strength_total"])
            if total >= 0:
                continue

            targets = SCAPEGOATS.get(planet, {})
            if not targets:
                continue

            distributed_this_planet = 0.0
            for target, proportion in targets.items():
                if target in enriched:
                    # CANONICAL EXHAUSTION GATE (cite: 1952 Gosvami, p.174)
                    # If target is already "beaten up" (exhausted in state machine), it rejects the debt.
                    is_exhausted = False
                    if ledger:
                        is_exhausted = ledger.is_scapegoat_exhausted(target)
                    
                    if not is_exhausted:
                        amount = total * proportion
                        enriched[target]["strength_total"] += amount
                        enriched[target]["strength_breakdown"]["scapegoat"] = enriched[target]["strength_breakdown"].get("scapegoat", 0.0) + amount
                        distributed_this_planet += amount

            # Adjust source planet by the amount successfully transferred
            enriched[planet]["scapegoat_adjustment"] = -distributed_this_planet
            enriched[planet]["strength_total"] -= distributed_this_planet
            enriched[planet]["strength_breakdown"]["scapegoat"] = -distributed_this_planet
            
            # NOTE: If distributed_this_planet < total (absolute values), 
            # the source planet WILL remain negative. This reflects 
            # the 'Structural Debt' you asked to see.
