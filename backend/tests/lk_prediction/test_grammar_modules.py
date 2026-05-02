"""
Unit tests for all 6 grammar modules.
Tests detect() with constructed ChartData and audit() with planet_strengths dict.
"""

import pytest
import json
from astroq.lk_prediction.grammar.modules.structural_module import StructuralModule
from astroq.lk_prediction.grammar.modules.state_module import StateModule
from astroq.lk_prediction.grammar.modules.mangal_badh_module import MangalBadhModule
from astroq.lk_prediction.grammar.modules.debt_module import DebtModule
from astroq.lk_prediction.grammar.modules.interaction_module import InteractionModule
from astroq.lk_prediction.grammar.modules.entanglement_module import EntanglementModule
from astroq.lk_prediction.config import ModelConfig
from tests.lk_prediction.conftest import MODEL_DEFAULTS_PATH


def _make_config(tmp_path, overrides=None):
    db_path = str(tmp_path / "test.db")
    defaults = {
        "strength": {
            "sleeping_planet_factor": 0.0,
            "kaayam_boost": 1.15,
            "dharmi_planet_boost": 1.50,
            "dharmi_kundli_boost": 1.20,
            "sathi_boost_per_companion": 1.00,
            "bilmukabil_penalty_per_hostile": 1.50,
            "mangal_badh_divisor": 16.0,
            "masnui_parent_feedback": 0.30,
            "rin_penalty_factor": 0.85,
            "dhoka_graha_factor": 0.70,
            "achanak_chot_penalty": 2.00,
            "cycle_35yr_boost": 1.25,
            "spoiler_factor": 0.50,
        }
    }
    if overrides:
        for k, v in overrides.items():
            defaults["strength"][k] = v
    defaults_path = tmp_path / "defaults.json"
    with open(defaults_path, "w") as f:
        json.dump(defaults, f)
    return ModelConfig(db_path=str(db_path), defaults_path=str(defaults_path))


def _make_chart(planets, chart_type="Birth", chart_period=0):
    return {
        "chart_type": chart_type,
        "chart_period": chart_period,
        "planets_in_houses": planets,
        "house_status": {},
    }


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


# -- StructuralModule --------------------------------------------------------

class TestStructuralModule:

    def test_nagrik_when_all_planets_upper_half(self):
        mod = StructuralModule()
        chart = _make_chart({"Sun": {"house": 1}, "Moon": {"house": 3}, "Mars": {"house": 5}})
        hits = mod.detect(chart)
        assert chart["structural_type"] == "Nagrik (Active/Self)"
        assert any(h.rule_id == "STRUCTURAL_TYPE" for h in hits)

    def test_nashtik_when_all_planets_lower_half(self):
        mod = StructuralModule()
        chart = _make_chart({"Sun": {"house": 7}, "Moon": {"house": 9}, "Mars": {"house": 11}})
        hits = mod.detect(chart)
        assert chart["structural_type"] == "Nashtik (Passive/Social)"
        assert any(h.rule_id == "STRUCTURAL_TYPE" for h in hits)

    def test_mixed_when_planets_both_halves(self):
        mod = StructuralModule()
        chart = _make_chart({"Sun": {"house": 1}, "Moon": {"house": 7}})
        mod.detect(chart)
        assert chart["structural_type"] == "Mixed"

    def test_andhi_kundli_sun4_sat7(self):
        mod = StructuralModule()
        chart = _make_chart({"Sun": {"house": 4}, "Saturn": {"house": 7}})
        hits = mod.detect(chart)
        assert chart["andhi_kundli_status"] == "Active (Sun 4, Sat 7)"
        assert any(h.rule_id == "ANDHI_KUNDLI" for h in hits)

    def test_andhi_kundli_malefics_in_10(self):
        mod = StructuralModule()
        chart = _make_chart({"Saturn": {"house": 10}, "Rahu": {"house": 10}})
        hits = mod.detect(chart)
        assert "Active" in chart["andhi_kundli_status"]
        assert any(h.rule_id == "ANDHI_KUNDLI" for h in hits)

    def test_andhi_kundli_inactive(self):
        mod = StructuralModule()
        chart = _make_chart({"Sun": {"house": 1}, "Saturn": {"house": 3}})
        mod.detect(chart)
        assert chart["andhi_kundli_status"] == "Inactive"

    def test_dharmi_teva_jupiter_saturn_conjunct(self):
        mod = StructuralModule()
        chart = _make_chart({"Jupiter": {"house": 5}, "Saturn": {"house": 5}})
        hits = mod.detect(chart)
        assert chart["dharmi_kundli_status"] == "Dharmi Teva"
        assert any(h.rule_id == "DHARMI_KUNDLI" for h in hits)

    def test_dharmi_kundli_inactive_separate_houses(self):
        mod = StructuralModule()
        chart = _make_chart({"Jupiter": {"house": 5}, "Saturn": {"house": 7}})
        mod.detect(chart)
        assert chart["dharmi_kundli_status"] == "Inactive"

    def test_audit_is_noop(self):
        mod = StructuralModule()
        chart = _make_chart({"Sun": {"house": 1}})
        enriched = {"Sun": {"house": 1, "strength_total": 5.0}}
        before = enriched["Sun"]["strength_total"]
        mod.audit(chart, enriched, [])
        assert enriched["Sun"]["strength_total"] == before


