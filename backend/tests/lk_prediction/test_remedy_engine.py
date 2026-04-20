"""
Phase B: TDD tests for RemedyEngine — written FIRST (Red phase).

22 unit tests covering:
  Group 1 (4): get_safe_houses
  Group 2 (3): get_year_shifting_options
  Group 3 (5): rank_safe_houses
  Group 4 (4): simulate_lifetime_strength
  Group 5 (2): analyze_life_area_potential
  Group 6 (3): generate_remedy_hints
  Group 7 (2): config integration
"""

from __future__ import annotations

import json
import sqlite3
import pytest
from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_db(tmp_path):
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS model_config "
        "(key TEXT PRIMARY KEY, value TEXT, figure TEXT)"
    )
    conn.commit()
    conn.close()
    return str(db)


@pytest.fixture
def tmp_defaults(tmp_path):
    defaults = {
        "remedy.shifting_boost": 2.5,
        "remedy.residual_impact_factor": 0.05,
        "remedy.safe_multiplier": 1.0,
        "remedy.goswami_h9_weight": 30,
        "remedy.goswami_h2_weight": 20,
        "remedy.goswami_h4_weight": 10,
        "remedy.goswami_unblock_weight": 50,
        "remedy.goswami_pair_weight": 40,
        "remedy.goswami_doubtful_weight": 20,
        "remedy.critical_score_threshold": 60,
        "remedy.high_score_threshold": 40,
        "remedy.medium_score_threshold": 20,
        "remedy.mangal_badh_hints": ["Honey in bowl", "Sweet rotis"],
        "remedy.birth_day_remedies": {
            "0": "Sunday remedy",
            "1": "Monday: milk",
            "2": "Tuesday remedy",
            "3": "Wednesday remedy",
            "4": "Thursday remedy",
            "5": "Friday remedy",
            "6": "Saturday remedy"
        }
    }
    f = tmp_path / "defaults.json"
    f.write_text(json.dumps(defaults))
    return str(f)


class FakeItemsResolver:
    """Minimal stub: returns a predictable article list."""
    def get_planet_items(self, planet: str, house: int) -> list[str]:
        return [f"{planet.lower()}_article_h{house}"]


def _make_engine(tmp_db, tmp_defaults):
    from astroq.lk_prediction.config import ModelConfig
    from astroq.lk_prediction.remedy_engine import RemedyEngine
    cfg = ModelConfig(db_path=tmp_db, defaults_path=tmp_defaults)
    return RemedyEngine(config=cfg, items_resolver=FakeItemsResolver())


# ---------------------------------------------------------------------------
# Helper: minimal chart structures
# ---------------------------------------------------------------------------

def _chart_with_planets(planet_house_map: dict, masnui=None) -> dict:
    """Build a minimal chart dict with planets_in_houses."""
    planets_in_houses = {}
    for planet, house in planet_house_map.items():
        planets_in_houses[planet] = {"house": house, "states": [], "strength_total": 3.0}
    chart = {
        "planets_in_houses": planets_in_houses,
        "masnui_grahas_formed": masnui or [],
    }
    return chart


def _annual_charts_simple(planet: str, ages: list[int], strength: float = 3.0) -> dict:
    """Multi-age annual chart dict with a single planet at house 1."""
    charts = {}
    for age in ages:
        charts[age] = {
            "planets_in_houses": {
                planet: {"house": 1, "states": [], "strength_total": strength}
            },
            "masnui_grahas_formed": [],
        }
    return charts


# ===========================================================================
# GROUP 1: get_safe_houses
# ===========================================================================

