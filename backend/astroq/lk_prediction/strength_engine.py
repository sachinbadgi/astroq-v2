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


# =========================================================================
# Astrological Lookup Tables
# =========================================================================

PLANET_PAKKA_GHAR = {
    "Sun": 1, "Moon": 4, "Mars": 3, "Mercury": 7, "Jupiter": 2,
    "Venus": 7, "Saturn": 10, "Rahu": 12, "Ketu": 6,
}

PLANET_EXALTATION = {
    "Sun": [1], "Moon": [2], "Mars": [10], "Mercury": [6],
    "Jupiter": [4], "Venus": [12], "Saturn": [7],
    "Rahu": [3, 6], "Ketu": [9, 12],
}

PLANET_DEBILITATION = {
    "Sun": [7], "Moon": [8], "Mars": [4], "Mercury": [12],
    "Jupiter": [10], "Venus": [6], "Saturn": [1],
    "Rahu": [9, 12], "Ketu": [3, 6],
}

FIXED_HOUSE_LORDS = {
    1: ["Sun"], 2: ["Jupiter"], 3: ["Mars"],
    4: ["Moon"], 5: ["Jupiter"], 6: ["Ketu"],
    7: ["Venus"], 8: ["Mars", "Saturn"], 9: ["Jupiter"],
    10: ["Saturn"], 11: ["Jupiter"], 12: ["Rahu"],
}

SCAPEGOATS_INFO = {
    "Saturn":  {"Rahu": 0.5, "Ketu": 0.3, "Venus": 0.2},
    "Mercury": {"Venus": 1.0},
    "Mars":    {"Ketu": 1.0},
    "Venus":   {"Moon": 1.0},
    "Jupiter": {"Ketu": 1.0},
    "Sun":     {"Ketu": 1.0},
    "Moon":    {"Jupiter": 0.4, "Sun": 0.3, "Mars": 0.3},
    "Rahu":    {},
    "Ketu":    {},
}

FRIENDS_DATA = {
    "Sun": ["Jupiter", "Mars", "Moon"],
    "Moon": ["Sun", "Mercury"],
    "Mars": ["Sun", "Moon", "Jupiter"],
    "Mercury": ["Sun", "Venus", "Rahu"],
    "Jupiter": ["Sun", "Mars", "Moon"],
    "Venus": ["Saturn", "Mercury", "Ketu"],
    "Saturn": ["Mercury", "Venus", "Rahu"],
    "Rahu": ["Mercury", "Saturn", "Ketu"],
    "Ketu": ["Venus", "Rahu"],
}

ENEMIES_DATA = {
    "Sun": ["Venus", "Saturn", "Rahu", "Ketu"],
    "Moon": ["Rahu", "Ketu"],
    "Mars": ["Mercury", "Ketu"],
    "Mercury": ["Moon"],
    "Jupiter": ["Venus", "Mercury"],
    "Venus": ["Sun", "Moon", "Rahu"],
    "Saturn": ["Sun", "Moon", "Mars"],
    "Rahu": ["Sun", "Venus", "Mars"],
    "Ketu": ["Moon", "Mars"],
}