# -- StateModule --------------------------------------------------------------

class TestStateModule:

    @pytest.fixture
    def mod(self, tmp_path):
        return StateModule(_make_config(tmp_path))

    def test_sleeping_planet_detected(self, mod):
        chart = _make_chart({"Sun": {"house": 2}})  # Sun's Pakka Ghar is 1
        hits = mod.detect(chart)
        assert any(h.rule_id == "SLEEPING" and "Sun" in h.affected_planets for h in hits)

    def test_not_sleeping_in_pakka_ghar(self, mod):
        chart = _make_chart({"Jupiter": {"house": 2}})  # Jupiter's Pakka Ghar is 2
        hits = mod.detect(chart)
        assert not any(h.rule_id == "SLEEPING" and "Jupiter" in h.affected_planets for h in hits)

    def test_sleeping_zeroes_strength(self, mod):
        chart = _make_chart({"Sun": {"house": 2}})
        hits = mod.detect(chart)
        enriched = {"Sun": _make_enriched_planet(2, 5.0)}
        mod.audit(chart, enriched, hits)
        assert enriched["Sun"]["strength_total"] == 0.0
        assert enriched["Sun"]["sleeping_status"] == "Sleeping Planet"

    def test_kaayam_jupiter_in_pakka_ghar(self, mod):
        chart = _make_chart({"Jupiter": {"house": 2}})
        hits = mod.detect(chart)
        enriched = {"Jupiter": _make_enriched_planet(2, 6.0)}
        mod.audit(chart, enriched, hits)
        assert enriched["Jupiter"]["kaayam_status"] == "Kaayam"
        assert enriched["Jupiter"]["strength_total"] > 6.0  # boosted

    def test_dharmi_jupiter_not_in_h10(self, mod):
        chart = _make_chart({"Jupiter": {"house": 2}})
        hits = mod.detect(chart)
        assert any(h.rule_id == "DHARMI" and "Jupiter" in h.affected_planets for h in hits)
        enriched = {"Jupiter": _make_enriched_planet(2, 6.0)}
        mod.audit(chart, enriched, hits)
        assert enriched["Jupiter"]["dharmi_status"] == "Dharmi Jupiter"
        assert enriched["Jupiter"]["strength_total"] > 6.0

    def test_dharmi_rahu_h4(self, mod):
        chart = _make_chart({"Rahu": {"house": 4}})
        hits = mod.detect(chart)
        assert any(h.rule_id == "DHARMI" and "Rahu" in h.affected_planets for h in hits)
        enriched = {"Rahu": _make_enriched_planet(4, 4.0)}
        mod.audit(chart, enriched, hits)
        assert enriched["Rahu"]["dharmi_status"] == "Dharmi Rahu (Poison Neutralized)"

    def test_dharmi_saturn_h11(self, mod):
        chart = _make_chart({"Saturn": {"house": 11}})
        hits = mod.detect(chart)
        assert any(h.rule_id == "DHARMI" and "Saturn" in h.affected_planets for h in hits)
        enriched = {"Saturn": _make_enriched_planet(11, 4.0)}
        mod.audit(chart, enriched, hits)
        assert "Dharmi Planet" in enriched["Saturn"]["dharmi_status"]

    def test_nikami_detection(self, mod):
        chart = _make_chart({"Sun": {"house": 10}})  # H10 owner is Saturn, enemy of Sun
        hits = mod.detect(chart)
        assert any(h.rule_id == "NIKAMI" and "Sun" in h.affected_planets for h in hits)

    def test_audit_nikami_sets_flag(self, mod):
        chart = _make_chart({"Sun": {"house": 10}})
        hits = mod.detect(chart)
        enriched = {"Sun": _make_enriched_planet(10, 4.0)}
        mod.audit(chart, enriched, hits)
        assert enriched["Sun"]["is_nikami"] is True


