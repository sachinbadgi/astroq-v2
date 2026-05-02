"""
Tests for Module 4: Rules Engine.

Tests written FIRST (TDD Red phase) — 14 unit tests covering
deterministic rule loading, condition evaluation (AND/OR/NOT,
placement, conjunction, confrontation), and RuleHit creation.
"""

import sqlite3
import json
import pytest

from astroq.lk_prediction.data_contracts import RuleHit

# We import lazily inside tests to support RED-first execution.

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _setup_test_rules_db(db_path):
    """Create deterministic_rules table and insert test data."""
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS deterministic_rules (
            id TEXT PRIMARY KEY,
            domain TEXT,
            description TEXT,
            condition TEXT,
            verdict TEXT,
            scale TEXT,
            scoring_type TEXT,
            success_weight REAL,
            source_page TEXT
        )
    ''')

    rules = [
        # Rule 1: Simple Placement (Sun in House 1)
        ("rule_sun_h1", "career", "Sun in ascendant is good", 
         json.dumps({"type": "placement", "planet": "Sun", "houses": [1]}),
         "Good for self-confidence", "major", "boost", 0.8, "Page 42"),

        # Rule 2: Conjunction (Sun + Mercury in House 1)
        ("rule_sun_mer_h1", "career", "Budhaditya in 1st",
         json.dumps({"type": "AND", "conditions": [
             {"type": "placement", "planet": "Sun", "houses": [1]},
             {"type": "placement", "planet": "Mercury", "houses": [1]}
         ]}),
         "Highly auspicious", "major", "boost", 0.9, "Page 100"),

        # Rule 3: Confrontation (Sun aspects Saturn)
        ("rule_sun_saturn_conf", "health", "Sun-Saturn clash",
         json.dumps({"type": "confrontation", "planet_a": "Sun", "planet_b": "Saturn"}),
         "Friction", "minor", "penalty", 0.5, "Page 20"),

        # Rule 4: OR condition (Mars in 1 or 8)
        ("rule_mars_1_8", "marriage", "Manglik dosa",
         json.dumps({"type": "OR", "conditions": [
             {"type": "placement", "planet": "Mars", "houses": [1]},
             {"type": "placement", "planet": "Mars", "houses": [8]}
         ]}),
         "Manglik", "major", "penalty", 0.7, "Page 30"),

         # Rule 5: NOT condition (Jupiter NOT in 10)
        ("rule_jup_not_10", "wealth", "Jupiter safe from fall",
         json.dumps({"type": "NOT", "condition": 
             {"type": "placement", "planet": "Jupiter", "houses": [10]}
         }),
         "Saved from debilitation", "minor", "boost", 0.4, "Page 50"),
         
        # New Rule: Chapter 16 Travel
        ("LK_GOSW_CH16_TRAVEL_KETU_H7", "travel", "Ketu in H7 -> Auspicious travel",
         json.dumps({"type": "placement", "planet": "Ketu", "houses": [7]}),
         "Auspicious travel and change of city.", "major", "boost", 0.85, "Page 296"),

        # New Rule: Chapter 17 Marriage
        ("LK_GOSW_CH17_MARR_VENUS_H4", "marriage", "Venus in H4 -> Delayed marriage",
         json.dumps({"type": "placement", "planet": "Venus", "houses": [4]}),
         "Marriage may be delayed or doubtful without remedies.", "moderate", "penalty", 0.8, "Page 298"),

        # New Rule: Chapter 16 Profession
        ("LK_GOSW_CH16_PROF_SUN_H10", "profession", "Sun in H10 -> Govt, Accounts",
         json.dumps({"type": "placement", "planet": "Sun", "houses": [10]}),
         "Profession / Fortune related to: Govt, Accounts, Books.", "major", "boost", 0.8, "Page 280-281"),

        # New Rule: Chapter 17 Progeny
        ("LK_GOSW_CH17_PROG_KETU_H11", "progeny", "Ketu in H11 -> Male Child",
         json.dumps({"type": "placement", "planet": "Ketu", "houses": [11]}),
         "Gives male child.", "major", "boost", 0.85, "Page 308-313"),

        # New Rule: Chapter 18 Wealth
        ("LK_GOSW_CH18_WEALTH_JUPITER_SUN", "wealth", "Jupiter-Sun together",
         json.dumps({"type": "AND", "conditions": [
            {"type": "OR", "conditions": [
                 {"type": "AND", "conditions": [{"type": "placement", "planet": "Jupiter", "houses": [1]}, {"type": "placement", "planet": "Sun", "houses": [1]}]}
            ]}
         ]}),
         "Super-royal income, yielding 21 base income units.", "extreme", "boost", 0.8, "Page 314"),
    ]

    cur.executemany('''
        INSERT OR REPLACE INTO deterministic_rules 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', rules)
    con.commit()
    con.close()