ASPECT_STRENGTH_DATA = {
    "Jupiter": {"Jupiter": 0, "Sun": 2, "Moon": 0.5, "Venus": 3.75, "Mars": 2, "Mercury": 2, "Saturn": 3, "Rahu": 2, "Ketu": 0.83333},
    "Sun":     {"Jupiter": 0.666667, "Sun": 0, "Moon": 0.75, "Venus": 0.75, "Mars": 2, "Mercury": 0.5, "Saturn": -5, "Rahu": -5, "Ketu": 0.5},
    "Moon":    {"Jupiter": 2, "Sun": 2, "Moon": 0, "Venus": 2, "Mars": 1, "Mercury": 2, "Saturn": 0.333333, "Rahu": 0.5, "Ketu": -5},
    "Venus":   {"Jupiter": 0.5, "Sun": 0.75, "Moon": 0.5, "Venus": 0, "Mars": 1.333333, "Mercury": 1, "Saturn": 0.333333, "Rahu": 2, "Ketu": 2},
    "Mars":    {"Jupiter": 2, "Sun": 2, "Moon": 2, "Venus": 0.333333, "Mars": 0, "Mercury": 2, "Saturn": 1.333333, "Rahu": 0, "Ketu": 0.5},
    "Mercury": {"Jupiter": 0.5, "Sun": 2, "Moon": 0.5, "Venus": 1, "Mars": 1, "Mercury": 0, "Saturn": 1.25, "Rahu": 2, "Ketu": 0.25},
    "Saturn":  {"Jupiter": 1.25, "Sun": 0.666667, "Moon": 0.333333, "Venus": 1.333333, "Mars": 0.333333, "Mercury": 0.8, "Saturn": 0, "Rahu": 2, "Ketu": 0.5},
    "Rahu":    {"Jupiter": 0, "Sun": -5, "Moon": 0.5, "Venus": 0.5, "Mars": 1, "Mercury": 2, "Saturn": 2, "Rahu": 0, "Ketu": 1},
    "Ketu":    {"Jupiter": 2, "Sun": 0.5, "Moon": -5, "Venus": 2, "Mars": 0.5, "Mercury": 0.75, "Saturn": 2, "Rahu": 1, "Ketu": 0},
}

HOUSE_ASPECT_DATA = {
    "1":  {"aspects": {"Outside Help": 5, "General Condition": 7, "Confrontation": 8, "Foundation": 9, "Deception": 10, "Joint Wall": 2, "100 Percent": 7}},
    "2":  {"aspects": {"Outside Help": 6, "General Condition": 8, "Confrontation": 9, "Foundation": 10, "Deception": 11, "Joint Wall": 3, "25 Percent": 6}},
    "3":  {"aspects": {"Outside Help": 7, "General Condition": 9, "Confrontation": 10, "Foundation": 11, "Deception": 12, "Joint Wall": 4, "50 Percent": [9, 11]}},
    "4":  {"aspects": {"Outside Help": 8, "General Condition": 10, "Confrontation": 11, "Foundation": 12, "Deception": 1, "Joint Wall": 5, "100 Percent": 10}},
    "5":  {"aspects": {"Outside Help": 9, "General Condition": 11, "Confrontation": 12, "Foundation": 1, "Deception": 2, "Joint Wall": 6, "50 Percent": [9]}},
    "6":  {"aspects": {"Outside Help": 10, "General Condition": 12, "Confrontation": 1, "Foundation": 2, "Deception": 3, "Joint Wall": 7}},
    "7":  {"aspects": {"Outside Help": 11, "General Condition": 1, "Confrontation": 2, "Foundation": 3, "Deception": 4, "Joint Wall": 8}},
    "8":  {"aspects": {"Outside Help": 12, "General Condition": 2, "Confrontation": 3, "Foundation": 4, "Deception": 5, "Joint Wall": 9, "25 Percent": 2}},
    "9":  {"aspects": {"Outside Help": 1, "General Condition": 3, "Confrontation": 4, "Foundation": 5, "Deception": 6, "Joint Wall": 10}},
    "10": {"aspects": {"Outside Help": 2, "General Condition": 4, "Confrontation": 5, "Foundation": 6, "Deception": 7, "Joint Wall": 11}},
    "11": {"aspects": {"Outside Help": 3, "General Condition": 5, "Confrontation": 6, "Foundation": 7, "Deception": 8, "Joint Wall": 12}},
    "12": {"aspects": {"Outside Help": 4, "General Condition": 6, "Confrontation": 7, "Foundation": 8, "Deception": 9, "Joint Wall": 1}},
}



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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calculate_chart_strengths(self, chart: dict) -> dict[str, Any]:
        """
        Run the full strength pipeline for every planet in *chart*.

        Returns a dict mapping planet name → EnrichedPlanet-like dict.
        """
        planets_data = chart.get("planets_in_houses", {})
        if not planets_data:
            return {}

        chart_type = chart.get("chart_type", "Birth")
        enriched: dict[str, Any] = {}

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
    # Step 1: Raw Aspect Calculation
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
            # Foundation / Outside Help are always positive
            elif aspect_type in ("Foundation", "Out Side help", "Outside Help"):
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