class TestGetSafeHouses:

    def test_get_safe_houses_no_enemies_returns_all_base_recs(self, tmp_db, tmp_defaults):
        """Sun with no enemies in any of its base recs → all returned as safe."""
        engine = _make_engine(tmp_db, tmp_defaults)
        # Sun base recs = PUCCA [1,5] + EXALTATION [1] → {1,5}
        # Chart has no enemies of Sun (no Saturn, Venus, Rahu, Ketu)
        chart = _chart_with_planets({"Moon": 2, "Jupiter": 4})
        safe, conflicts = engine.get_safe_houses("Sun", chart)
        assert set(safe) == {1, 5}
        assert len(conflicts) == 0

    def test_get_safe_houses_enemy_in_target_returns_blocked(self, tmp_db, tmp_defaults):
        """Saturn (enemy of Sun) placed in H5 blocks H5 from Sun's safe list."""
        engine = _make_engine(tmp_db, tmp_defaults)
        chart = _chart_with_planets({"Saturn": 5, "Moon": 2})
        safe, conflicts = engine.get_safe_houses("Sun", chart)
        assert 5 not in safe
        assert 5 in conflicts
        assert "Saturn" in conflicts[5]

    def test_get_safe_houses_masnui_enemy_in_target_returns_blocked(self, tmp_db, tmp_defaults):
        """Artificial Saturn in H5 resolves to Saturn → blocks Sun's H5."""
        engine = _make_engine(tmp_db, tmp_defaults)
        masnui = [{"name": "Artificial Saturn (Like Ketu)", "house": 5}]
        chart = _chart_with_planets({"Moon": 2}, masnui=masnui)
        safe, conflicts = engine.get_safe_houses("Sun", chart)
        assert 5 not in safe
        assert 5 in conflicts

    def test_get_safe_houses_empty_chart_returns_all_recs(self, tmp_db, tmp_defaults):
        """Empty planet chart → no blockers → all base recs safe."""
        engine = _make_engine(tmp_db, tmp_defaults)
        chart = _chart_with_planets({})
        safe, conflicts = engine.get_safe_houses("Sun", chart)
        assert len(safe) > 0
        assert len(conflicts) == 0


# ===========================================================================
# GROUP 2: get_year_shifting_options
# ===========================================================================

class TestGetYearShiftingOptions:

    def test_get_year_shifting_options_intersection_of_birth_and_annual(self, tmp_db, tmp_defaults):
        """A house safe in both birth AND annual appears in safe_matches."""
        engine = _make_engine(tmp_db, tmp_defaults)
        # Sun base recs = {1, 5}. Neither chart blocks them.
        birth = _chart_with_planets({"Moon": 2})
        annual = _chart_with_planets({"Moon": 3})
        result = engine.get_year_shifting_options(birth, annual, age=25)
        assert "Sun" in result
        sun_result = result["Sun"]
        safe_houses = [opt.house for opt in sun_result.safe_matches]
        assert len(safe_houses) > 0
        # Houses in safe_matches must have been safe in both charts
        birth_safe, _ = engine.get_safe_houses("Sun", birth)
        annual_safe, _ = engine.get_safe_houses("Sun", annual)
        for h in safe_houses:
            assert h in birth_safe
            assert h in annual_safe

    def test_get_year_shifting_options_no_overlap_returns_empty_safe_matches(self, tmp_db, tmp_defaults):
        """Birth blocks H5, annual blocks H1 → safe_matches for Sun is empty."""
        engine = _make_engine(tmp_db, tmp_defaults)
        # Block Sun's H5 in birth chart (Saturn=enemy in H5)
        birth = _chart_with_planets({"Saturn": 5, "Moon": 2})
        # Block Sun's H1 in annual chart (Saturn=enemy in H1)
        annual = _chart_with_planets({"Saturn": 1, "Moon": 3})
        result = engine.get_year_shifting_options(birth, annual, age=28)
        sun_result = result["Sun"]
        assert sun_result.safe_matches == []

    def test_get_year_shifting_options_conflict_map_merges_both_charts(self, tmp_db, tmp_defaults):
        """Birth conflict is prefixed 'Birth:', annual conflict is prefixed 'Annual:'."""
        engine = _make_engine(tmp_db, tmp_defaults)
        birth = _chart_with_planets({"Saturn": 5, "Moon": 2})   # blocks Sun H5 in birth
        annual = _chart_with_planets({"Saturn": 1, "Moon": 3})  # blocks Sun H1 in annual
        result = engine.get_year_shifting_options(birth, annual, age=28)
        conflicts = result["Sun"].conflicts
        # At least one conflict entry should show source
        all_conflict_text = " ".join(conflicts.values())
        assert "Birth" in all_conflict_text or "Annual" in all_conflict_text


