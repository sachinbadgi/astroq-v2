"""
Module 0: Chart Generator

Orchestrates ephemeris I/O (flatlib/VedicHoroscopeData) and delegates all
pure transformation logic to ChartTransformer.

Responsibility split:
  ChartGenerator   — flatlib/ephemeris I/O seam (DOB+TOB+POB → planet-house map)
  ChartTransformer — pure transformation (planet-house map → ChartData for all periods)

New code that needs chart transformation without ephemeris should import
ChartTransformer directly:
    from astroq.lk_prediction.chart_transformer import ChartTransformer
"""
import logging
from typing import Dict, Any, List, Optional

from astroq.lk_prediction.constants import (
    PLANET_EXALTATION, PLANET_DEBILITATION, FIXED_HOUSE_LORDS
)
from astroq.lk_prediction.location_provider import NominatimLocationProvider
from astroq.lk_prediction.chart_transformer import ChartTransformer, YEAR_MATRIX, STANDARD_PLANETS
import dateutil.parser

try:
    import pytz
except ImportError:
    pass

logger = logging.getLogger("astroq.lk_prediction.chart_generator")

# Runtime Patch for flatlib 0.3.x compatibility & Swiss Ephemeris fixes
try:
    import flatlib.const as flat_const
    import flatlib.ephem.swe as swe
    import swisseph

    _ay_vals = {
        'AY_LAHIRI': 1, 'AY_RAMAN': 3, 'AY_KRISHNAMURTI': 5,
        'AY_LAHIRI_1940': 43, 'AY_LAHIRI_VP285': 44, 'AY_LAHIRI_ICRC': 45,
        'AY_KRISHNAMURTI_SENTHILATHIBAN': 57
    }
    for k, v in _ay_vals.items():
        if not hasattr(flat_const, k):
            setattr(flat_const, k, v)

    def patched_sweObject(obj, jd):
        sweObj = swe.SWE_OBJECTS[obj]
        res, flg = swisseph.calc_ut(jd, sweObj)
        return {'id': obj, 'lon': res[0], 'lat': res[1], 'lonspeed': res[3], 'latspeed': res[4]}
    swe.sweObject = patched_sweObject

    def patched_sweObjectLon(obj, jd):
        sweObj = swe.SWE_OBJECTS[obj]
        res, flg = swisseph.calc_ut(jd, sweObj)
        return res[0]
    swe.sweObjectLon = patched_sweObjectLon

    swe.SWE_AYANAMSAS = {
        flat_const.AY_LAHIRI: 1, flat_const.AY_LAHIRI_1940: 43,
        flat_const.AY_LAHIRI_VP285: 44, flat_const.AY_LAHIRI_ICRC: 45,
        flat_const.AY_KRISHNAMURTI: 5, flat_const.AY_KRISHNAMURTI_SENTHILATHIBAN: 57,
        flat_const.AY_RAMAN: 3,
    }

    def get_ayanamsa(jd, mode):
        eph_mode = swe.SWE_AYANAMSAS.get(mode, 1)
        swisseph.set_sid_mode(eph_mode, 0, 0)
        res = swisseph.get_ayanamsa_ex_ut(jd, flags=2 | 65536)
        return res[1]
    swe.get_ayanamsa = get_ayanamsa

    def patched_sweFixedStar(star, jd):
        res, stnam, flg = swisseph.fixstar2_ut(star, jd)
        mag = swisseph.fixstar2_mag(star)
        return {'id': star, 'mag': mag, 'lon': res[0], 'lat': res[1]}
    swe.sweFixedStar = patched_sweFixedStar

except Exception as e:
    logger.warning(f"Failed to apply flatlib runtime patch: {e}")

try:
    from vedicastro.VedicAstro import VedicHoroscopeData
except ImportError:
    VedicHoroscopeData = None