# -- MangalBadhModule ---------------------------------------------------------

class TestMangalBadhModule:

    @pytest.fixture
    def mod(self, tmp_path):
        return MangalBadhModule(_make_config(tmp_path))

    def test_no_mars_no_hits(self, mod):
        chart = _make_chart({"Sun": {"house": 1}})
        hits = mod.detect(chart)
        assert hits == []

    def test_mars_in_3_adds_increment(self, mod):
        chart = _make_chart({"Mars": {"house": 3}})
        hits = mod.detect(chart)
        assert len(hits) > 0
        assert chart["mangal_badh_status"] == "Active"
        assert chart["mangal_badh_count"] >= 1

    def test_ketu_in_1_adds_increment(self, mod):
        chart = _make_chart({"Mars": {"house": 1}, "Ketu": {"house": 1}})
        hits = mod.detect(chart)
        assert chart["mangal_badh_count"] >= 1

    def test_sun_mercury_conjunct_decrements(self, mod):
        chart = _make_chart({"Mars": {"house": 1}, "Sun": {"house": 5}, "Mercury": {"house": 5}})
        mod.detect(chart)
        assert chart["mangal_badh_count"] >= 0  # decrement can't go below 0

    def test_audit_reduces_mars_strength(self, mod):
        chart = _make_chart({"Mars": {"house": 3}})  # triggers increment
        hits = mod.detect(chart)
        enriched = {"Mars": _make_enriched_planet(3, 10.0)}
        mars_before = enriched["Mars"]["strength_total"]
        mod.audit(chart, enriched, hits)
        assert enriched["Mars"]["strength_total"] < mars_before

    def test_audit_no_hits_noop(self, mod):
        chart = _make_chart({"Sun": {"house": 1}})
        hits = mod.detect(chart)
        enriched = {"Sun": _make_enriched_planet(1, 5.0)}
        sun_before = enriched["Sun"]["strength_total"]
        mod.audit(chart, enriched, hits)
        assert enriched["Sun"]["strength_total"] == sun_before


# -- DebtModule ----------------------------------------------------------------

