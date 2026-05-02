# backend/tests/lk_prediction/test_scapegoat_router.py
from astroq.lk_prediction.scapegoat_router import ScapegoatRouter

def test_saturn_hit_by_sun_routes_to_venus_and_rahu():
    router = ScapegoatRouter()
    assert "Venus" in router.get_scapegoats("Saturn")
    assert "Rahu" in router.get_scapegoats("Saturn")

def test_jupiter_routes_to_ketu():
    router = ScapegoatRouter()
    assert "Ketu" in router.get_scapegoats("Jupiter")

def test_planet_with_no_scapegoat_returns_empty():
    router = ScapegoatRouter()
    assert router.get_scapegoats("Moon") == []