# ===========================================================================
# GROUP 3: rank_safe_houses
# ===========================================================================

class TestRankSafeHouses:

    def _make_annual_pih(self, planet, house, states=None):
        return {planet: {"house": house, "states": states or [], "strength_total": 3.0}}

    def test_rank_safe_houses_h9_scores_higher_than_h4(self, tmp_db, tmp_defaults):
        """H9 gets +30, H4 gets +10 → H9 ranked higher than H4."""
        engine = _make_engine(tmp_db, tmp_defaults)
        # Jupiter's safe houses include 9 and 4
        annual_chart = _chart_with_planets({"Moon": 2})
        annual_pih = self._make_annual_pih("Jupiter", 2)
        opts = engine.rank_safe_houses("Jupiter", [9, 4], annual_chart, annual_pih)
        scores = {o.house: o.score for o in opts}
        assert scores[9] > scores[4]

    def test_rank_safe_houses_unblock_rule_gives_critical(self, tmp_db, tmp_defaults):
        """Planet in H8 of annual chart → targeting H4 gets +50 → CRITICAL tier."""
        engine = _make_engine(tmp_db, tmp_defaults)
        annual_chart = _chart_with_planets({"Mars": 2})
        # Jupiter is in H8 this year
        annual_pih = self._make_annual_pih("Jupiter", 8)
        opts = engine.rank_safe_houses("Jupiter", [4], annual_chart, annual_pih)
        assert len(opts) == 1
        # base(10) + h4(10) + unblock(50) = 70 → CRITICAL
        assert opts[0].rank == "CRITICAL"
        assert opts[0].score >= 60

    def test_rank_safe_houses_pair_companion_boosts_score(self, tmp_db, tmp_defaults):
        """Moon+Jupiter pair: when Jupiter targets H2 and Moon is at same annual house → +40."""
        engine = _make_engine(tmp_db, tmp_defaults)
        # Moon is in same house as Jupiter's annual_house for pair check
        # Jupiter annual house = 3, Moon is also in H3
        annual_chart = _chart_with_planets({"Moon": 3})  # Moon co-occupies with Jupiter
        annual_pih = {
            "Jupiter": {"house": 3, "states": [], "strength_total": 3.0},
            "Moon": {"house": 3, "states": [], "strength_total": 3.0},
        }
        opts = engine.rank_safe_houses("Jupiter", [2], annual_chart, annual_pih)
        assert len(opts) == 1
        # base(10) + h2(20) + pair(40) = 70 → CRITICAL
        assert opts[0].score >= 40  # at minimum High

    def test_rank_safe_houses_doubtful_planet_boosts_rank(self, tmp_db, tmp_defaults):
        """Planet with 'Doubtful' state → +20 added to score."""
        engine = _make_engine(tmp_db, tmp_defaults)
        annual_chart = _chart_with_planets({"Moon": 2})
        # Jupiter with "Doubtful" state
        annual_pih = self._make_annual_pih("Jupiter", 5, states=["Doubtful"])
        opts_doubtful = engine.rank_safe_houses("Jupiter", [11], annual_chart, annual_pih)

        annual_pih_normal = self._make_annual_pih("Jupiter", 5, states=[])
        opts_normal = engine.rank_safe_houses("Jupiter", [11], annual_chart, annual_pih_normal)

        assert opts_doubtful[0].score > opts_normal[0].score
        assert opts_doubtful[0].score - opts_normal[0].score == 20

    def test_rank_safe_houses_sorted_descending_by_score(self, tmp_db, tmp_defaults):
        """Multiple safe houses → returned sorted highest score first."""
        engine = _make_engine(tmp_db, tmp_defaults)
        annual_chart = _chart_with_planets({"Moon": 2})
        annual_pih = self._make_annual_pih("Jupiter", 5)
        # Jupiter base recs include 2,4,5,9,11,12 — use subset
        opts = engine.rank_safe_houses("Jupiter", [2, 4, 9], annual_chart, annual_pih)
        scores = [o.score for o in opts]
        assert scores == sorted(scores, reverse=True)