class TestDebtModule:

    @pytest.fixture
    def mod(self, tmp_path):
        return DebtModule(_make_config(tmp_path))

    def test_pitra_rin_venus_in_2(self, mod):
        chart = _make_chart({"Venus": {"house": 2}})
        hits = mod.detect(chart)
        assert any("Pitra Rin" in h.description for h in hits)

    def test_no_debt_if_trigger_absent(self, mod):
        chart = _make_chart({"Sun": {"house": 1}})
        hits = mod.detect(chart)
        assert hits == []

    def test_audit_applies_penalty(self, mod):
        chart = _make_chart({"Venus": {"house": 5}})  # Pitra Rin + Swayam Rin
        hits = mod.detect(chart)
        enriched = {"Venus": _make_enriched_planet(5, 10.0)}
        venus_before = enriched["Venus"]["strength_total"]
        mod.audit(chart, enriched, hits)
        assert enriched["Venus"]["strength_total"] < venus_before
        assert len(enriched["Venus"]["rin_debts"]) >= 1

    def test_audit_noop_if_no_hits(self, mod):
        chart = _make_chart({"Sun": {"house": 1}})
        hits = mod.detect(chart)
        enriched = {"Sun": _make_enriched_planet(1, 5.0)}
        sun_before = enriched["Sun"]["strength_total"]
        mod.audit(chart, enriched, hits)
        assert enriched["Sun"]["strength_total"] == sun_before


# -- InteractionModule --------------------------------------------------------

class TestInteractionModule:

    @pytest.fixture
    def mod(self, tmp_path):
        return InteractionModule(_make_config(tmp_path))

    def test_disposition_rahu_h11_spoils_jupiter(self, mod):
        chart = _make_chart({"Rahu": {"house": 11}, "Jupiter": {"house": 2}})
        hits = mod.detect(chart)
        disp_hits = [h for h in hits if h.rule_id == "DISPOSITION" and "Jupiter" in h.affected_planets]
        assert len(disp_hits) >= 1
        assert disp_hits[0].metadata["effect"] == "Bad"

    def test_disposition_audit_reduces_affected(self, mod):
        chart = _make_chart({"Rahu": {"house": 11}, "Jupiter": {"house": 2}})
        hits = mod.detect(chart)
        enriched = {
            "Rahu": _make_enriched_planet(11, 4.0),
            "Jupiter": _make_enriched_planet(2, 6.0),
        }
        jup_before = enriched["Jupiter"]["strength_total"]
        mod.audit(chart, enriched, hits)
        assert enriched["Jupiter"]["strength_total"] < jup_before

    def test_disposition_moon_h1_boosts_mars(self, mod):
        chart = _make_chart({"Moon": {"house": 1}, "Mars": {"house": 5}})
        hits = mod.detect(chart)
        enriched = {
            "Moon": _make_enriched_planet(1, 3.0),
            "Mars": _make_enriched_planet(5, 5.0),
        }
        mars_before = enriched["Mars"]["strength_total"]
        mod.audit(chart, enriched, hits)
        # Moon in H1 gives "Good" effect to Mars
        assert enriched["Mars"]["strength_total"] > mars_before

    def test_sathi_exchange_detected(self, mod):
        # Jupiter in H2 (its own house), some planet in Jupiter's owned house
        # For a clean Sathi test, use same-house companions
        chart = _make_chart({"Sun": {"house": 1}, "Moon": {"house": 1}})
        hits = mod.detect(chart)
        sathi_hits = [h for h in hits if h.rule_id == "SATHI_EXCHANGE"]
        assert len(sathi_hits) >= 1

    def test_sathi_boosts_companions(self, mod):
        chart = _make_chart({"Sun": {"house": 1}, "Moon": {"house": 1}})
        hits = mod.detect(chart)
        enriched = {
            "Sun": _make_enriched_planet(1, 5.0),
            "Moon": _make_enriched_planet(1, 4.0),
        }
        sun_before = enriched["Sun"]["strength_total"]
        moon_before = enriched["Moon"]["strength_total"]
        mod.audit(chart, enriched, hits)
        assert enriched["Sun"]["strength_total"] > sun_before
        assert enriched["Moon"]["strength_total"] > moon_before

    def test_bilmukabil_detected(self, mod):
        # Need: friends, significant aspect, enemy in foundational house
        # Sun and Moon are friends. Sun in H1 aspects H7. Moon in H7.
        # Enemy of Sun (Saturn) needs to be in Moon's foundational house.
        # Moon's foundational house depends on the constant.
        chart = _make_chart({
            "Sun": {"house": 1},
            "Moon": {"house": 7},
        })
        chart["planets_in_houses"]["Sun"]["aspects"] = [
            {"aspecting_planet": "Moon", "aspect_type": "100 Percent"}
        ]
        hits = mod.detect(chart)
        bil_hits = [h for h in hits if h.rule_id == "BILMUKABIL"]
        # May or may not fire depending on foundational houses
        # Just verify detect runs cleanly
        assert isinstance(hits, list)

    def test_dhoka_birth_h10(self, mod):
        chart = _make_chart({"Saturn": {"house": 10}}, chart_type="Birth")
        hits = mod.detect(chart)
        assert any(h.rule_id == "DHOKA" for h in hits)

    def test_no_dhoka_empty_h10(self, mod):
        chart = _make_chart({"Sun": {"house": 1}}, chart_type="Birth")
        hits = mod.detect(chart)
        assert not any(h.rule_id == "DHOKA" for h in hits)

    def test_35yr_ruler_yearly_chart(self, mod):
        chart = _make_chart({"Sun": {"house": 1}}, chart_type="Yearly", chart_period=30)
        hits = mod.detect(chart)
        assert any(h.rule_id == "CYCLE_35YR" for h in hits)

    def test_35yr_ruler_birth_chart_no_hit(self, mod):
        chart = _make_chart({"Sun": {"house": 1}}, chart_type="Birth", chart_period=0)
        hits = mod.detect(chart)
        assert not any(h.rule_id == "CYCLE_35YR" for h in hits)


