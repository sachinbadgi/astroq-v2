"""
Module 2: Strength Engine.

Calculates the total strength for each planet in a chart through a 4-step
pipeline:

    Step 1  Raw Aspect Calculation
    Step 2  Dignity Scoring (Pakka Ghar, Exalted, Debilitated, FHL, Sign Lord)
    Step 3  Scapegoat Distribution
    Step 4  Natal → Annual Additive Merge (annual charts only)

All weights are loaded from :class:`ModelConfig`.
"""

from __future__ import annotations

from typing import Any

from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.constants import (
    PLANET_PAKKA_GHAR, PLANET_EXALTATION, PLANET_DEBILITATION,
    FIXED_HOUSE_LORDS, SCAPEGOATS_INFO, FRIENDS_DATA, ENEMIES_DATA,
    ASPECT_STRENGTH_DATA, HOUSE_ASPECT_DATA, SUDDEN_STRIKE_HOUSE_SETS
)

class StrengthEngine:
    """
    Calculates planet strengths from raw chart data.

    Parameters
    ----------
    config : ModelConfig
        Centralised configuration instance.
    """

    def __init__(self, config: ModelConfig) -> None:
        self._cfg = config

    # Public API
    # ------------------------------------------------------------------

    def calculate_chart_strengths(self, chart: dict, natal_chart: Optional[dict] = None) -> dict[str, Any]:
        """
        Run the full strength pipeline for every planet in *chart*.

        If chart is Yearly, it incorporates Achanak Chot triggers derived 
        from comparison with *natal_chart*.

        Returns a dict mapping planet name → EnrichedPlanet-like dict.
        """
        planets_data = chart.get("planets_in_houses", {})
        if not planets_data:
            return {}

        chart_type = chart.get("chart_type", "Birth")
        enriched: dict[str, Any] = {}

        # Pre-calculate Achanak Chot Triggers if it's a Yearly chart
        achanak_triggers = []
        if chart_type == "Yearly" and natal_chart:
            natal_pairs = self._find_achanak_chot_potential_pairs(natal_chart)
            achanak_triggers = self._detect_annual_achanak_triggers(natal_pairs, chart)
            chart["achanak_chot_triggers"] = achanak_triggers

        # Step 1 + 2: Aspects + Dignity per planet
        for planet, data in planets_data.items():
            house = data.get("house", 0)

            # --- Step 1: Raw Aspect Calculation ---
            raw_aspect = self._calculate_raw_aspects(planet, data, planets_data)

            # --- Step 2: Dignity Scoring ---
            dignity = self._calculate_dignity(planet, house, data, chart_type)

            # Build initial strength = aspects + dignity
            strength_total = raw_aspect + dignity

            enriched[planet] = {
                "house": house,
                "raw_aspect_strength": raw_aspect,
                "dignity_score": dignity,
                "scapegoat_adjustment": 0.0,
                "strength_total": strength_total,
                "strength_breakdown": {
                    "aspects": raw_aspect,
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
        """
        Additive merge: ``annual_strength += natal_strength`` for each planet.
        """
        import copy
        merged = copy.deepcopy(annual)

        for planet in merged:
            if planet in natal:
                natal_total = natal[planet].get("strength_total", 0.0)
                merged[planet]["strength_total"] = (
                    merged[planet].get("strength_total", 0.0) + natal_total
                )

        return merged

    # ------------------------------------------------------------------
    # Internal Logic: Achanak Chot (Sudden Strike)
    # ------------------------------------------------------------------

    def _find_achanak_chot_potential_pairs(self, natal_chart: dict) -> list[tuple[tuple[str, str], tuple[int, int]]]:
        """
        Identifies pairs of planets in houses that form a potential Sudden Strike
        relationship in the Natal Chart.
        """
        planets_data = natal_chart.get("planets_in_houses", {})
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

    def _detect_annual_achanak_triggers(self, potential_pairs: list, annual_chart: dict) -> list[dict]:
        """
        Checks if potential pairs from Birth significantly aspect each other in Annual.
        Significant types: "100 Percent", "50 Percent", "25 Percent"
        """
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

    # ------------------------------------------------------------------
    # Internal Logic: Strength Calculation
    # ------------------------------------------------------------------

    def _calculate_raw_aspects(self, planet: str, data: dict, all_planets: dict) -> float:
        """Sum aspect contributions based on type and relationship."""
        house = data.get("house", 0)
        
        # If aspects are provided in the data, use them (useful for tests/mocks)
        aspects = data.get("aspects", [])
        
        # Otherwise, dynamically calculate aspects from HOUSE_ASPECT_DATA
        if not aspects and house > 0:
            house_str = str(house)
            house_aspects = HOUSE_ASPECT_DATA.get(house_str, {}).get("aspects", {})
            
            for aspect_type, target_houses in house_aspects.items():
                if target_houses is None:
                    continue
                    
                target_list = target_houses if isinstance(target_houses, list) else [target_houses]
                
                for target_h in target_list:
                    # Find planets in the target house
                    for p_b, d_b in all_planets.items():
                        if d_b.get("house") == target_h:
                            # We found an aspected planet
                            p_b_name = p_b.split(" ")[-1] if "Masnui" in p_b else p_b
                            p_a_name = planet.split(" ")[-1] if "Masnui" in planet else planet
                            
                            aspect_str = ASPECT_STRENGTH_DATA.get(p_a_name, {}).get(p_b_name, 0.0)
                            
                            # Determine relationship
                            if p_b_name in FRIENDS_DATA.get(p_a_name, []):
                                rel = "friend"
                            elif p_b_name in ENEMIES_DATA.get(p_a_name, []):
                                rel = "enemy"
                            else:
                                rel = "equal"
                                
                            aspects.append({
                                "aspect_strength": aspect_str,
                                "aspect_type": aspect_type,
                                "relationship": rel
                            })
                            
            # Save calculated aspects back to data for later steps/modules
            data["aspects"] = aspects

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

    # ------------------------------------------------------------------
    # Step 2: Dignity Scoring
    # ------------------------------------------------------------------

    def _calculate_dignity(
        self, planet: str, house: int, data: dict, chart_type: str
    ) -> float:
        """Compute dignity adjustments based on planet position and states."""
        w_pakka = self._cfg.get("strength.natal.pakka_ghar", fallback=2.20)
        w_exalted = self._cfg.get("strength.natal.exalted", fallback=5.00)
        w_debilitated = self._cfg.get("strength.natal.debilitated", fallback=-5.00)
        w_fhl = self._cfg.get("strength.natal.fixed_house_lord", fallback=1.50)
        annual_factor = self._cfg.get("strength.annual_dignity_factor", fallback=0.50)

        dignity = 0.0
        states = data.get("states", [])

        # Pakka Ghar check
        if PLANET_PAKKA_GHAR.get(planet) == house:
            dignity += w_pakka

        # Exaltation check (state-based OR position-based)
        ex_houses = PLANET_EXALTATION.get(planet, [])
        if "Exalted" in states or house in ex_houses:
            dignity += w_exalted

        # Debilitation check
        deb_houses = PLANET_DEBILITATION.get(planet, [])
        if "Debilitated" in states or house in deb_houses:
            dignity += w_debilitated  # w_debilitated is already negative

        # Fixed House Lord check
        if planet in FIXED_HOUSE_LORDS.get(house, []):
            dignity += w_fhl

        # Dampen for annual charts
        if chart_type == "Yearly":
            dignity *= annual_factor

        return dignity

    # ------------------------------------------------------------------
    # Step 3: Scapegoat Distribution
    # ------------------------------------------------------------------

    def _distribute_scapegoats(self, enriched: dict[str, Any]) -> None:
        """
        Redistribute negative strength from a planet to its scapegoats.

        After redistribution the source planet's strength is set to 0.
        """
        # We iterate over a snapshot of planet names so mutations are safe
        for planet in list(enriched.keys()):
            total = float(enriched[planet]["strength_total"])
            if total >= 0:
                continue

            scapegoats = SCAPEGOATS_INFO.get(planet, {})
            if not scapegoats:
                continue

            distributed_total = 0.0
            for target, proportion in scapegoats.items():
                if target in enriched:
                    amount = total * proportion  # total is negative
                    enriched[target]["strength_total"] += amount
                    enriched[target]["strength_breakdown"]["scapegoat"] = (
                        enriched[target]["strength_breakdown"].get("scapegoat", 0.0)
                        + amount
                    )
                    distributed_total += amount

            # Record adjustment & zero out source
            enriched[planet]["scapegoat_adjustment"] = distributed_total
            old_total = float(enriched[planet]["strength_total"])
            enriched[planet]["strength_total"] = 0.0
            enriched[planet]["strength_breakdown"]["scapegoat"] = -old_total  # offset