# ===========================================================================
# GROUP 4: simulate_lifetime_strength
# ===========================================================================

class TestSimulateLifetimeStrength:

    def test_simulate_lifetime_strength_baseline_matches_chart_strengths(self, tmp_db, tmp_defaults):
        """No remedies → remedy[age] == baseline[age] for all ages."""
        engine = _make_engine(tmp_db, tmp_defaults)
        annual_charts = _annual_charts_simple("Sun", [1, 2, 3], strength=4.5)
        birth = _chart_with_planets({"Moon": 2})
        proj = engine.simulate_lifetime_strength(birth, annual_charts, applied_remedies=[])
        sun_data = proj.planets["Sun"]
        for i, age in enumerate([1, 2, 3]):
            assert sun_data["baseline"][i] == pytest.approx(4.5)
            assert sun_data["remedy"][i] == pytest.approx(4.5)

    def test_simulate_lifetime_strength_boost_applied_correct_year(self, tmp_db, tmp_defaults):
        """Safe remedy at age 2 → remedy[age=2] = baseline + 2.5, others unchanged."""
        engine = _make_engine(tmp_db, tmp_defaults)
        annual_charts = _annual_charts_simple("Sun", [1, 2, 3], strength=1.0)
        birth = _chart_with_planets({})
        remedies = [{"planet": "Sun", "age": 2, "target_house": 1, "is_safe": True}]
        proj = engine.simulate_lifetime_strength(birth, annual_charts, applied_remedies=remedies)
        sun_data = proj.planets["Sun"]
        ages = sorted(annual_charts.keys())
        idx2 = ages.index(2)
        # At age=2: base(1.0) + boost(2.5) + any residual from age 2 itself
        assert sun_data["remedy"][idx2] > sun_data["baseline"][idx2]
        # At age=1 (before remedy): remedy == baseline
        idx1 = ages.index(1)
        assert sun_data["remedy"][idx1] == pytest.approx(sun_data["baseline"][idx1])

    def test_simulate_lifetime_strength_residual_carries_forward(self, tmp_db, tmp_defaults):
        """After remedy at age=1, residual carries into age=2 and age=3."""
        engine = _make_engine(tmp_db, tmp_defaults)
        annual_charts = _annual_charts_simple("Sun", [1, 2, 3], strength=0.0)
        birth = _chart_with_planets({})
        remedies = [{"planet": "Sun", "age": 1, "target_house": 1, "is_safe": True}]
        proj = engine.simulate_lifetime_strength(birth, annual_charts, applied_remedies=remedies)
        sun_data = proj.planets["Sun"]
        ages = sorted(annual_charts.keys())
        idx2 = ages.index(2)
        idx3 = ages.index(3)
        # residual = 2.5 * 0.05 = 0.125, so ages 2,3 should have remedy > 0
        assert sun_data["remedy"][idx2] > 0
        assert sun_data["remedy"][idx3] > 0

    def test_simulate_lifetime_strength_unsafe_remedy_half_boost(self, tmp_db, tmp_defaults):
        """Unsafe remedy applies half the boost (0.5 multiplier)."""
        engine = _make_engine(tmp_db, tmp_defaults)
        annual_charts = _annual_charts_simple("Sun", [1], strength=0.0)
        birth = _chart_with_planets({})
        safe_rem = [{"planet": "Sun", "age": 1, "target_house": 1, "is_safe": True}]
        unsafe_rem = [{"planet": "Sun", "age": 1, "target_house": 1, "is_safe": False}]
        proj_safe = engine.simulate_lifetime_strength(birth, annual_charts, safe_rem)
        proj_unsafe = engine.simulate_lifetime_strength(birth, annual_charts, unsafe_rem)
        safe_boost = proj_safe.planets["Sun"]["remedy"][0]
        unsafe_boost = proj_unsafe.planets["Sun"]["remedy"][0]
        assert safe_boost == pytest.approx(unsafe_boost * 2.0)


