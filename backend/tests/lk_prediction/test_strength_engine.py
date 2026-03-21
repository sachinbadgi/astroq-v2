"""
Tests for Module 2: Strength Engine.

Tests written FIRST (TDD Red phase) — 10 unit tests.
"""

import copy
import pytest

# We import lazily inside tests so the module can be "RED" at first.

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_planet(house, states=None, aspects=None, strength_total=0.0):
    return {
        "house": house,
        "states": states or [],
        "aspects": aspects or [],
        "strength_total": strength_total,
        "sleeping_status": "",
        "dharmi_status": "",
    }


def _make_aspect(aspecting_planet, house, aspect_strength, aspect_type, relationship):
    return {
        "aspecting_planet": aspecting_planet,
        "house": house,
        "aspect_strength": aspect_strength,
        "aspect_type": aspect_type,
        "relationship": relationship,
    }


def _minimal_chart(planets_dict, chart_type="Birth", chart_period=0):
    return {
        "chart_type": chart_type,
        "chart_period": chart_period,
        "planets_in_houses": planets_dict,
        "mangal_badh_counter": 0,
        "mangal_badh_status": "",
        "dharmi_kundli_status": "Not Dharmi Teva",
        "house_status": {},
        "masnui_grahas_formed": [],
        "lal_kitab_debts": [],
        "achanak_chot_triggers": [],
        "dhoka_graha_analysis": [],
        "varshaphal_metadata": {},
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestStrengthEngine:

    def _make_config(self, tmp_defaults, tmp_db):
        from astroq.lk_prediction.config import ModelConfig
        return ModelConfig(db_path=tmp_db, defaults_path=tmp_defaults)

    def _make_engine(self, tmp_defaults, tmp_db):
        from astroq.lk_prediction.strength_engine import StrengthEngine
        cfg = self._make_config(tmp_defaults, tmp_db)
        return StrengthEngine(cfg)

    # -- Aspect tests --

    def test_aspect_strength_sun_h1_aspects_h7(self, tmp_defaults, tmp_db):
        """Sun in house 1 should create an aspect relationship to house 7."""
        engine = self._make_engine(tmp_defaults, tmp_db)

        # Sun in H1 aspects H7 (100 Percent aspect from HOUSE_ASPECT_DATA["1"]["100 Percent"] = 7)
        # Mercury is in H7, so Sun→Mercury aspect should exist
        planets = {
            "Sun": _make_planet(1),
            "Mercury": _make_planet(7),
        }
        chart = _minimal_chart(planets)
        enriched = engine.calculate_chart_strengths(chart)

        # Sun should have a non-zero aspect-based strength component
        assert enriched["Sun"]["raw_aspect_strength"] != 0.0

    def test_aspect_strength_friend_returns_positive(self, tmp_defaults, tmp_db):
        """Friendly aspect should contribute positive strength."""
        engine = self._make_engine(tmp_defaults, tmp_db)

        # Sun in H1, Jupiter in H7 (Sun-Jupiter are friends)
        # Sun aspects H7 via "100 Percent" and "General Condition"
        sun_aspects = [
            _make_aspect("Jupiter", 7, 0.666667, "Foundation", "friend"),
        ]
        planets = {
            "Sun": _make_planet(1, aspects=sun_aspects),
            "Jupiter": _make_planet(7),
        }
        chart = _minimal_chart(planets)
        enriched = engine.calculate_chart_strengths(chart)

        assert enriched["Sun"]["raw_aspect_strength"] > 0

    def test_aspect_strength_enemy_returns_negative(self, tmp_defaults, tmp_db):
        """Enemy confrontation aspect should contribute negative strength."""
        engine = self._make_engine(tmp_defaults, tmp_db)

        sun_aspects = [
            _make_aspect("Saturn", 7, 5.0, "Confrontation", "enemy"),
        ]
        planets = {
            "Sun": _make_planet(1, aspects=sun_aspects),
            "Saturn": _make_planet(7),
        }
        chart = _minimal_chart(planets)
        enriched = engine.calculate_chart_strengths(chart)

        assert enriched["Sun"]["raw_aspect_strength"] < 0

    # -- Dignity tests --

    def test_dignity_exalted_adds_weight(self, tmp_defaults, tmp_db):
        """Exalted planet should get a positive dignity score."""
        engine = self._make_engine(tmp_defaults, tmp_db)

        # Sun exalted in H1
        planets = {"Sun": _make_planet(1, states=["Exalted"])}
        chart = _minimal_chart(planets)
        enriched = engine.calculate_chart_strengths(chart)

        assert enriched["Sun"]["dignity_score"] > 0
        # Default exalted weight is 5.0
        assert enriched["Sun"]["dignity_score"] >= 5.0

    def test_dignity_debilitated_subtracts_weight(self, tmp_defaults, tmp_db):
        """Debilitated planet should get a negative dignity score."""
        engine = self._make_engine(tmp_defaults, tmp_db)

        # Sun debilitated in H7
        planets = {"Sun": _make_planet(7, states=["Debilitated"])}
        chart = _minimal_chart(planets)
        enriched = engine.calculate_chart_strengths(chart)

        assert enriched["Sun"]["dignity_score"] < 0

    def test_dignity_pakka_ghar_adds_weight(self, tmp_defaults, tmp_db):
        """Planet in its Pakka Ghar should get dignity boost."""
        engine = self._make_engine(tmp_defaults, tmp_db)

        # Sun's Pakka Ghar is H1
        planets = {"Sun": _make_planet(1)}
        chart = _minimal_chart(planets)
        enriched = engine.calculate_chart_strengths(chart)

        # Default pakka_ghar weight is 2.20
        assert enriched["Sun"]["dignity_score"] >= 2.2

    # -- Scapegoat test --

    def test_scapegoat_distributes_negative_to_targets(self, tmp_defaults, tmp_db):
        """Negative strength planet distributes pain to scapegoats."""
        engine = self._make_engine(tmp_defaults, tmp_db)

        # Saturn with negative strength → scapegoats are Rahu(0.5), Ketu(0.3), Venus(0.2)
        planets = {
            "Saturn": _make_planet(10, aspects=[
                _make_aspect("Sun", 1, 5.0, "Confrontation", "enemy"),
                _make_aspect("Mars", 4, 5.0, "Confrontation", "enemy"),
            ]),
            "Rahu": _make_planet(12),
            "Ketu": _make_planet(6),
            "Venus": _make_planet(7),
        }
        chart = _minimal_chart(planets)
        enriched = engine.calculate_chart_strengths(chart)

        # Saturn's negative strength should be redistributed — Saturn goes to 0
        assert enriched["Saturn"]["scapegoat_adjustment"] != 0 or enriched["Saturn"]["strength_total"] == 0.0
        # At least one scapegoat should have reduced strength
        scapegoat_hit = (
            enriched["Rahu"]["strength_total"] < 0
            or enriched["Ketu"]["strength_total"] < 0
            or enriched["Venus"]["strength_total"] < 0
        )
        assert scapegoat_hit

    # -- Natal-Annual merge test --

    def test_natal_annual_merge_is_additive(self, tmp_defaults, tmp_db):
        """Annual strengths should be added to natal strengths (not averaged)."""
        engine = self._make_engine(tmp_defaults, tmp_db)

        natal = {
            "Sun": {"house": 1, "strength_total": 5.0, "raw_aspect_strength": 3.0,
                    "dignity_score": 2.0, "scapegoat_adjustment": 0.0,
                    "strength_breakdown": {"aspects": 3.0, "dignity": 2.0, "scapegoat": 0.0}},
        }
        annual = {
            "Sun": {"house": 10, "strength_total": 3.0, "raw_aspect_strength": 2.0,
                    "dignity_score": 1.0, "scapegoat_adjustment": 0.0,
                    "strength_breakdown": {"aspects": 2.0, "dignity": 1.0, "scapegoat": 0.0}},
        }

        merged = engine.merge_natal_annual(natal, annual)
        # Additive: 5.0 + 3.0 = 8.0
        assert merged["Sun"]["strength_total"] == 8.0

    # -- Edge case tests --

    def test_empty_chart_returns_zero_strength(self, tmp_defaults, tmp_db):
        """Chart with no planets should return empty dict."""
        engine = self._make_engine(tmp_defaults, tmp_db)

        chart = _minimal_chart({})
        enriched = engine.calculate_chart_strengths(chart)
        assert enriched == {}

    def test_strength_breakdown_sums_to_total(self, tmp_defaults, tmp_db):
        """strength_breakdown components should sum to strength_total."""
        engine = self._make_engine(tmp_defaults, tmp_db)

        planets = {
            "Sun": _make_planet(1, states=["Exalted"], aspects=[
                _make_aspect("Jupiter", 9, 0.666667, "Foundation", "friend"),
            ]),
        }
        chart = _minimal_chart(planets)
        enriched = engine.calculate_chart_strengths(chart)

        sun = enriched["Sun"]
        breakdown = sun["strength_breakdown"]
        breakdown_sum = sum(breakdown.values())

        assert abs(breakdown_sum - sun["strength_total"]) < 0.001
