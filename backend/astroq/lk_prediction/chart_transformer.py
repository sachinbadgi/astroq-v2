"""
ChartTransformer
================
Pure transformation logic extracted from ChartGenerator.

No flatlib/VedicHoroscopeData dependency. Takes a planet->house mapping
and produces ChartData dicts for natal and all annual/sub-period charts.

Testable with fixture data — no ephemeris required.
"""
from __future__ import annotations

import copy
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dateutil.relativedelta import relativedelta

from astroq.lk_prediction.constants import (
    PLANET_EXALTATION, PLANET_DEBILITATION, FIXED_HOUSE_LORDS
)

logger = logging.getLogger(__name__)

# Authentic 120-Year Lal Kitab Varshphal Movement Matrix (1952 Edition)
# Extracted from ChartGenerator so it can be referenced and tested independently.
YEAR_MATRIX: Dict[int, Dict[int, int]] = {
    1: {1:1,2:9,3:10,4:3,5:5,6:2,7:11,8:7,9:6,10:12,11:4,12:8},
    2: {1:4,2:1,3:12,4:9,5:3,6:7,7:5,8:6,9:2,10:8,11:10,12:11},
    3: {1:9,2:4,3:1,4:2,5:8,6:3,7:10,8:5,9:7,10:11,11:12,12:6},
    4: {1:3,2:8,3:4,4:1,5:10,6:9,7:6,8:11,9:5,10:7,11:2,12:12},
    5: {1:11,2:3,3:8,4:4,5:1,6:5,7:9,8:2,9:12,10:6,11:7,12:10},
    6: {1:5,2:12,3:3,4:8,5:4,6:11,7:2,8:9,9:1,10:10,11:6,12:7},
    7: {1:7,2:6,3:9,4:5,5:12,6:4,7:1,8:10,9:11,10:2,11:8,12:3},
    8: {1:2,2:7,3:6,4:12,5:9,6:10,7:3,8:1,9:8,10:5,11:11,12:4},
    9: {1:12,2:2,3:7,4:6,5:11,6:1,7:8,8:4,9:10,10:3,11:5,12:9},
    10: {1:10,2:11,3:2,4:7,5:6,6:12,7:4,8:8,9:3,10:1,11:9,12:5},
    11: {1:8,2:5,3:11,4:10,5:7,6:6,7:12,8:3,9:9,10:4,11:1,12:2},
    12: {1:6,2:10,3:5,4:11,5:2,6:8,7:7,8:12,9:4,10:9,11:3,12:1},
    13: {1:1,2:5,3:10,4:8,5:11,6:6,7:7,8:2,9:12,10:3,11:9,12:4},
    14: {1:4,2:1,3:3,4:2,5:5,6:7,7:8,8:11,9:6,10:12,11:10,12:9},
    15: {1:9,2:4,3:1,4:6,5:8,6:5,7:2,8:7,9:11,10:10,11:12,12:3},
    16: {1:3,2:9,3:4,4:1,5:12,6:8,7:6,8:5,9:2,10:7,11:11,12:10},
    17: {1:11,2:3,3:9,4:4,5:1,6:10,7:5,8:6,9:7,10:8,11:2,12:12},
    18: {1:5,2:11,3:6,4:9,5:4,6:1,7:12,8:8,9:10,10:2,11:3,12:7},
    19: {1:7,2:10,3:11,4:3,5:9,6:4,7:1,8:12,9:8,10:5,11:6,12:2},
    20: {1:2,2:7,3:5,4:12,5:3,6:9,7:10,8:1,9:4,10:6,11:8,12:11},
    21: {1:12,2:2,3:8,4:5,5:10,6:3,7:9,8:4,9:1,10:11,11:7,12:6},
    22: {1:10,2:12,3:2,4:7,5:6,6:11,7:3,8:9,9:5,10:1,11:4,12:8},
    23: {1:8,2:6,3:12,4:10,5:7,6:2,7:11,8:3,9:9,10:4,11:1,12:5},
    24: {1:6,2:8,3:7,4:11,5:2,6:12,7:4,8:10,9:3,10:9,11:5,12:1},
    25: {1:1,2:6,3:10,4:3,5:2,6:8,7:7,8:4,9:11,10:5,11:12,12:9},
    26: {1:4,2:1,3:3,4:8,5:6,6:7,7:2,8:11,9:12,10:9,11:5,12:10},
    27: {1:9,2:4,3:1,4:5,5:10,6:11,7:12,8:7,9:6,10:8,11:2,12:3},
    28: {1:3,2:9,3:4,4:1,5:11,6:5,7:6,8:8,9:7,10:2,11:10,12:12},
    29: {1:11,2:3,3:9,4:4,5:1,6:6,7:8,8:2,9:10,10:12,11:7,12:5},
    30: {1:5,2:11,3:8,4:9,5:4,6:1,7:3,8:12,9:2,10:10,11:6,12:7},
    31: {1:7,2:5,3:11,4:12,5:9,6:4,7:1,8:10,9:8,10:6,11:3,12:2},
    32: {1:2,2:7,3:5,4:11,5:3,6:12,7:10,8:6,9:4,10:1,11:9,12:8},
    33: {1:12,2:2,3:6,4:10,5:8,6:3,7:9,8:1,9:5,10:7,11:4,12:11},
    34: {1:10,2:12,3:2,4:7,5:5,6:9,7:11,8:3,9:1,10:4,11:8,12:6},
    35: {1:8,2:10,3:12,4:6,5:7,6:2,7:4,8:5,9:9,10:3,11:11,12:1},
    36: {1:6,2:8,3:7,4:2,5:12,6:10,7:5,8:9,9:3,10:11,11:1,12:4},
    37: {1:1,2:3,3:10,4:6,5:9,6:12,7:7,8:5,9:11,10:2,11:4,12:8},
    38: {1:4,2:1,3:3,4:8,5:6,6:5,7:2,8:7,9:12,10:10,11:11,12:9},
    39: {1:9,2:4,3:1,4:12,5:8,6:2,7:10,8:11,9:6,10:3,11:5,12:7},
    40: {1:3,2:9,3:4,4:1,5:11,6:8,7:6,8:12,9:2,10:5,11:7,12:10},
    41: {1:11,2:7,3:9,4:4,5:1,6:6,7:8,8:2,9:10,10:12,11:3,12:5},
    42: {1:5,2:11,3:8,4:9,5:12,6:1,7:3,8:4,9:7,10:6,11:10,12:2},
    43: {1:7,2:5,3:11,4:2,5:3,6:4,7:1,8:10,9:8,10:9,11:12,12:6},
    44: {1:2,2:10,3:5,4:3,5:4,6:9,7:12,8:8,9:1,10:7,11:6,12:11},
    45: {1:12,2:2,3:6,4:5,5:10,6:7,7:9,8:1,9:3,10:11,11:8,12:4},
    46: {1:10,2:12,3:2,4:7,5:5,6:3,7:11,8:6,9:4,10:8,11:9,12:1},
    47: {1:8,2:6,3:12,4:10,5:7,6:11,7:4,8:9,9:5,10:1,11:2,12:3},
    48: {1:6,2:8,3:7,4:11,5:2,6:10,7:5,8:3,9:9,10:4,11:1,12:12},
    49: {1:1,2:7,3:10,4:6,5:12,6:2,7:8,8:4,9:11,10:9,11:3,12:5},
    50: {1:4,2:1,3:8,4:3,5:6,6:12,7:5,8:11,9:2,10:7,11:10,12:9},
    51: {1:9,2:4,3:1,4:2,5:8,6:3,7:12,8:6,9:7,10:10,11:5,12:11},
    52: {1:3,2:9,3:4,4:1,5:11,6:7,7:2,8:12,9:5,10:8,11:6,12:10},
    53: {1:11,2:10,3:7,4:4,5:1,6:6,7:3,8:9,9:12,10:5,11:8,12:2},
    54: {1:5,2:11,3:3,4:9,5:4,6:1,7:6,8:2,9:10,10:12,11:7,12:8},
    55: {1:7,2:5,3:11,4:8,5:3,6:9,7:1,8:10,9:6,10:4,11:2,12:12},
    56: {1:2,2:3,3:5,4:11,5:9,6:4,7:10,8:1,9:8,10:6,11:12,12:7},
    57: {1:12,2:2,3:6,4:5,5:10,6:8,7:9,8:7,9:4,10:11,11:1,12:3},
    58: {1:10,2:12,3:2,4:7,5:5,6:11,7:4,8:8,9:3,10:1,11:9,12:6},
    59: {1:8,2:6,3:12,4:10,5:7,6:5,7:11,8:3,9:9,10:2,11:4,12:1},
    60: {1:6,2:8,3:9,4:12,5:2,6:10,7:7,8:5,9:1,10:3,11:11,12:4},
    61: {1:1,2:11,3:10,4:6,5:12,6:2,7:4,8:7,9:8,10:9,11:5,12:3},
    62: {1:4,2:1,3:6,4:8,5:3,6:12,7:2,8:10,9:9,10:5,11:7,12:11},
    63: {1:9,2:4,3:1,4:2,5:8,6:6,7:12,8:11,9:7,10:3,11:10,12:5},
    64: {1:3,2:9,3:4,4:1,5:6,6:8,7:7,8:12,9:5,10:2,11:11,12:10},
    65: {1:11,2:2,3:9,4:4,5:1,6:5,7:8,8:3,9:10,10:12,11:6,12:7},
    66: {1:5,2:10,3:3,4:9,5:2,6:1,7:6,8:8,9:11,10:7,11:12,12:4},
    67: {1:7,2:5,3:11,4:3,5:10,6:4,7:1,8:9,9:12,10:6,11:8,12:2},
    68: {1:2,2:3,3:5,4:11,5:9,6:7,7:10,8:1,9:6,10:8,11:4,12:12},
    69: {1:12,2:8,3:7,4:5,5:11,6:3,7:9,8:4,9:1,10:10,11:2,12:6},
    70: {1:10,2:12,3:2,4:7,5:5,6:11,7:3,8:6,9:4,10:1,11:9,12:8},
    71: {1:8,2:6,3:12,4:10,5:7,6:9,7:11,8:5,9:2,10:4,11:3,12:1},
    72: {1:6,2:7,3:8,4:12,5:4,6:10,7:5,8:2,9:3,10:11,11:1,12:9},
    73: {1:1,2:4,3:10,4:6,5:12,6:11,7:7,8:8,9:2,10:5,11:9,12:3},
    74: {1:4,2:2,3:3,4:8,5:6,6:12,7:1,8:11,9:7,10:10,11:5,12:9},
    75: {1:9,2:10,3:1,4:3,5:8,6:6,7:2,8:7,9:5,10:4,11:12,12:11},
}

