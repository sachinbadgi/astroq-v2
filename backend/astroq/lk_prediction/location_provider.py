"""
GeoProvider
===========
Single source of truth for place-name → (latitude, longitude, utc_offset) resolution.

Replaces 16+ copies of GEO_MAP scattered across backend scripts.

Usage (drop-in for all scripts):
    from astroq.lk_prediction.location_provider import GeoProvider
    lat, lon, tz = GeoProvider.lookup("Allahabad, India")
    # Falls back to New Delhi if place not found.

The canonical table (KNOWN_PLACES) is the union of all prior copies, deduped and
corrected. Add new entries here once; all 16 callers benefit immediately.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Canonical place → (lat, lon, utc_offset) table
# This is the superset of every GEO_MAP definition previously scattered across
# backend/scripts/*.py and engine_runner.py.
# ---------------------------------------------------------------------------
_GeoEntry = Tuple[float, float, str]  # (lat, lon, utc_offset)

KNOWN_PLACES: Dict[str, _GeoEntry] = {
    "Allahabad, India":                        (25.4358,   81.8463,  "+05:30"),
    "Mumbai, India":                           (19.0760,   72.8777,  "+05:30"),
    "Vadnagar, India":                         (23.7801,   72.6373,  "+05:30"),
    "San Francisco, California, US":           (37.7749, -122.4194,  "-08:00"),
    "Seattle, Washington, US":                 (47.6062, -122.3321,  "-08:00"),
    "Sandringham, Norfolk, UK":                (52.8311,    0.5054,  "+00:00"),
    "New Delhi, India":                        (28.6139,   77.2090,  "+05:30"),
    "Gary, Indiana, US":                       (41.5934,  -87.3464,  "-06:00"),
    "Pretoria, South Africa":                  (-25.7479,  28.2293,  "+02:00"),
    "Porbandar, India":                        (21.6417,   69.6293,  "+05:30"),
    "Jamaica Hospital, Queens, New York, US":  (40.7028,  -73.8152,  "-05:00"),
    "Honolulu, Hawaii, US":                    (21.3069, -157.8583,  "-10:00"),
    "Mayfair, London, UK":                     (51.5100,   -0.1458,  "+00:00"),
    "Skopje, North Macedonia":                 (42.0003,   21.4280,  "+01:00"),
    "Scranton, Pennsylvania, US":              (41.4090,  -75.6624,  "-05:00"),
    "Buckingham Palace, London, UK":           (51.5014,   -0.1419,  "+00:00"),
    "St. Petersburg, Russia":                  (59.9311,   30.3609,  "+03:00"),
    "Hodgenville, KY, USA":                    (37.5737,  -85.7411,  "-06:00"),
    "Mvezo, South Africa":                     (-31.9329,  28.9988,  "+02:00"),
    "Aden, Yemen":                             (12.7855,   45.0187,  "+03:00"),
    "Indore, India":                           (22.7196,   75.8577,  "+05:30"),
    "Jamshedpur, India":                       (22.8046,   86.2029,  "+05:30"),
    "Raisen, India":                           (23.3314,   77.7886,  "+05:30"),
    "Madanapalle, India":                      (13.5510,   78.5051,  "+05:30"),
    "Ranchi, India":                           (23.3441,   85.3096,  "+05:30"),
    # Aliases for typo variants found in some scripts
    "Pretoria, South South Africa":            (-25.7479,  28.2293,  "+02:00"),
}

_DEFAULT: _GeoEntry = (28.6139, 77.2090, "+05:30")  # New Delhi


class GeoProvider:
    """
    Deep module: resolves a place name to geographic coordinates.

    Interface (3 public entry-points):
        GeoProvider.lookup(place)          → (lat, lon, utc_offset) or default
        GeoProvider.lookup_or_raise(place) → (lat, lon, utc_offset) or KeyError
        GeoProvider.all_places()           → list[str] of known place names
    """

    # Expose the raw dict so callers that need dict-iteration keep working.
    # Prefer GeoProvider.lookup() for all new code.
    MAP: Dict[str, _GeoEntry] = KNOWN_PLACES

    @classmethod
    def lookup(cls, place: str, default: Optional[_GeoEntry] = None) -> _GeoEntry:
        """
        Case-insensitive, partial-match resolution.
        Returns *default* (New Delhi) if not found; never raises.
        """
        result = cls._match(place)
        if result is not None:
            return result
        fallback = default if default is not None else _DEFAULT
        logger.warning("GeoProvider: unknown place '%s' — using default %s", place, fallback)
        return fallback

    @classmethod
    def lookup_or_raise(cls, place: str) -> _GeoEntry:
        """Raises KeyError if the place is not in KNOWN_PLACES. Use for strict validation."""
        result = cls._match(place)
        if result is None:
            raise KeyError(f"GeoProvider: no entry for '{place}'")
        return result

    @classmethod
    def all_places(cls) -> List[str]:
        """Returns the sorted list of all known place names."""
        return sorted(cls.MAP.keys())

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    @classmethod
    def _match(cls, place: str) -> Optional[_GeoEntry]:
        """Exact match first; then bidirectional substring match (case-insensitive)."""
        # 1. Exact match
        if place in cls.MAP:
            return cls.MAP[place]

        # 2. Case-insensitive exact
        pl = place.lower()
        for key, val in cls.MAP.items():
            if key.lower() == pl:
                return val

        # 3. Bidirectional substring (mirrors old engine_runner._get_geo logic)
        for key, val in cls.MAP.items():
            kl = key.lower()
            if kl in pl or pl in kl:
                return val

        return None


# ---------------------------------------------------------------------------
# Backward-compat shim: plain dict that scripts can use as `GEO_MAP`
# ---------------------------------------------------------------------------
# Old usage in scripts:
#   GEO_MAP = { ... }
#   lat, lon, tz = GEO_MAP.get(place, DEFAULT_GEO)
#
# New drop-in:
#   from astroq.lk_prediction.location_provider import GEO_MAP, DEFAULT_GEO
#   lat, lon, tz = GEO_MAP.get(place, DEFAULT_GEO)
#
# This preserves every existing script without requiring a line-by-line edit.
GEO_MAP = KNOWN_PLACES
DEFAULT_GEO: _GeoEntry = _DEFAULT


# ---------------------------------------------------------------------------
# Online fallback (Nominatim) — unchanged from prior implementation
# ---------------------------------------------------------------------------

class LocationProvider:
    """Interface for resolving place names into coordinates and timezones via network."""
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
        import datetime
        import pytz
        tz_name = tf.timezone_at(lat=loc.latitude, lng=loc.longitude)
        if tz_name:
            tz = pytz.timezone(tz_name)
            utc_offset = datetime.datetime.now(tz).strftime("%z")
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