class ChartGenerator:
    """
    Ephemeris I/O seam: translates DOB/TOB/POB → planet-house map via
    VedicHoroscopeData, then delegates all chart transformations to ChartTransformer.

    To generate charts without ephemeris (tests, simulation), use:
        ChartTransformer.build_natal_chart_data(planet_house_map, ...)
        ChartTransformer.generate_annual_charts(natal_chart, ...)
    """

    CHART_SYSTEMS = ["kp", "vedic"]

    # Re-exported for backward compatibility
    YEAR_MATRIX = YEAR_MATRIX

    def __init__(self, location_provider=None):
        self.location_provider = location_provider or NominatimLocationProvider()

    def _parse_date_time(self, dob_str: str, tob_str: str) -> dict:
        try:
            parsed_date = dateutil.parser.parse(dob_str)
            parsed_time = dateutil.parser.parse(tob_str)
        except Exception as exc:
            raise ValueError(
                f"Could not understand the date/time format. Use YYYY-MM-DD and HH:MM. Error: {exc}"
            )
        return {
            "year": parsed_date.year, "month": parsed_date.month,
            "day": parsed_date.day, "hour": parsed_time.hour,
            "minute": parsed_time.minute, "second": parsed_time.second,
        }

    def geocode_place(self, place_name: str,
                      user_agent: str = "astroq_research_geocoder_v1") -> List[Dict[str, Any]]:
        """Look up lat/lon and UTC offset — delegated to LocationProvider seam."""
        return self.location_provider.geocode_place(place_name, user_agent)

    def generate_chart(self, dob_str: str, tob_str: str, place_name: str,
                       latitude: float, longitude: float, utc_string: str,
                       chart_system: str = "kp") -> dict:
        """
        Translate DOB/TOB/POB → planet-house map via VedicHoroscopeData,
        then delegate ChartData construction to ChartTransformer.
        """
        if chart_system not in self.CHART_SYSTEMS:
            raise ValueError(f"Unknown chart system '{chart_system}'. Choose from: {self.CHART_SYSTEMS}")

        dt = self._parse_date_time(dob_str, tob_str)
        ayanamsa = "Lahiri" if chart_system == "vedic" else "Krishnamurti"
        house_system = "Whole Sign" if chart_system == "vedic" else "Placidus"

        calculator = VedicHoroscopeData(
            year=dt["year"], month=dt["month"], day=dt["day"],
            hour=dt["hour"], minute=dt["minute"], second=dt["second"],
            utc=utc_string, latitude=latitude, longitude=longitude,
            ayanamsa=ayanamsa, house_system=house_system,
        )

        chart = calculator.generate_chart()
        va_planets_raw = calculator.get_planets_data_from_chart(chart)

        planet_house_map: Dict[str, int] = {}
        for p_obj in va_planets_raw:
            planet_name = getattr(p_obj, "Object", "N/A")
            if planet_name in STANDARD_PLANETS:
                planet_house_map[planet_name] = getattr(p_obj, "HouseNr", 1)

        birth_datetime_str = (
            f"{dt['year']:04d}-{dt['month']:02d}-{dt['day']:02d}"
            f"T{dt['hour']:02d}:{dt['minute']:02d}:{dt['second']:02d}"
        )
        return ChartTransformer.build_natal_chart_data(planet_house_map, birth_datetime_str, chart_system)

    # ------------------------------------------------------------------
    # Delegation to ChartTransformer (pure transformation, no flatlib)
    # ------------------------------------------------------------------

    def generate_annual_charts(self, natal_chart: dict, max_years: int = 100) -> Dict[str, dict]:
        """Delegate to ChartTransformer."""
        return ChartTransformer.generate_annual_charts(natal_chart, max_years)

    def _detect_planet_states(self, planet: str, house: int) -> List[str]:
        """Backward-compat instance shim."""
        return ChartTransformer.detect_planet_states(planet, house)

    @staticmethod
    def _detect_states_static(planet: str, house: int) -> list:
        """Backward-compat static shim."""
        return ChartTransformer.detect_planet_states(planet, house)

    @staticmethod
    def _apply_planet_logic(parent_chart: dict, offset: int, mode: str,
                            chart_type: str, chart_label: str) -> dict:
        """Backward-compat static shim."""
        return ChartTransformer._apply_planet_logic(
            parent_chart, offset, mode, chart_type, chart_label
        )

    def generate_monthly_chart(self, annual_chart: dict, month_number: int = 1) -> dict:
        return ChartTransformer.generate_monthly_chart(annual_chart, month_number)

    def generate_daily_chart(self, monthly_chart: dict, days_elapsed: int) -> dict:
        return ChartTransformer.generate_daily_chart(monthly_chart, days_elapsed)

    def generate_hourly_chart(self, daily_chart: dict, hour: int) -> dict:
        return ChartTransformer.generate_hourly_chart(daily_chart, hour)

    def build_full_chart_payload(self, dob_str: str, tob_str: str, place_name: str,
                                 latitude: float = 0.0, longitude: float = 0.0,
                                 utc_string: str = "+05:30", chart_system: str = "kp",
                                 annual_basis: Optional[str] = None) -> Dict[str, dict]:
        """
        Geocode (if needed), generate natal chart via ephemeris,
        delegate annual chart generation to ChartTransformer.
        """
        if latitude is None or longitude is None or (latitude == 0.0 and longitude == 0.0):
            locations = self.geocode_place(place_name)
            if not locations:
                raise ValueError(f"Could not geocode {place_name} and lat/lon were not provided.")
            loc = locations[0]
            latitude = loc["latitude"]
            longitude = loc["longitude"]
            utc_string = loc["utc_offset"]

        natal_chart = self.generate_chart(dob_str, tob_str, place_name,
                                          latitude, longitude, utc_string, chart_system)

        if not annual_basis:
            annual_basis = chart_system

        if annual_basis == "vedic" and chart_system != "vedic":
            seed_chart = self.generate_chart(dob_str, tob_str, place_name,
                                             latitude, longitude, utc_string, "vedic")
        elif annual_basis == "kp" and chart_system != "kp":
            seed_chart = self.generate_chart(dob_str, tob_str, place_name,
                                             latitude, longitude, utc_string, "kp")
        else:
            seed_chart = natal_chart

        annual_charts = ChartTransformer.generate_annual_charts(seed_chart)

        payload = {"chart_0": natal_chart, "metadata": {
            "chart_system": chart_system, "annual_basis": annual_basis,
        }}
        payload.update(annual_charts)
        return payload