def _make_minimal_chart(planets_data):
    return {
        "chart_type": "Birth",
        "chart_period": 0,
        "planets_in_houses": planets_data,
        "house_status": {}
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRulesEngine:

    @pytest.fixture
    def rules_engine(self, tmp_db, tmp_defaults):
        _setup_test_rules_db(tmp_db)
        from astroq.lk_prediction.config import ModelConfig
        from astroq.lk_prediction.rules_engine import RulesEngine
        cfg = ModelConfig(db_path=tmp_db, defaults_path=tmp_defaults)
        return RulesEngine(cfg_or_db_path=tmp_db)

    # -- 1. Placement Evaluation --
    def test_placement_rule_fires_if_planet_in_target_house(self, rules_engine):
        chart = _make_minimal_chart({"Sun": {"house": 1}})
        hits = rules_engine.evaluate_chart(chart)
        
        # Should hit rule_sun_h1
        hit_ids = [h.rule_id for h in hits]
        assert "rule_sun_h1" in hit_ids
        
        # Verify the RuleHit contract
        hit = next(h for h in hits if h.rule_id == "rule_sun_h1")
        assert hit.domain == "career"
        assert "Sun" in hit.primary_target_planets
        assert 1 in hit.target_houses
        assert hit.scoring_type == "boost"
        assert hit.specificity == 1 # 1 base condition

    def test_placement_rule_misses_if_planet_elsewhere(self, rules_engine):
        chart = _make_minimal_chart({"Sun": {"house": 2}})
        hits = rules_engine.evaluate_chart(chart)
        assert not any(h.rule_id == "rule_sun_h1" for h in hits)

    def test_placement_rule_misses_if_planet_missing(self, rules_engine):
        chart = _make_minimal_chart({"Moon": {"house": 1}})
        hits = rules_engine.evaluate_chart(chart)
        assert not any(h.rule_id == "rule_sun_h1" for h in hits)

    # -- 2. Conjunction (AND) Evaluation --
    def test_conjunction_and_rule_fires_if_all_true(self, rules_engine):
        chart = _make_minimal_chart({"Sun": {"house": 1}, "Mercury": {"house": 1}})
        hits = rules_engine.evaluate_chart(chart)
        
        hit_ids = [h.rule_id for h in hits]
        # Should hit BOTH the simple Sun rule and the compound Sun+Mercury rule
        assert "rule_sun_h1" in hit_ids
        assert "rule_sun_mer_h1" in hit_ids
        
        hit = next(h for h in hits if h.rule_id == "rule_sun_mer_h1")
        assert hit.specificity == 2 # 2 base conditions
        assert "Sun" in hit.primary_target_planets
        assert "Mercury" in hit.primary_target_planets

    def test_conjunction_and_rule_misses_if_partial_true(self, rules_engine):
        chart = _make_minimal_chart({"Sun": {"house": 1}, "Mercury": {"house": 2}})
        hits = rules_engine.evaluate_chart(chart)
        
        hit_ids = [h.rule_id for h in hits]
        assert "rule_sun_h1" in hit_ids # Sun is in 1
        assert "rule_sun_mer_h1" not in hit_ids # Mercury is not in 1

    # -- 3. Confrontation Evaluation --
    def test_confrontation_rule_fires_based_on_aspects(self, rules_engine):
        chart = _make_minimal_chart({
            "Sun": {"house": 1, "aspects": [{"target": "Saturn", "aspect_type": "100 Percent"}]},
            "Saturn": {"house": 7}
        })
        hits = rules_engine.evaluate_chart(chart)
        assert any(h.rule_id == "rule_sun_saturn_conf" for h in hits)

    def test_confrontation_rule_misses_if_no_aspect(self, rules_engine):
        chart = _make_minimal_chart({
            "Sun": {"house": 1},
            "Saturn": {"house": 2}
        })
        hits = rules_engine.evaluate_chart(chart)
        assert not any(h.rule_id == "rule_sun_saturn_conf" for h in hits)

    # -- 4. OR Condition Evaluation --
    def test_or_rule_fires_if_first_true(self, rules_engine):
        chart = _make_minimal_chart({"Mars": {"house": 1}})
        hits = rules_engine.evaluate_chart(chart)
        assert any(h.rule_id == "rule_mars_1_8" for h in hits)

    def test_or_rule_fires_if_second_true(self, rules_engine):
        chart = _make_minimal_chart({"Mars": {"house": 8}})
        hits = rules_engine.evaluate_chart(chart)
        assert any(h.rule_id == "rule_mars_1_8" for h in hits)

    def test_or_rule_misses_if_both_false(self, rules_engine):
        chart = _make_minimal_chart({"Mars": {"house": 2}})
        hits = rules_engine.evaluate_chart(chart)
        assert not any(h.rule_id == "rule_mars_1_8" for h in hits)

    # -- 5. NOT Condition Evaluation --
    def test_not_rule_fires_if_condition_false(self, rules_engine):
        chart = _make_minimal_chart({"Jupiter": {"house": 11}})
        hits = rules_engine.evaluate_chart(chart)
        assert any(h.rule_id == "rule_jup_not_10" for h in hits)

    def test_not_rule_misses_if_condition_true(self, rules_engine):
        chart = _make_minimal_chart({"Jupiter": {"house": 10}})
        hits = rules_engine.evaluate_chart(chart)
        assert not any(h.rule_id == "rule_jup_not_10" for h in hits)

    # -- 6. Magnitude calculation and sorting --
    def test_rule_magnitudes_use_config_scaling(self, rules_engine):
        from astroq.lk_prediction.astrological_context import UnifiedAstrologicalContext
        from astroq.lk_prediction.data_contracts import EnrichedChart

        ctx = UnifiedAstrologicalContext(enriched=EnrichedChart(source={}))

        # Test magnitude scaling function (scale mapping: minor=1, moderate=2, major=3, deterministic/extreme=4+)
        assert ctx._apply_scale_to_base("minor", 0.04) == 0.04 * 1
        assert ctx._apply_scale_to_base("major", 0.04) == 0.04 * 3

    def test_hits_are_sorted_by_specificity_descending(self, rules_engine):
        chart = _make_minimal_chart({"Sun": {"house": 1}, "Mercury": {"house": 1}})
        hits = rules_engine.evaluate_chart(chart)
        
        # Both rule_sun_h1 (spec=1) and rule_sun_mer_h1 (spec=2) should fire.
        # Highest specificity should be first.
        assert len(hits) >= 2
        assert hits[0].rule_id == "rule_sun_mer_h1"
        assert hits[1].rule_id == "rule_sun_h1"

    # -- 7. Gosvami Ch 16-19 Domain Rules Evaluation --
    def test_travel_ketu_h7_rule_fires(self, rules_engine):
        chart = _make_minimal_chart({"Ketu": {"house": 7}})
        hits = rules_engine.evaluate_chart(chart)
        assert any(h.rule_id == "LK_GOSW_CH16_TRAVEL_KETU_H7" for h in hits)
        hit = next(h for h in hits if h.rule_id == "LK_GOSW_CH16_TRAVEL_KETU_H7")
        assert hit.domain == "travel"
        assert hit.scoring_type == "boost"

    def test_marriage_venus_h4_rule_fires(self, rules_engine):
        chart = _make_minimal_chart({"Venus": {"house": 4}})
        hits = rules_engine.evaluate_chart(chart)
        assert any(h.rule_id == "LK_GOSW_CH17_MARR_VENUS_H4" for h in hits)
        hit = next(h for h in hits if h.rule_id == "LK_GOSW_CH17_MARR_VENUS_H4")
        assert hit.domain == "marriage"
        assert hit.scoring_type == "penalty"

    def test_profession_sun_h10_rule_fires(self, rules_engine):
        chart = _make_minimal_chart({"Sun": {"house": 10}})
        hits = rules_engine.evaluate_chart(chart)
        assert any(h.rule_id == "LK_GOSW_CH16_PROF_SUN_H10" for h in hits)
        hit = next(h for h in hits if h.rule_id == "LK_GOSW_CH16_PROF_SUN_H10")
        assert hit.domain == "profession"
        assert hit.scoring_type == "boost"

    def test_progeny_ketu_h11_rule_fires(self, rules_engine):
        chart = _make_minimal_chart({"Ketu": {"house": 11}})
        hits = rules_engine.evaluate_chart(chart)
        assert any(h.rule_id == "LK_GOSW_CH17_PROG_KETU_H11" for h in hits)
        hit = next(h for h in hits if h.rule_id == "LK_GOSW_CH17_PROG_KETU_H11")
        assert hit.domain == "progeny"
        assert hit.scoring_type == "boost"

    def test_wealth_jup_sun_rule_fires(self, rules_engine):
        chart = _make_minimal_chart({"Sun": {"house": 1}, "Jupiter": {"house": 1}})
        hits = rules_engine.evaluate_chart(chart)
        assert any(h.rule_id == "LK_GOSW_CH18_WEALTH_JUPITER_SUN" for h in hits)
        hit = next(h for h in hits if h.rule_id == "LK_GOSW_CH18_WEALTH_JUPITER_SUN")
        assert hit.domain == "wealth"
        assert hit.scoring_type == "boost"
