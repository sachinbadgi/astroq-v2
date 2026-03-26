"""
Tests for MISSING/PARTIAL Grammar Features (Section 14 of lk_prediction_model_v2.md).

These tests were written FIRST (TDD Red phase) — they describe the complete, correct
logic from the reference codebase that was missing or wrong in the new implementation.

Reference: D:\astroq-mar26\backend\astroq\
  - Mars_special_rules.py               → Mangal Badh 17-rule system
  - global_birth_yearly_strength_additional_checks.py → 16 disposition rules
  - global_birth_yearly_grammer_rules.py → BilMukabil 3-step, Sleeping aspect-map
"""

import pytest


# ---------------------------------------------------------------------------
# Helpers (shared with main test file)
# ---------------------------------------------------------------------------

def _make_enriched_planet(house, strength_total=5.0):
    return {
        "house": house,
        "raw_aspect_strength": strength_total,
        "dignity_score": 0.0,
        "scapegoat_adjustment": 0.0,
        "strength_total": strength_total,
        "strength_breakdown": {
            "aspects": strength_total,
            "dignity": 0.0,
            "scapegoat": 0.0,
        },
    }


def _make_minimal_chart(planets_dict):
    return {
        "chart_type": "Birth",
        "chart_period": 0,
        "planets_in_houses": planets_dict,
        "house_status": {},
    }


def _make_analyser(tmp_defaults, tmp_db):
    from astroq.lk_prediction.config import ModelConfig
    from astroq.lk_prediction.grammar_analyser import GrammarAnalyser
    cfg = ModelConfig(db_path=tmp_db, defaults_path=tmp_defaults)
    return GrammarAnalyser(cfg)


# ---------------------------------------------------------------------------
# 1. Complete Mangal Badh — 17-Rule System
# ---------------------------------------------------------------------------

