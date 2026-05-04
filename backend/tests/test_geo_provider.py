"""
Tests for GeoProvider — the canonical place-to-coordinate resolver.

Run: cd backend && python3 -m pytest tests/test_geo_provider.py -v
"""
import pytest
from astroq.lk_prediction.location_provider import GeoProvider, GEO_MAP, DEFAULT_GEO, KNOWN_PLACES


class TestGeoProviderLookup:

    def test_exact_match(self):
        lat, lon, tz = GeoProvider.lookup("Allahabad, India")
        assert (lat, lon, tz) == (25.4358, 81.8463, "+05:30")

    def test_case_insensitive(self):
        lat, lon, tz = GeoProvider.lookup("allahabad, india")
        assert lat == pytest.approx(25.4358)

    def test_partial_substring_match(self):
        # "Mumbai" should match "Mumbai, India"
        lat, lon, tz = GeoProvider.lookup("Mumbai")
        assert lat == pytest.approx(19.0760)

    def test_unknown_place_returns_default(self):
        result = GeoProvider.lookup("Atlantis, Fictional")
        assert result == DEFAULT_GEO

    def test_unknown_place_with_custom_default(self):
        custom = (0.0, 0.0, "+00:00")
        result = GeoProvider.lookup("Atlantis, Fictional", default=custom)
        assert result == custom

    def test_lookup_or_raise_known(self):
        lat, lon, tz = GeoProvider.lookup_or_raise("New Delhi, India")
        assert lat == pytest.approx(28.6139)

    def test_lookup_or_raise_unknown(self):
        with pytest.raises(KeyError, match="Atlantis"):
            GeoProvider.lookup_or_raise("Atlantis, Fictional")

    def test_all_places_returns_sorted_list(self):
        places = GeoProvider.all_places()
        assert isinstance(places, list)
        assert len(places) >= 20
        assert places == sorted(places)

    def test_typo_alias_pretoria(self):
        """The 'South South Africa' typo variant maps correctly."""
        lat, lon, tz = GeoProvider.lookup("Pretoria, South South Africa")
        assert lat == pytest.approx(-25.7479)

    def test_ranchi_is_present(self):
        """Ranchi was in some scripts but missing from engine_runner; now canonical."""
        lat, lon, tz = GeoProvider.lookup("Ranchi, India")
        assert lat == pytest.approx(23.3441)


class TestBackwardCompatShim:
    """Scripts that used GEO_MAP.get(place, DEFAULT_GEO) must still work."""

    def test_geo_map_is_dict(self):
        assert isinstance(GEO_MAP, dict)

    def test_geo_map_contains_allahabad(self):
        assert "Allahabad, India" in GEO_MAP

    def test_geo_map_get_with_default(self):
        result = GEO_MAP.get("Allahabad, India", DEFAULT_GEO)
        assert result == (25.4358, 81.8463, "+05:30")

    def test_default_geo_is_new_delhi(self):
        lat, lon, tz = DEFAULT_GEO
        assert lat == pytest.approx(28.6139)
        assert tz == "+05:30"

    def test_geo_map_get_unknown_returns_default(self):
        result = GEO_MAP.get("Atlantis", DEFAULT_GEO)
        assert result == DEFAULT_GEO


class TestNoDuplicatesInCanonicalTable:

    def test_all_coordinates_are_tuples_of_three(self):
        for place, entry in KNOWN_PLACES.items():
            assert len(entry) == 3, f"{place} has malformed entry: {entry}"
            lat, lon, tz = entry
            assert isinstance(lat, float)
            assert isinstance(lon, float)
            assert isinstance(tz, str) and ":" in tz

    def test_utc_offsets_are_valid_format(self):
        import re
        pattern = re.compile(r'^[+-]\d{2}:\d{2}$')
        for place, (lat, lon, tz) in KNOWN_PLACES.items():
            assert pattern.match(tz), f"{place} has invalid UTC offset: '{tz}'"