# ===========================================================================
# GROUP 5: analyze_life_area_potential
# ===========================================================================

class TestAnalyzeLifeAreaPotential:

    def test_analyze_life_area_potential_max_exceeds_applied(self, tmp_db, tmp_defaults):
        """max_remediable >= current_remediation (can't over-remedy)."""
        engine = _make_engine(tmp_db, tmp_defaults)
        birth = _chart_with_planets({})
        annual_charts = _annual_charts_simple("Jupiter", [1, 2, 3], strength=2.0)
        # Add other planets needed by life area groups
        for age in annual_charts:
            annual_charts[age]["planets_in_houses"]["Venus"] = {"house": 2, "states": [], "strength_total": 2.0}
            annual_charts[age]["planets_in_houses"]["Mercury"] = {"house": 3, "states": [], "strength_total": 2.0}
        remedies = [{"planet": "Jupiter", "age": 1, "target_house": 4, "is_safe": True}]
        summaries = engine.analyze_life_area_potential(birth, annual_charts, remedies, current_age=1)
        for area, summary in summaries.items():
            assert summary.max_remediable >= summary.current_remediation

    def test_analyze_life_area_potential_efficiency_correct_percentage(self, tmp_db, tmp_defaults):
        """Efficiency = (applied-baseline)/(max-baseline+0.1)*100, bounded 0-100."""
        engine = _make_engine(tmp_db, tmp_defaults)
        birth = _chart_with_planets({})
        annual_charts = _annual_charts_simple("Jupiter", [1], strength=0.0)
        for age in annual_charts:
            for p in ["Venus", "Mercury", "Sun", "Mars", "Saturn", "Moon"]:
                annual_charts[age]["planets_in_houses"][p] = {"house": 1, "states": [], "strength_total": 0.0}
        summaries = engine.analyze_life_area_potential(birth, annual_charts, [], current_age=1)
        for area, summary in summaries.items():
            assert 0.0 <= summary.remediation_efficiency <= 100.0


# ===========================================================================
# GROUP 6: generate_remedy_hints
# ===========================================================================