class TestMangalBadhComplete:
    """All increment and decrement rules for the Mangal Badh counter."""

    def test_r1_sun_saturn_conjunct_increments(self, tmp_defaults, tmp_db):
        """R1: Sun and Saturn in same house → +1 counter."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        chart = _make_minimal_chart({
            "Sun": {"house": 4}, "Saturn": {"house": 4}, "Mars": {"house": 7},
            "Moon": {"house": 11}, "Mercury": {"house": 3}, "Venus": {"house": 2},
            "Jupiter": {"house": 9}, "Rahu": {"house": 2}, "Ketu": {"house": 8},
        })
        counter = analyser.detect_mangal_badh(chart)
        assert counter >= 1, f"R1 (Sun+Saturn conjunct) must increment counter, got {counter}"

    def test_r5_mars_mercury_conjunct_increments(self, tmp_defaults, tmp_db):
        """R5: Mars+Mercury conjunct → +1 counter."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        chart = _make_minimal_chart({
            "Mars": {"house": 5}, "Mercury": {"house": 5},
            "Sun": {"house": 1}, "Moon": {"house": 4},
            "Venus": {"house": 6}, "Saturn": {"house": 10}, "Rahu": {"house": 12},
            "Ketu": {"house": 6}, "Jupiter": {"house": 11},
        })
        counter = analyser.detect_mangal_badh(chart)
        assert counter >= 1, f"R5 (Mars+Mercury conjunct) must increment counter, got {counter}"

    def test_r5_mars_ketu_conjunct_increments(self, tmp_defaults, tmp_db):
        """R5: Mars+Ketu conjunct → +1 counter."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        chart = _make_minimal_chart({
            "Mars": {"house": 2}, "Ketu": {"house": 2},
            "Sun": {"house": 1}, "Moon": {"house": 4},
            "Mercury": {"house": 7}, "Venus": {"house": 6},
            "Saturn": {"house": 10}, "Rahu": {"house": 8}, "Jupiter": {"house": 11},
        })
        counter = analyser.detect_mangal_badh(chart)
        assert counter >= 1, f"R5 (Mars+Ketu conjunct) must increment counter, got {counter}"

    def test_r6_ketu_in_h1_increments(self, tmp_defaults, tmp_db):
        """R6: Ketu in H1 → +1 counter."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        chart = _make_minimal_chart({
            "Ketu": {"house": 1}, "Mars": {"house": 3},
            "Sun": {"house": 2}, "Moon": {"house": 4},
            "Mercury": {"house": 7}, "Venus": {"house": 6},
            "Saturn": {"house": 10}, "Rahu": {"house": 7}, "Jupiter": {"house": 11},
        })
        counter = analyser.detect_mangal_badh(chart)
        assert counter >= 1, f"R6 (Ketu in H1) must increment counter, got {counter}"

    def test_r7_ketu_in_h8_increments(self, tmp_defaults, tmp_db):
        """R7: Ketu in H8 → +1 counter."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        chart = _make_minimal_chart({
            "Ketu": {"house": 8}, "Mars": {"house": 3},
            "Sun": {"house": 2}, "Moon": {"house": 4},
            "Mercury": {"house": 7}, "Venus": {"house": 6},
            "Saturn": {"house": 10}, "Rahu": {"house": 12}, "Jupiter": {"house": 11},
        })
        counter = analyser.detect_mangal_badh(chart)
        assert counter >= 1, f"R7 (Ketu in H8) must increment counter, got {counter}"

    def test_r8_mars_in_h3_increments(self, tmp_defaults, tmp_db):
        """R8: Mars in H3 → +1 counter."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        chart = _make_minimal_chart({
            "Mars": {"house": 3},
            "Sun": {"house": 1}, "Moon": {"house": 4}, "Mercury": {"house": 7},
            "Venus": {"house": 2}, "Saturn": {"house": 10}, "Rahu": {"house": 12},
            "Ketu": {"house": 6}, "Jupiter": {"house": 11},
        })
        counter = analyser.detect_mangal_badh(chart)
        assert counter >= 1, f"R8 (Mars in H3) must increment counter, got {counter}"

    def test_r9_venus_in_h9_increments(self, tmp_defaults, tmp_db):
        """R9: Venus in H9 → +1 counter."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        chart = _make_minimal_chart({
            "Venus": {"house": 9}, "Mars": {"house": 1},
            "Sun": {"house": 2}, "Moon": {"house": 4},
            "Mercury": {"house": 7}, "Saturn": {"house": 10}, "Rahu": {"house": 12},
            "Ketu": {"house": 6}, "Jupiter": {"house": 11},
        })
        counter = analyser.detect_mangal_badh(chart)
        assert counter >= 1, f"R9 (Venus in H9) must increment counter, got {counter}"

    def test_r10_sun_in_h6_increments(self, tmp_defaults, tmp_db):
        """R10: Sun in H6 → +1 counter."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        chart = _make_minimal_chart({
            "Sun": {"house": 6}, "Mars": {"house": 1},
            "Moon": {"house": 4}, "Mercury": {"house": 3},
            "Venus": {"house": 2}, "Saturn": {"house": 8}, "Rahu": {"house": 11},
            "Ketu": {"house": 5}, "Jupiter": {"house": 9},
        })
        counter = analyser.detect_mangal_badh(chart)
        assert counter >= 1, f"R10 (Sun in H6) must increment counter, got {counter}"

    def test_r11_mars_in_h6_increments(self, tmp_defaults, tmp_db):
        """R11: Mars in H6 → +1 counter."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        chart = _make_minimal_chart({
            "Mars": {"house": 6},
            "Sun": {"house": 1}, "Moon": {"house": 4}, "Mercury": {"house": 7},
            "Venus": {"house": 2}, "Saturn": {"house": 10}, "Rahu": {"house": 12},
            "Ketu": {"house": 6}, "Jupiter": {"house": 11},
        })
        counter = analyser.detect_mangal_badh(chart)
        assert counter >= 1, f"R11 (Mars in H6) must increment counter, got {counter}"

    def test_r12_mercury_in_h1_h3_h8_increments(self, tmp_defaults, tmp_db):
        """R12: Mercury in H1/H3/H8 → +1 counter each."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        for merc_h in [1, 3, 8]:
            chart = _make_minimal_chart({
                "Mercury": {"house": merc_h}, "Mars": {"house": 5},
                "Sun": {"house": 4}, "Moon": {"house": 4},
                "Venus": {"house": 2}, "Saturn": {"house": 10}, "Rahu": {"house": 12},
                "Ketu": {"house": 6}, "Jupiter": {"house": 11},
            })
            counter = analyser.detect_mangal_badh(chart)
            assert counter >= 1, f"R12 (Mercury in H{merc_h}) must increment counter, got {counter}"

    def test_r13_rahu_in_h5_increments(self, tmp_defaults, tmp_db):
        """R13: Rahu in H5 → +1 counter."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        chart = _make_minimal_chart({
            "Rahu": {"house": 5}, "Mars": {"house": 1},
            "Sun": {"house": 2}, "Moon": {"house": 4}, "Mercury": {"house": 7},
            "Venus": {"house": 6}, "Saturn": {"house": 10}, "Ketu": {"house": 11},
            "Jupiter": {"house": 3},
        })
        counter = analyser.detect_mangal_badh(chart)
        assert counter >= 1, f"R13 (Rahu in H5) must increment counter, got {counter}"

    def test_d1_sun_mercury_conjunct_decrements(self, tmp_defaults, tmp_db):
        """D1: Sun+Mercury conjunct → -1 counter."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        # All benign positions with one adding rule, then D1 reduces it
        chart_with_d1 = _make_minimal_chart({
            "Sun": {"house": 5}, "Mercury": {"house": 5}, "Mars": {"house": 1},
            "Moon": {"house": 4}, "Venus": {"house": 2}, "Saturn": {"house": 8},
            "Rahu": {"house": 3}, "Ketu": {"house": 9}, "Jupiter": {"house": 11},
        })
        chart_without_d1 = _make_minimal_chart({
            "Sun": {"house": 5}, "Mercury": {"house": 7}, "Mars": {"house": 1},
            "Moon": {"house": 4}, "Venus": {"house": 2}, "Saturn": {"house": 8},
            "Rahu": {"house": 3}, "Ketu": {"house": 9}, "Jupiter": {"house": 11},
        })
        c_with = analyser.detect_mangal_badh(chart_with_d1)
        c_without = analyser.detect_mangal_badh(chart_without_d1)
        assert c_with < c_without, \
            f"D1 (Sun+Mercury conjunct) must decrement: {c_with} should be < {c_without}"

    def test_d4_moon_in_good_houses_decrements(self, tmp_defaults, tmp_db):
        """D4: Moon in H1/H2/H3/H4/H8/H9 → -1 counter."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        for moon_h in [1, 2, 3, 4, 8, 9]:
            chart_with = _make_minimal_chart({
                "Moon": {"house": moon_h}, "Mars": {"house": 6},
                "Sun": {"house": 2}, "Mercury": {"house": 7},
                "Venus": {"house": 6}, "Saturn": {"house": 10}, "Rahu": {"house": 12},
                "Ketu": {"house": 6}, "Jupiter": {"house": 11},
            })
            chart_without = _make_minimal_chart({
                "Moon": {"house": 5}, "Mars": {"house": 6},
                "Sun": {"house": 2}, "Mercury": {"house": 7},
                "Venus": {"house": 6}, "Saturn": {"house": 10}, "Rahu": {"house": 12},
                "Ketu": {"house": 6}, "Jupiter": {"house": 11},
            })
            c_with = analyser.detect_mangal_badh(chart_with)
            c_without = analyser.detect_mangal_badh(chart_without)
            assert c_with < c_without, \
                f"D4 (Moon in H{moon_h}) should decrement: {c_with} should be < {c_without}"

    def test_mangal_badh_strength_formula_uses_divisor_16(self, tmp_defaults, tmp_db):
        """Mangal Badh formula: mars_new = mars_old - mars_old * (1 + counter/16.0)."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        # Create a chart with Mars in H3 (R8 fires → counter >= 1)
        chart = _make_minimal_chart({
            "Mars": {"house": 3}, "Sun": {"house": 1}, "Moon": {"house": 4},
            "Mercury": {"house": 7}, "Venus": {"house": 2}, "Saturn": {"house": 10},
            "Rahu": {"house": 12}, "Ketu": {"house": 6}, "Jupiter": {"house": 11},
        })
        counter = analyser.detect_mangal_badh(chart)
        assert counter >= 1, "Need at least 1 counter for this test"

        enriched = {"Mars": _make_enriched_planet(3, 10.0)}
        chart["mangal_badh_status"] = "Active"
        chart["mangal_badh_count"] = counter
        analyser.apply_grammar_rules(chart, enriched)

        # Formula: mars_new = 10.0 - 10.0 * (1 + counter/16.0)
        expected_reduction = 10.0 * (1.0 + counter / 16.0)
        expected_new = 10.0 - expected_reduction
        actual = enriched["Mars"]["strength_total"]
        assert abs(actual - expected_new) < 0.1, \
            f"Expected Mars={expected_new:.2f} (with divisor 16), got {actual:.2f}"


