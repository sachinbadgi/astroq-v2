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
            "Sun": {"house": 1, "aspects": [{"aspecting_planet": "Saturn", "aspect_type": "100 Percent"}]},
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
        from astroq.lk_prediction.rules_engine import apply_scale_to_magnitude
        
        # Test magnitude scaling function (scale mapping: minor=1, moderate=2, major=3, deterministic/extreme=4+)
        assert apply_scale_to_magnitude("minor", 0.04) == 0.04 * 1
        assert apply_scale_to_magnitude("major", 0.04) == 0.04 * 3

    def test_hits_are_sorted_by_specificity_descending(self, rules_engine):
        chart = _make_minimal_chart({"Sun": {"house": 1}, "Mercury": {"house": 1}})
        hits = rules_engine.evaluate_chart(chart)
        
        # Both rule_sun_h1 (spec=1) and rule_sun_mer_h1 (spec=2) should fire.
        # Highest specificity should be first.
        assert len(hits) >= 2
        assert hits[0].rule_id == "rule_sun_mer_h1"
        assert hits[1].rule_id == "rule_sun_h1"