STANDARD_PLANETS = frozenset([
    "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"
])

MONTHLY_RULERS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus",
                  "Saturn", "Rahu", "Ketu", "Sun", "Moon", "Mars"]


class ChartTransformer:
    """
    Pure ChartData transformation engine — zero flatlib dependency.

    Responsibilities:
    - detect_planet_states(planet, house) → List[str]
    - build_natal_chart_data(planet_house_map, birth_datetime_str, chart_system) → ChartData
    - generate_annual_charts(natal_chart, max_years) → Dict[str, ChartData]
    - generate_monthly_chart(annual_chart, month_number) → ChartData
    - generate_daily_chart(monthly_chart, days_elapsed) → ChartData
    - generate_hourly_chart(daily_chart, hour) → ChartData

    All methods are stateless — they take ChartData dicts and return ChartData dicts.
    """

    @staticmethod
    def detect_planet_states(planet: str, house: int) -> List[str]:
        """Detect Lal Kitab planetary states from house placement."""
        states = []
        if planet in PLANET_EXALTATION and house in PLANET_EXALTATION[planet]:
            states.append("Exalted")
        if planet in PLANET_DEBILITATION and house in PLANET_DEBILITATION[planet]:
            states.append("Debilitated")
        if house in FIXED_HOUSE_LORDS and planet in FIXED_HOUSE_LORDS[house]:
            states.append("Fixed House Lord")
        return states

    @staticmethod
    def build_natal_chart_data(
        planet_house_map: Dict[str, int],
        birth_datetime_str: str = "",
        chart_system: str = "vedic",
    ) -> Dict[str, Any]:
        """
        Build a ChartData dict from a raw planet→house mapping.

        Parameters
        ----------
        planet_house_map : {planet_name: house_number}
            Raw positions from any source (VedicHoroscopeData, fixture, DB).
        birth_datetime_str : ISO-format datetime string.
        chart_system : 'vedic' | 'kp'
        """
        planets_in_houses: Dict[str, Any] = {}
        for planet, house in planet_house_map.items():
            if planet not in STANDARD_PLANETS:
                continue
            planets_in_houses[planet] = {
                "house": house,
                "house_natal": house,
                "states": ChartTransformer.detect_planet_states(planet, house),
            }
        return {
            "chart_type": "Birth",
            "chart_period": 0,
            "chart_system": chart_system,
            "birth_time": birth_datetime_str,
            "planets_in_houses": planets_in_houses,
        }

    @staticmethod
    def generate_annual_charts(
        natal_chart: Dict[str, Any],
        max_years: int = 75,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Generate all Varshphal annual charts from a natal chart using YEAR_MATRIX.
        Returns {'chart_1': ChartData, ..., 'chart_N': ChartData}.
        """
        annual_charts: Dict[str, Dict[str, Any]] = {}
        birth_datetime_str = natal_chart.get("birth_time", "")

        try:
            birth_datetime: Optional[datetime] = (
                datetime.fromisoformat(birth_datetime_str.replace("Z", "+00:00"))
                if birth_datetime_str else None
            )
        except ValueError:
            birth_datetime = None

        for age in range(1, max_years + 1):
            mapping = YEAR_MATRIX.get(age, {})
            annual = natal_chart.copy()
            annual["chart_type"] = "Yearly"
            annual["chart_period"] = age

            annual_planets: Dict[str, Any] = {}
            for p, p_data in natal_chart.get("planets_in_houses", {}).items():
                p_copy = p_data.copy()
                if p == "Asc":
                    p_copy["house"] = 1
                else:
                    natal_h = p_copy.get("house_natal", p_copy.get("house", 0))
                    if natal_h in mapping:
                        p_copy["house"] = int(mapping[natal_h])
                    p_copy["states"] = ChartTransformer.detect_planet_states(p, p_copy["house"])
                annual_planets[p] = p_copy

            annual["planets_in_houses"] = annual_planets

            if birth_datetime:
                period_start = birth_datetime + relativedelta(years=age - 1)
                period_end = birth_datetime + relativedelta(years=age)
                annual["period_start"] = period_start.date().isoformat()
                annual["period_end"] = (period_end - timedelta(days=1)).date().isoformat()
                annual["birth_time"] = period_start.isoformat()

            annual_charts[f"chart_{age}"] = annual

        return annual_charts

    @staticmethod
    def _apply_planet_logic(
        parent_chart: Dict[str, Any],
        offset: int,
        mode: str,
        chart_type: str,
        chart_label: str,
    ) -> Dict[str, Any]:
        """Rotation ('rotate') or progression ('progress') transform."""
        child = copy.deepcopy(parent_chart)
        child["chart_type"] = chart_type
        child["chart_label"] = chart_label

        new_planets: Dict[str, Any] = {}
        for planet, p_data in parent_chart.get("planets_in_houses", {}).items():
            p_copy = p_data.copy()
            if planet == "Asc":
                p_copy["house"] = 1
            else:
                old_house = p_data.get("house", 1)
                if mode == "rotate":
                    p_copy["house"] = ((old_house - 1 - offset) % 12) + 1
                else:
                    p_copy["house"] = ((old_house - 1 + offset) % 12) + 1
                p_copy["states"] = ChartTransformer.detect_planet_states(planet, p_copy["house"])
            new_planets[planet] = p_copy

        child["planets_in_houses"] = new_planets
        return child

    @classmethod
    def generate_monthly_chart(cls, annual_chart: Dict[str, Any], month_number: int = 1) -> Dict[str, Any]:
        """Derive Monthly chart from Annual chart (Goswami 1952 rotation)."""
        ruler_idx = (month_number - 1) % len(MONTHLY_RULERS)
        month_ruler = MONTHLY_RULERS[ruler_idx]
        ruler_house = annual_chart.get("planets_in_houses", {}).get(month_ruler, {}).get("house", 1)
        child = cls._apply_planet_logic(annual_chart, ruler_house - 1, "rotate", "Monthly", f"Month {month_number}")
        child["chart_period_month"] = month_number
        child["chart_period"] = annual_chart.get("chart_period", 0)
        child["monthly_ruler"] = month_ruler
        return child

    @classmethod
    def generate_daily_chart(cls, monthly_chart: Dict[str, Any], days_elapsed: int) -> Dict[str, Any]:
        """Derive Daily chart from Monthly chart (Mars progression)."""
        mars_house = monthly_chart.get("planets_in_houses", {}).get("Mars", {}).get("house", 1)
        shift = (mars_house - 1 + max(0, days_elapsed - 1)) % 12
        child = cls._apply_planet_logic(monthly_chart, shift, "rotate", "Daily", f"Day {days_elapsed}")
        child["chart_period_day"] = days_elapsed
        child["chart_period"] = monthly_chart.get("chart_period", 0)
        return child

    @classmethod
    def generate_hourly_chart(cls, daily_chart: Dict[str, Any], hour: int) -> Dict[str, Any]:
        """Derive Hourly chart from Daily chart (Jupiter hour-progression)."""
        shift = max(0, hour - 1)
        child = cls._apply_planet_logic(daily_chart, shift, "progress", "Hourly", f"Hour {hour}")
        child["chart_period_hour"] = hour
        child["chart_period"] = daily_chart.get("chart_period", 0)
        return child