# ---------------------------------------------------------------------------
# 2. Complete Disposition Rules — 16 Rules
# ---------------------------------------------------------------------------

class TestDispositionRulesComplete:
    """All 16 Lal Kitab planet disposition rules from reference codebase."""

    def test_jupiter_h7_spoils_venus(self, tmp_defaults, tmp_db):
        """DISP_JUP7_VENUS_BAD: Jupiter in H7 reduces Venus strength."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        enriched = {
            "Jupiter": _make_enriched_planet(7, 8.0),
            "Venus":   _make_enriched_planet(2, 5.0),
        }
        chart = _make_minimal_chart({"Jupiter": {"house": 7}, "Venus": {"house": 2}})
        venus_before = 5.0
        analyser.apply_grammar_rules(chart, enriched)
        assert enriched["Venus"]["strength_total"] < venus_before, \
            "Jupiter in H7 must reduce Venus strength"

    def test_rahu_h11_spoils_jupiter(self, tmp_defaults, tmp_db):
        """DISP_RAHU_H11_JUP_BAD: Rahu in H11 reduces Jupiter strength."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        enriched = {
            "Rahu":    _make_enriched_planet(11, 4.0),
            "Jupiter": _make_enriched_planet(2, 6.0),
        }
        chart = _make_minimal_chart({"Rahu": {"house": 11}, "Jupiter": {"house": 2}})
        jup_before = 6.0
        analyser.apply_grammar_rules(chart, enriched)
        assert enriched["Jupiter"]["strength_total"] < jup_before, \
            "Rahu in H11 must reduce Jupiter strength"

    def test_rahu_h12_spoils_jupiter(self, tmp_defaults, tmp_db):
        """DISP_RAHU_H12_JUP_BAD: Rahu in H12 reduces Jupiter strength."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        enriched = {
            "Rahu":    _make_enriched_planet(12, 3.0),
            "Jupiter": _make_enriched_planet(2, 6.0),
        }
        chart = _make_minimal_chart({"Rahu": {"house": 12}, "Jupiter": {"house": 2}})
        jup_before = 6.0
        analyser.apply_grammar_rules(chart, enriched)
        assert enriched["Jupiter"]["strength_total"] < jup_before, \
            "Rahu in H12 must reduce Jupiter strength"

    def test_sun_h6_spoils_saturn(self, tmp_defaults, tmp_db):
        """DISP_SUN_H6_SATURN_BAD: Sun in H6 reduces Saturn strength."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        enriched = {
            "Sun":    _make_enriched_planet(6, 5.0),
            "Saturn": _make_enriched_planet(10, 7.0),
        }
        chart = _make_minimal_chart({"Sun": {"house": 6}, "Saturn": {"house": 10}})
        sat_before = 7.0
        analyser.apply_grammar_rules(chart, enriched)
        assert enriched["Saturn"]["strength_total"] < sat_before, \
            "Sun in H6 must reduce Saturn strength"

    def test_sun_h10_spoils_mars_and_ketu(self, tmp_defaults, tmp_db):
        """DISP_SUN_H10_MARS_KETU_BAD: Sun in H10 reduces both Mars and Ketu."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        enriched = {
            "Sun":  _make_enriched_planet(10, 6.0),
            "Mars": _make_enriched_planet(3, 4.0),
            "Ketu": _make_enriched_planet(6, 3.0),
        }
        chart = _make_minimal_chart({
            "Sun": {"house": 10}, "Mars": {"house": 3}, "Ketu": {"house": 6}
        })
        mars_before = 4.0
        ketu_before = 3.0
        analyser.apply_grammar_rules(chart, enriched)
        assert enriched["Mars"]["strength_total"] < mars_before, \
            "Sun in H10 must reduce Mars strength"
        assert enriched["Ketu"]["strength_total"] < ketu_before, \
            "Sun in H10 must reduce Ketu strength"

    def test_sun_h11_spoils_mars(self, tmp_defaults, tmp_db):
        """DISP_SUN_H11_MARS_BAD: Sun in H11 reduces Mars strength."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        enriched = {
            "Sun":  _make_enriched_planet(11, 4.0),
            "Mars": _make_enriched_planet(3, 5.0),
        }
        chart = _make_minimal_chart({"Sun": {"house": 11}, "Mars": {"house": 3}})
        mars_before = 5.0
        analyser.apply_grammar_rules(chart, enriched)
        assert enriched["Mars"]["strength_total"] < mars_before, \
            "Sun in H11 must reduce Mars strength"

    def test_moon_h1_helps_mars(self, tmp_defaults, tmp_db):
        """DISP_MOON_H1_H3_H8_MARS_GOOD: Moon in H1/H3/H8 boosts Mars via disposition."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        for moon_h in [1, 3, 8]:
            enriched = {
                "Moon": _make_enriched_planet(moon_h, 5.0),
                "Mars": _make_enriched_planet(6, 3.0),
            }
            chart = _make_minimal_chart({"Moon": {"house": moon_h}, "Mars": {"house": 6}})
            analyser.apply_grammar_rules(chart, enriched)
            # The disposition rule must contribute a positive value to Mars's breakdown.
            # We check breakdown["disposition"] because Mangal Badh may also apply
            # in a minimal chart (R2/R3 fire when Sun/Moon don't aspect Mars).
            assert enriched["Mars"]["strength_breakdown"]["disposition"] > 0, \
                f"Moon in H{moon_h} should add positive disposition to Mars"


    def test_venus_h9_spoils_mars(self, tmp_defaults, tmp_db):
        """DISP_VENUS_H9_MARS_BAD: Venus in H9 reduces Mars strength."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        enriched = {
            "Venus": _make_enriched_planet(9, 4.0),
            "Mars":  _make_enriched_planet(1, 5.0),
        }
        chart = _make_minimal_chart({"Venus": {"house": 9}, "Mars": {"house": 1}})
        mars_before = 5.0
        analyser.apply_grammar_rules(chart, enriched)
        assert enriched["Mars"]["strength_total"] < mars_before, \
            "Venus in H9 must reduce Mars strength"

    def test_venus_h2_h5_h12_spoils_jupiter(self, tmp_defaults, tmp_db):
        """DISP_VENUS_H2_H5_H12_JUP_BAD: Venus in H2/H5/H12 reduces Jupiter."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        for venus_h in [2, 5, 12]:
            enriched = {
                "Venus":   _make_enriched_planet(venus_h, 4.0),
                "Jupiter": _make_enriched_planet(11, 6.0),
            }
            chart = _make_minimal_chart({"Venus": {"house": venus_h}, "Jupiter": {"house": 11}})
            jup_before = 6.0
            analyser.apply_grammar_rules(chart, enriched)
            assert enriched["Jupiter"]["strength_total"] < jup_before, \
                f"Venus in H{venus_h} should reduce Jupiter"

    def test_mercury_h3_h6_h8_h12_spoils_moon(self, tmp_defaults, tmp_db):
        """DISP_MERCURY_H3_H6_H8_H12_MOON_BAD: Mercury in these houses spoils Moon."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        for merc_h in [3, 6, 8, 12]:
            enriched = {
                "Mercury": _make_enriched_planet(merc_h, 4.0),
                "Moon":    _make_enriched_planet(4, 6.0),
            }
            chart = _make_minimal_chart({"Mercury": {"house": merc_h}, "Moon": {"house": 4}})
            moon_before = 6.0
            analyser.apply_grammar_rules(chart, enriched)
            assert enriched["Moon"]["strength_total"] < moon_before, \
                f"Mercury in H{merc_h} should reduce Moon"

    def test_mercury_h2_h5_h9_spoils_jupiter(self, tmp_defaults, tmp_db):
        """DISP_MERCURY_H2_H5_H9_JUP_BAD: Mercury in H2/H5/H9 reduces Jupiter."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        for merc_h in [2, 5, 9]:
            enriched = {
                "Mercury": _make_enriched_planet(merc_h, 4.0),
                "Jupiter": _make_enriched_planet(11, 6.0),
            }
            chart = _make_minimal_chart({"Mercury": {"house": merc_h}, "Jupiter": {"house": 11}})
            jup_before = 6.0
            analyser.apply_grammar_rules(chart, enriched)
            assert enriched["Jupiter"]["strength_total"] < jup_before, \
                f"Mercury in H{merc_h} should reduce Jupiter"

    def test_saturn_h4_h6_h10_spoils_moon(self, tmp_defaults, tmp_db):
        """DISP_SATURN_H4_H6_H10_MOON_BAD: Saturn in H4/H6/H10 reduces Moon."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        for sat_h in [4, 6, 10]:
            enriched = {
                "Saturn": _make_enriched_planet(sat_h, 4.0),
                "Moon":   _make_enriched_planet(1, 6.0),
            }
            chart = _make_minimal_chart({"Saturn": {"house": sat_h}, "Moon": {"house": 1}})
            moon_before = 6.0
            analyser.apply_grammar_rules(chart, enriched)
            assert enriched["Moon"]["strength_total"] < moon_before, \
                f"Saturn in H{sat_h} should reduce Moon"

    def test_rahu_h2_h5_h6_h9_spoils_jupiter(self, tmp_defaults, tmp_db):
        """DISP_RAHU_H2_H5_H6_H9_JUP_BAD: Rahu in H2/H5/H6/H9 reduces Jupiter."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        for rahu_h in [2, 5, 6, 9]:
            enriched = {
                "Rahu":    _make_enriched_planet(rahu_h, 4.0),
                "Jupiter": _make_enriched_planet(3, 6.0),
            }
            chart = _make_minimal_chart({"Rahu": {"house": rahu_h}, "Jupiter": {"house": 3}})
            jup_before = 6.0
            analyser.apply_grammar_rules(chart, enriched)
            assert enriched["Jupiter"]["strength_total"] < jup_before, \
                f"Rahu in H{rahu_h} should reduce Jupiter"

    def test_ketu_h11_h12_spoils_jupiter(self, tmp_defaults, tmp_db):
        """DISP_KETU_H11_H12_JUP_BAD: Ketu in H11/H12 reduces Jupiter."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        for ketu_h in [11, 12]:
            enriched = {
                "Ketu":    _make_enriched_planet(ketu_h, 3.0),
                "Jupiter": _make_enriched_planet(2, 6.0),
            }
            chart = _make_minimal_chart({"Ketu": {"house": ketu_h}, "Jupiter": {"house": 2}})
            jup_before = 6.0
            analyser.apply_grammar_rules(chart, enriched)
            assert enriched["Jupiter"]["strength_total"] < jup_before, \
                f"Ketu in H{ketu_h} should reduce Jupiter"

    def test_ketu_h11_h12_spoils_mars_and_helps_venus(self, tmp_defaults, tmp_db):
        """DISP_KETU_H11_H12_MARS_BAD_VENUS_GOOD: Ketu H11/H12 → Mars Bad, Venus Good."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        for ketu_h in [11, 12]:
            enriched = {
                "Ketu":  _make_enriched_planet(ketu_h, 3.0),
                "Mars":  _make_enriched_planet(3, 5.0),
                "Venus": _make_enriched_planet(6, 4.0),
            }
            chart = _make_minimal_chart({
                "Ketu": {"house": ketu_h}, "Mars": {"house": 3}, "Venus": {"house": 6}
            })
            mars_before, venus_before = 5.0, 4.0
            analyser.apply_grammar_rules(chart, enriched)
            # Check disposition breakdown is positive for Venus (Good rule)
            # and mars final is less than before (Bad rule overwhelms any other effect)
            assert enriched["Mars"]["strength_total"] < mars_before, \
                f"Ketu in H{ketu_h} should reduce Mars"
            # Venus boost: disposition breakdown must show positive Venus contribution
            assert enriched["Venus"]["strength_breakdown"]["disposition"] > 0, \
                f"Ketu in H{ketu_h} should add positive disposition to Venus"


    def test_moon_h6_spoils_mars_and_helps_venus(self, tmp_defaults, tmp_db):
        """DISP_MOON_H6_MARS_BAD_VENUS_GOOD: Moon H6 → Mars Bad, Venus Good."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        enriched = {
            "Moon":  _make_enriched_planet(6, 4.0),
            "Mars":  _make_enriched_planet(3, 5.0),
            "Venus": _make_enriched_planet(7, 3.0),
        }
        chart = _make_minimal_chart({
            "Moon": {"house": 6}, "Mars": {"house": 3}, "Venus": {"house": 7}
        })
        mars_before, venus_before = 5.0, 3.0
        analyser.apply_grammar_rules(chart, enriched)
        assert enriched["Mars"]["strength_total"] < mars_before, \
            "Moon in H6 should reduce Mars"
        assert enriched["Venus"]["strength_total"] > venus_before, \
            "Moon in H6 should boost Venus"