class TestGenerateRemedyHints:

    def _make_shifting_result(self, planet, safe_opts):
        from astroq.lk_prediction.remedy_engine import PlanetShiftingResult
        return PlanetShiftingResult(
            planet=planet,
            birth_house=1,
            annual_house=1,
            safe_matches=safe_opts,
            other_options=[],
            conflicts={},
            llm_hint="",
        )

    def _make_option(self, house, score, rank):
        from astroq.lk_prediction.remedy_engine import ShiftingOption
        return ShiftingOption(
            house=house,
            score=score,
            rank=rank,
            rationale="Test rationale",
            articles=["test_article"],
        )

    def test_generate_remedy_hints_returns_top_3_critical_high(self, tmp_db, tmp_defaults):
        """5 CRITICAL/High options → returns exactly 3."""
        engine = _make_engine(tmp_db, tmp_defaults)
        opts = [self._make_option(h, 80 - h, "CRITICAL") for h in range(1, 6)]
        year_options = {
            "Sun": self._make_shifting_result("Sun", opts[:2]),
            "Jupiter": self._make_shifting_result("Jupiter", opts[2:]),
        }
        hints = engine.generate_remedy_hints(year_options)
        assert len(hints) == 3

    def test_generate_remedy_hints_includes_planet_and_house(self, tmp_db, tmp_defaults):
        """Each hint string must mention the planet and house number."""
        engine = _make_engine(tmp_db, tmp_defaults)
        opts = [self._make_option(9, 70, "CRITICAL")]
        year_options = {"Jupiter": self._make_shifting_result("Jupiter", opts)}
        hints = engine.generate_remedy_hints(year_options)
        assert len(hints) == 1
        assert "Jupiter" in hints[0]
        assert "9" in hints[0]

    def test_generate_remedy_hints_empty_when_no_safe_matches(self, tmp_db, tmp_defaults):
        """No safe matches → generate_remedy_hints returns []."""
        engine = _make_engine(tmp_db, tmp_defaults)
        year_options = {"Sun": self._make_shifting_result("Sun", [])}
        hints = engine.generate_remedy_hints(year_options)
        assert hints == []

    # --- Phase F: Chapter 8 Alignment ---

    def test_generate_remedy_hints_includes_mangal_badh_special_hints(self, tmp_db, tmp_defaults):
        """If mangal_badh_status is 'Active', special Mars hints are included."""
        engine = _make_engine(tmp_db, tmp_defaults)
        opts = [self._make_option(10, 70, "CRITICAL")]
        year_options = {"Mars": self._make_shifting_result("Mars", opts)}
        
        chart = {
            "planets_in_houses": {"Mars": {"house": 4}},
            "mangal_badh_status": "Active"
        }
        hints = engine.generate_remedy_hints(year_options, chart=chart)
        # Should contain some special Mars text from defaults
        assert any("honey" in h.lower() or "tandoori" in h.lower() for h in hints)

    def test_generate_remedy_hints_includes_birth_day_remedy(self, tmp_db, tmp_defaults):
        """If birth_time is provided, the helpful remedy for that weekday is included."""
        engine = _make_engine(tmp_db, tmp_defaults)
        opts = [self._make_option(1, 70, "CRITICAL")]
        year_options = {"Sun": self._make_shifting_result("Sun", opts)}
        
        chart = {
            "planets_in_houses": {"Sun": {"house": 1}},
            "birth_time": "1977-11-28T18:30:00" # Monday
        }
        hints = engine.generate_remedy_hints(year_options, chart=chart)
        assert any("Monday" in h or "milk" in h.lower() for h in hints)

    def test_generate_remedy_hints_sorts_by_kendra_priority(self, tmp_db, tmp_defaults):
        """If scores are equal, hints are sorted by Order of Remedies (1 > 10 > 7 > 4)."""
        engine = _make_engine(tmp_db, tmp_defaults)
        
        # Mercury in H10 (Kendra) vs Jupiter in H9 (not Kendra)
        # Set Mercury house to 10 in shifting result so it's matched
        opts_j = [self._make_option(9, 70, "CRITICAL")]
        opts_m = [self._make_option(10, 70, "CRITICAL")]
        
        year_options = {
            "Jupiter": self._make_shifting_result("Jupiter", opts_j),
            "Mercury": self._make_shifting_result("Mercury", opts_m),
        }
        
        hints = engine.generate_remedy_hints(year_options)
        # Mercury in H10 has higher priority than Jupiter in H9
        assert "Mercury" in hints[0]
        assert "Jupiter" in hints[1]


# ===========================================================================
# GROUP 7: Config integration
# ===========================================================================

