"""
Module 0: Chart Generator

Provides the foundation for the Lal Kitab Prediction Pipeline by:
1. Translating DOB/TOB/POB and geographical coordinates into an astronomical chart using `vedicastro`.
2. Extracting KP or Vedic planet/house mappings.
3. Generating the Natal Chart in `ChartData` format.
4. Generating all 75 Varshaphal (Annual) charts dynamically using Lal Kitab progression rules.

This eliminates the need for external pipeline dependency when generating the raw inputs for prediction.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
import dateutil.parser

try:
    from geopy.geocoders import Nominatim
    from timezonefinder import TimezoneFinder
    import pytz
except ImportError:
    pass  # Allow tests to run even if missing, unless called

try:
    from vedicastro.VedicAstro import VedicHoroscopeData
except ImportError:
    pass

logger = logging.getLogger("astroq.lk_prediction.chart_generator")


class ChartGenerator:
    """
    Generates ChartData dicts suitable for the LKPredictionPipeline.
    """

    CHART_SYSTEMS = ["kp", "vedic"]
    
    # 12-Year Varshaphal Rotation Table (maps Natal House -> Annual House based on Cycle Year)
    VAR_MAP = {
        1:  {1: 1, 2: 9, 3: 10, 4: 3, 5: 5, 6: 2, 7: 11, 8: 7, 9: 6, 10: 12, 11: 4, 12: 8},
        2:  {1: 4, 2: 1, 3: 12, 4: 9, 5: 3, 6: 7, 7: 5, 8: 6, 9: 2, 10: 8, 11: 10, 12: 11},
        3:  {1: 9, 2: 4, 3:  1, 4: 2, 5: 8, 6: 3, 7: 10, 8: 5, 9: 7, 10: 11, 11: 12, 12:  6},
        4:  {1: 3, 2: 8, 3:  4, 4: 1, 5: 10, 6: 9, 7:  6, 8: 11, 9: 5, 10:  7, 11:  2, 12: 12},
        5:  {1: 11, 2: 3, 3:  8, 4: 4, 5:  1, 6: 5, 7:  9, 8:  2, 9: 12, 10:  6, 11:  7, 12: 10},
        6:  {1: 5, 2: 12, 3:  3, 4: 8, 5:  4, 6: 11, 7:  2, 8:  9, 9:  1, 10: 10, 11:  6, 12:  7},
        7:  {1: 7, 2: 6, 3:  9, 4: 5, 5: 12, 6: 4, 7:  1, 8: 10, 9: 11, 10:  2, 11:  8, 12:  3},
        8:  {1: 2, 2: 7, 3:  6, 4: 12, 5: 9, 6: 10, 7:  3, 8:  1, 9:  8, 10:  5, 11: 11, 12:  4},
        9:  {1: 12, 2: 2, 3:  7, 4: 6, 5: 11, 6: 1, 7:  8, 8:  4, 9: 10, 10:  3, 11:  5, 12:  9},
        10: {1: 10, 2: 11, 3:  2, 4: 7, 5:  6, 6: 12, 7:  4, 8:  8, 9:  3, 10:  1, 11:  9, 12:  5},
        11: {1: 8, 2: 5, 3: 11, 4: 10, 5:  7, 6:  6, 7: 12, 8:  3, 9:  9, 10:  4, 11:  1, 12:  2},
        12: {1: 6, 2: 10, 3:  5, 4: 11, 5:  2, 6:  8, 7:  7, 8: 12, 9:  4, 10:  9, 11:  3, 12:  1}
    }

    def _parse_date_time(self, dob_str: str, tob_str: str) -> dict:
        try:
            parsed_date = dateutil.parser.parse(dob_str, dayfirst=True)
            parsed_time = dateutil.parser.parse(tob_str)
        except Exception as exc:
            raise ValueError(f"Could not understand the date/time format. Use YYYY-MM-DD and HH:MM. Error: {exc}")

        return {
            "year": parsed_date.year,
            "month": parsed_date.month,
            "day": parsed_date.day,
            "hour": parsed_time.hour,
            "minute": parsed_time.minute,
            "second": parsed_time.second
        }

    def geocode_place(self, place_name: str) -> List[Dict[str, Any]]:
        """Look up lat/lon and UTC offset from a place name string."""
        if not place_name or not place_name.strip():
            return []
            
        geolocator = Nominatim(user_agent="lk_predictor_geocoder", timeout=10)
        tf = TimezoneFinder()

        try:
            results = geolocator.geocode(place_name, exactly_one=False, limit=1)
        except Exception as e:
            logger.warning("Geocoding failed for '%s': %s", place_name, e)
            return []

        if not results:
            return []
            
        loc = results[0]
        tz_name = tf.timezone_at(lat=loc.latitude, lng=loc.longitude)
        if tz_name:
            tz = pytz.timezone(tz_name)
            utc_offset = datetime.now(tz).strftime("%z")
            utc_offset = f"{utc_offset[:3]}:{utc_offset[3:]}"
        else:
            utc_offset = "+00:00"
            tz_name = "UTC"

        return [{
            "display_name": loc.address,
            "latitude": round(loc.latitude, 6),
            "longitude": round(loc.longitude, 6),
            "utc_offset": utc_offset,
            "timezone": tz_name,
        }]

    def generate_chart(self, dob_str: str, tob_str: str, place_name: str, 
                       latitude: float, longitude: float, utc_string: str, 
                       chart_system: str = "kp") -> dict:
        """
        Generate astronomical chart and convert to 'ChartData' Base Contract format.
        """
        if chart_system not in self.CHART_SYSTEMS:
            raise ValueError(f"Unknown chart system '{chart_system}'. Choose from: {self.CHART_SYSTEMS}")

        dt = self._parse_date_time(dob_str, tob_str)
        ayanamsa = "Krishnamurti" if chart_system == "kp" else "Lahiri"
        house_system = "Placidus" if chart_system == "kp" else "Whole Sign"

        calculator = VedicHoroscopeData(
            year=dt["year"], month=dt["month"], day=dt["day"],
            hour=dt["hour"], minute=dt["minute"], second=dt["second"],
            utc=utc_string, latitude=latitude, longitude=longitude,
            ayanamsa=ayanamsa, house_system=house_system,
        )

        chart = calculator.generate_chart()
        va_planets_raw = calculator.get_planets_data_from_chart(chart)
        
        # Standard LK planets mapping
        standard_planets = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
        planets_in_houses = {}
        
        for p_obj in va_planets_raw:
            planet_name = getattr(p_obj, "Object", "N/A")
            if planet_name in standard_planets:
                house = getattr(p_obj, "HouseNr", 0)
                planets_in_houses[planet_name] = {
                    "house": house,
                    "house_natal": house,  # Store natal house strictly for Varshaphal base mapping
                }

        birth_datetime_str = f"{dt['year']:04d}-{dt['month']:02d}-{dt['day']:02d}T{dt['hour']:02d}:{dt['minute']:02d}:{dt['second']:02d}"

        # Build ChartData dict contract
        return {
            "chart_type": "Birth",
            "chart_period": 0,
            "birth_time": birth_datetime_str,
            "planets_in_houses": planets_in_houses
        }

    def generate_annual_charts(self, natal_chart: dict, max_years: int = 75) -> Dict[str, dict]:
        """
        Iterate over max_years and construct Varshaphal charts from the natal chart
        according to the 12-year mapping cycle.
        """
        annual_charts = {}
        birth_datetime_str = natal_chart.get("birth_time", "")
        
        try:
            birth_datetime = datetime.fromisoformat(birth_datetime_str.replace('Z', '+00:00')) if birth_datetime_str else None
        except ValueError:
            birth_datetime = None

        for age in range(1, max_years + 1):
            annual = natal_chart.copy()
            annual["chart_type"] = "Yearly"
            annual["chart_period"] = age
            
            # Deep copy planets to apply new house placements without clobbering Natal
            annual_planets = {}
            cycle_yr = ((age - 1) % 12) + 1
            mapping = self.VAR_MAP.get(cycle_yr, {})
            
            for p, p_data in natal_chart.get("planets_in_houses", {}).items():
                p_copy = p_data.copy()
                natal_h = p_copy.get("house_natal", p_copy.get("house", 0))
                
                # Apply Varshaphal shifting if valid house
                if natal_h in mapping:
                    p_copy["house"] = mapping[natal_h]
                    
                annual_planets[p] = p_copy
                
            annual["planets_in_houses"] = annual_planets
            
            if birth_datetime:
                annual["birth_time"] = (birth_datetime + timedelta(days=age * 365.25)).isoformat()
            
            annual_charts[f"chart_{age}"] = annual
            
        return annual_charts

    def build_full_chart_payload(self, dob_str: str, tob_str: str, place_name: str,
                                 latitude: float = 0.0, longitude: float = 0.0,
                                 utc_string: str = "+05:30", chart_system: str = "kp") -> Dict[str, dict]:
        """
        Wraps geocoding iff lat/lon are not provided, generates Natal, and all 75 Annual charts.
        """
        if latitude == 0.0 or longitude == 0.0:
            locations = self.geocode_place(place_name)
            if not locations:
                raise ValueError(f"Could not geocode {place_name} and lat/lon were not provided.")
            loc = locations[0]
            latitude = loc["latitude"]
            longitude = loc["longitude"]
            utc_string = loc["utc_offset"]
            
        natal_chart = self.generate_chart(dob_str, tob_str, place_name, latitude, longitude, utc_string, chart_system)
        annual_charts = self.generate_annual_charts(natal_chart)
        
        payload = {"chart_0": natal_chart}
        payload.update(annual_charts)
        
        return payload