# ---------------------------------------------------------------------------
# 3. BilMukabil — Correct 3-Step Logic
# ---------------------------------------------------------------------------

class TestBilMukabilCorrectLogic:
    """BilMukabil requires: natural friends + significant aspect + enemy in foundational house."""

    def test_bilmukabil_fails_if_not_natural_friends(self, tmp_defaults, tmp_db):
        """Non-friends (Sun and Saturn) with 100% enemy aspects → NOT BilMukabil."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        # Sun and Saturn are natural enemies (not friends)
        chart = {"planets_in_houses": {
            "Sun":    {"house": 1, "aspects": [{"aspecting_planet": "Saturn", "aspect_type": "100 Percent", "relationship": "enemy"}]},
            "Saturn": {"house": 7, "aspects": [{"aspecting_planet": "Sun", "aspect_type": "100 Percent", "relationship": "enemy"}]},
        }}
        result = analyser.detect_bilmukabil("Sun", "Saturn", chart["planets_in_houses"])
        assert result is False, "Sun and Saturn are not natural friends → cannot be BilMukabil"

    def test_bilmukabil_fails_without_significant_aspect(self, tmp_defaults, tmp_db):
        """Natural friends (Jupiter+Sun) without significant aspect → NOT BilMukabil."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        # Jupiter and Sun are natural friends but only have 'Foundation' aspect (not 100/50/25%)
        chart = {"planets_in_houses": {
            "Jupiter": {"house": 2, "aspects": [{"aspecting_planet": "Sun", "aspect_type": "Foundation", "relationship": "friend"}]},
            "Sun":     {"house": 9, "aspects": [{"aspecting_planet": "Jupiter", "aspect_type": "Foundation", "relationship": "friend"}]},
        }}
        result = analyser.detect_bilmukabil("Jupiter", "Sun", chart["planets_in_houses"])
        assert result is False, "Without significant aspect, no BilMukabil"

    def test_bilmukabil_fails_without_enemy_in_foundational_house(self, tmp_defaults, tmp_db):
        """Natural friends with 50% aspect but no enemy in foundational house → NOT BilMukabil."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        # Jupiter (H4) and Sun (H10) are friends with 100% aspect
        # Foundational of Jupiter: [2,5,9,11,12]; Foundational of Sun: [1,5]
        # Put Venus (enemy of Jupiter) in H3 — not in foundational of Sun
        # Put Rahu (enemy of Sun) in H6 — not in foundational of Jupiter
        chart = {"planets_in_houses": {
            "Jupiter": {"house": 4, "aspects": [{"aspecting_planet": "Sun", "aspect_type": "100 Percent", "relationship": "friend"}]},
            "Sun":     {"house": 10, "aspects": [{"aspecting_planet": "Jupiter", "aspect_type": "100 Percent", "relationship": "friend"}]},
            "Venus":   {"house": 3, "aspects": []},    # enemy of Jupiter, not in Sun foundational
            "Rahu":    {"house": 6, "aspects": []},    # enemy of Sun, not in Jupiter foundational
        }}
        result = analyser.detect_bilmukabil("Jupiter", "Sun", chart["planets_in_houses"])
        assert result is False, "No enemy in foundational house → not BilMukabil"

    def test_bilmukabil_true_all_three_conditions_met(self, tmp_defaults, tmp_db):
        """All 3 conditions: friends + 100% aspect + enemy in foundational house → BilMukabil."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        # Jupiter(H4) and Sun(H10): natural friends; H4↔H10 is 100% aspect
        # Saturn (enemy of Sun) in H2 = foundational house of Jupiter → triggers!
        chart = {"planets_in_houses": {
            "Jupiter": {"house": 4, "aspects": [{"aspecting_planet": "Sun", "aspect_type": "100 Percent", "relationship": "friend"}]},
            "Sun":     {"house": 10, "aspects": [{"aspecting_planet": "Jupiter", "aspect_type": "100 Percent", "relationship": "friend"}]},
            "Saturn":  {"house": 2, "aspects": []},   # enemy of Sun; H2 is foundational of Jupiter
        }}
        result = analyser.detect_bilmukabil("Jupiter", "Sun", chart["planets_in_houses"])
        assert result is True, "All 3 BilMukabil conditions met → should return True"

    def test_bilmukabil_50_percent_aspect_is_significant(self, tmp_defaults, tmp_db):
        """50% aspects also qualify as significant for BilMukabil (not just 100%)."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        # Mars(H3) and Jupiter(H9): Mars aspects H9 via 50%; they are natural friends
        # Mercury (enemy of Jupiter, enemy of Mars) in H12 = foundational of Jupiter
        chart = {"planets_in_houses": {
            "Mars":    {"house": 3, "aspects": [{"aspecting_planet": "Jupiter", "aspect_type": "50 Percent", "relationship": "friend"}]},
            "Jupiter": {"house": 9, "aspects": [{"aspecting_planet": "Mars", "aspect_type": "50 Percent", "relationship": "friend"}]},
            "Mercury": {"house": 12, "aspects": []},  # enemy of Mars; H12 is in Jupiter foundational
        }}
        result = analyser.detect_bilmukabil("Mars", "Jupiter", chart["planets_in_houses"])
        assert result is True, "50% aspect with enemy in foundational → BilMukabil"


# ---------------------------------------------------------------------------
# 4. Sleeping Planet — Canonical Aspect-Map Detection
# ---------------------------------------------------------------------------

class TestSleepingPlanetAspectMap:
    """Sleeping detection must use HOUSE_ASPECT_MAP, not just check len(aspects)>0."""

    def test_planet_in_h2_aspects_h6_if_occupied_is_awake(self, tmp_defaults, tmp_db):
        """Moon (H2) aspects H6 via HOUSE_ASPECT_MAP; if H6 occupied → Awake."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        # Moon pakka ghar = H4; Moon in H2 aspects H6
        # Saturn is in H6 → Moon aspects an occupied house → Awake
        chart = {"planets_in_houses": {
            "Moon":   {"house": 2},
            "Saturn": {"house": 6},   # occupies H6
        }}
        result = analyser.detect_sleeping("Moon", chart["planets_in_houses"])
        assert result is False, "Moon in H2 with Saturn in H6 (aspected) → Awake"

    def test_planet_in_h2_with_empty_h6_is_sleeping(self, tmp_defaults, tmp_db):
        """Moon (H2) aspects H6; H6 is empty → Sleeping."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        chart = {"planets_in_houses": {
            "Moon": {"house": 2},
            "Sun":  {"house": 1},   # H6 is empty
        }}
        result = analyser.detect_sleeping("Moon", chart["planets_in_houses"])
        assert result is True, "Moon in H2 with empty H6 → Sleeping"

    def test_planet_in_h3_aspects_h9_and_h11_awake_if_either_occupied(self, tmp_defaults, tmp_db):
        """Mars (H3) aspects H9 and H11; if either occupied → Awake."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        # Mars pakka ghar = H3; Mars IS in H3 → never sleeping (pakka ghar check)
        # Use Saturn in H3 instead (pakka of Saturn is H10)
        chart = {"planets_in_houses": {
            "Saturn": {"house": 3},
            "Venus":  {"house": 9},  # H3 aspects H9 and H11; Venus in H9 → Awake
        }}
        result = analyser.detect_sleeping("Saturn", chart["planets_in_houses"])
        assert result is False, "Saturn in H3 with Venus in H9 (aspected) → Awake"

    def test_planet_in_h8_has_no_aspects_always_sleeping(self, tmp_defaults, tmp_db):
        """H8 aspects nothing (empty in HOUSE_ASPECT_MAP) → always sleeping if not in pakka ghar."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        # Mars pakka ghar = H3, not H8. 
        # House 8 in canonical map DOES aspect houses (2, 3, 4, 5, 12).
        # We empty those houses to ensure it sleeps.
        chart = {"planets_in_houses": {
            "Mars":  {"house": 8},
            "Sun":   {"house": 7}, # Not aspected by H8
        }}
        result = analyser.detect_sleeping("Mars", chart["planets_in_houses"])
        assert result is True, "Mars in H8 (with no occupied aspect targets) → Sleeping"

    def test_planet_in_pakka_ghar_never_sleeping(self, tmp_defaults, tmp_db):
        """Planet in its pakka ghar is never sleeping regardless of aspects."""
        analyser = _make_analyser(tmp_defaults, tmp_db)
        # Saturn pakka ghar = H10; Saturn in H10 → never sleeping
        chart = {"planets_in_houses": {
            "Saturn": {"house": 10},  # In its pakka ghar
        }}
        result = analyser.detect_sleeping("Saturn", chart["planets_in_houses"])
        assert result is False, "Saturn in H10 (pakka ghar) → never sleeping"