class TestConfigIntegration:

    def test_remedy_engine_config_shifting_boost_used(self, tmp_db, tmp_defaults, tmp_path):
        """Engine reads remedy.shifting_boost from config (custom value respected)."""
        import json
        import sqlite3
        # Override config with custom boost
        custom_defaults = {
            "remedy.shifting_boost": 5.0,  # non-default
            "remedy.residual_impact_factor": 0.05,
            "remedy.safe_multiplier": 1.0,
            "remedy.unsafe_multiplier": 0.5,
                "remedy.goswami_h9_weight": 30,
            "remedy.goswami_h2_weight": 20,
            "remedy.goswami_h4_weight": 10,
            "remedy.goswami_unblock_weight": 50,
            "remedy.goswami_pair_weight": 40,
            "remedy.goswami_doubtful_weight": 20,
            "remedy.critical_score_threshold": 60,
            "remedy.high_score_threshold": 40,
            "remedy.medium_score_threshold": 20,
        }
        cf = tmp_path / "custom.json"
        cf.write_text(json.dumps(custom_defaults))
        db2 = tmp_path / "test2.db"
        conn = sqlite3.connect(str(db2))
        conn.execute("CREATE TABLE IF NOT EXISTS model_config (key TEXT PRIMARY KEY, value TEXT, figure TEXT)")
        conn.commit()
        conn.close()
        from astroq.lk_prediction.config import ModelConfig
        from astroq.lk_prediction.remedy_engine import RemedyEngine
        cfg = ModelConfig(db_path=str(db2), defaults_path=str(cf))
        engine = RemedyEngine(config=cfg, items_resolver=FakeItemsResolver())
        annual_charts = _annual_charts_simple("Sun", [1], strength=0.0)
        birth = _chart_with_planets({})
        remedies = [{"planet": "Sun", "age": 1, "target_house": 1, "is_safe": True}]
        proj = engine.simulate_lifetime_strength(birth, annual_charts, remedies)
        # boost should be 5.0 + (5.0 * 0.05) = 5.25
        assert proj.planets["Sun"]["remedy"][0] == pytest.approx(5.25)

    def test_remedy_engine_config_residual_factor_used(self, tmp_db, tmp_defaults, tmp_path):
        """Engine reads remedy.residual_impact_factor from config (custom value respected)."""
        import json
        import sqlite3
        custom_defaults = {
            "remedy.shifting_boost": 2.5,
            "remedy.residual_impact_factor": 0.20,  # custom: 20%
            "remedy.safe_multiplier": 1.0,
            "remedy.unsafe_multiplier": 0.5,
                "remedy.goswami_h9_weight": 30,
            "remedy.goswami_h2_weight": 20,
            "remedy.goswami_h4_weight": 10,
            "remedy.goswami_unblock_weight": 50,
            "remedy.goswami_pair_weight": 40,
            "remedy.goswami_doubtful_weight": 20,
            "remedy.critical_score_threshold": 60,
            "remedy.high_score_threshold": 40,
            "remedy.medium_score_threshold": 20,
        }
        cf = tmp_path / "custom2.json"
        cf.write_text(json.dumps(custom_defaults))
        db2 = tmp_path / "test3.db"
        conn = sqlite3.connect(str(db2))
        conn.execute("CREATE TABLE IF NOT EXISTS model_config (key TEXT PRIMARY KEY, value TEXT, figure TEXT)")
        conn.commit()
        conn.close()
        from astroq.lk_prediction.config import ModelConfig
        from astroq.lk_prediction.remedy_engine import RemedyEngine
        cfg = ModelConfig(db_path=str(db2), defaults_path=str(cf))
        engine = RemedyEngine(config=cfg, items_resolver=FakeItemsResolver())
        annual_charts = _annual_charts_simple("Sun", [1, 2], strength=0.0)
        birth = _chart_with_planets({})
        remedies = [{"planet": "Sun", "age": 1, "target_house": 1, "is_safe": True}]
        proj = engine.simulate_lifetime_strength(birth, annual_charts, remedies)
        ages = sorted(annual_charts.keys())
        idx2 = ages.index(2)
        # residual at age=2 should be 2.5 * 0.20 = 0.5 (not 2.5 * 0.05 = 0.125)
        assert proj.planets["Sun"]["remedy"][idx2] == pytest.approx(0.5)