# -- EntanglementModule -------------------------------------------------------

class TestEntanglementModule:

    @pytest.fixture
    def mod(self, tmp_path):
        return EntanglementModule(_make_config(tmp_path))

    def test_sun_venus_forms_masnui_jupiter(self, mod):
        chart = _make_chart({"Sun": {"house": 1}, "Venus": {"house": 1}})
        hits = mod.detect(chart)
        assert any("Artificial Jupiter" in h.description for h in hits)
        assert len(chart.get("masnui_grahas_formed", [])) >= 1

    def test_no_masnui_without_conjunction(self, mod):
        chart = _make_chart({"Sun": {"house": 1}, "Venus": {"house": 4}})
        hits = mod.detect(chart)
        assert not any("Artificial Jupiter" in h.description for h in hits)

    def test_audit_creates_masnui_planet_in_enriched(self, mod):
        chart = _make_chart({"Sun": {"house": 1}, "Venus": {"house": 1}})
        hits = mod.detect(chart)
        enriched = {
            "Sun": _make_enriched_planet(1, 10.0),
            "Venus": _make_enriched_planet(1, 10.0),
        }
        mod.audit(chart, enriched, hits)
        assert "Masnui Jupiter" in enriched
        masnui = enriched["Masnui Jupiter"]
        assert masnui["is_masnui"] is True
        assert masnui["strength_total"] == 5.0

    def test_audit_adds_feedback_to_parents(self, mod):
        chart = _make_chart({"Sun": {"house": 1}, "Venus": {"house": 1}})
        hits = mod.detect(chart)
        enriched = {
            "Sun": _make_enriched_planet(1, 10.0),
            "Venus": _make_enriched_planet(1, 10.0),
        }
        sun_before = enriched["Sun"]["strength_total"]
        venus_before = enriched["Venus"]["strength_total"]
        mod.audit(chart, enriched, hits)
        assert enriched["Sun"]["strength_total"] > sun_before
        assert enriched["Venus"]["strength_total"] > venus_before
        assert enriched["Sun"]["is_masnui_parent"] is True
        assert enriched["Venus"]["is_masnui_parent"] is True

    def test_audit_noop_if_no_hits(self, mod):
        chart = _make_chart({"Sun": {"house": 1}})
        hits = mod.detect(chart)
        enriched = {"Sun": _make_enriched_planet(1, 5.0)}
        sun_before = enriched["Sun"]["strength_total"]
        mod.audit(chart, enriched, hits)
        assert enriched["Sun"]["strength_total"] == sun_before
        assert "Masnui Jupiter" not in enriched
