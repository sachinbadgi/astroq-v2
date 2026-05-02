import logging
from typing import List, Dict, Any
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

class LocationProvider:
    """Interface for resolving place names into coordinates and timezones."""
    def geocode_place(self, place_name: str, user_agent: str = "astroq_research_geocoder_v1") -> List[Dict[str, Any]]:
        raise NotImplementedError

class NominatimLocationProvider(LocationProvider):
    """Concrete implementation using geopy and timezonefinder."""
    def geocode_place(self, place_name: str, user_agent: str = "astroq_research_geocoder_v1") -> List[Dict[str, Any]]:
        if not place_name or not place_name.strip():
            return []
            
        try:
            from geopy.geocoders import Nominatim
            from timezonefinder import TimezoneFinder
        except ImportError:
            logger.error("Required packages (geopy, timezonefinder) are missing.")
            return []

        geolocator = Nominatim(user_agent=user_agent, timeout=10)
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
