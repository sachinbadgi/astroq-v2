"""
Lal Kitab Grammar Logic Depth Validation.

This suite verifies the core tag-based logic (Kaayam, Dharmi, Masnui, etc.)
and validates the RulesEngine against specific high-fidelity rule patterns.
"""

import pytest
import json
import sqlite3
import os
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.grammar_analyser import GrammarAnalyser
from astroq.lk_prediction.strength_engine import StrengthEngine
from astroq.lk_prediction.rules_engine import RulesEngine
from astroq.lk_prediction.astrological_context import UnifiedAstrologicalContext
from astroq.lk_prediction.data_contracts import EnrichedChart

@pytest.fixture
def env_setup(tmp_path):
    db_path = tmp_path / "test_rules.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE deterministic_rules (id TEXT, domain TEXT, description TEXT, condition TEXT, scoring_type TEXT, scale TEXT, magnitude REAL, success_weight REAL)")
    
    # 1. Insert a handful of valid rules for testing
    rules = [
        ("RULE_SUN_H4", "career", "Sun in H4 gives honors", 
         '{"type": "placement", "planet": "Sun", "houses": [4]}', "boost", "major", 5.0, 1.0),
        ("RULE_TAK_MOON_VEN", "health", "Moon confronts Venus", 
         '{"type": "confrontation", "planet_a": "Moon", "planet_b": "Venus"}', "penalty", "minor", 1.0, 1.0),
    ]
    conn.executemany("INSERT INTO deterministic_rules VALUES (?,?,?,?,?,?,?,?)", rules)
    conn.commit()
    conn.close()
    
    defaults_path = tmp_path / "defaults.json"
    with open(defaults_path, "w") as f:
        json.dump({"strength": {"mangal_badh_divisor": 16.0, "masnui_parent_feedback": 0.3}}, f)
        
    cfg = ModelConfig(db_path=str(db_path), defaults_path=str(defaults_path))
    return cfg, GrammarAnalyser(cfg), StrengthEngine(cfg), RulesEngine(cfg)

class TestGrammarDepth:

    def test_kaayam_planet_tag(self, env_setup):
        """A planet is Kaayam if its friends are in supportive houses or no enemies oppose it."""
        cfg, grammar, strength, _ = env_setup
        # Jupiter Pakka Ghar is 2. 
        # In our engine, Kaayam is detected if a planet is in its Pakka Ghar 
        # and not hit by an equal or enemy.
        chart = {
            "planets_in_houses": {
                "Jupiter": {"house": 2} # Pakka Ghar
            }
        }
        enriched = strength.calculate_chart_strengths(chart)
        grammar.apply_grammar_rules(chart, enriched)
        
        # Verify tag and boost
        assert enriched["Jupiter"]["kaayam_status"] == "Kaayam"

    def test_kaayam_negative_enemy_hit(self, env_setup):
        """A planet should NOT be Kaayam if it is hit by an enemy aspect."""
        cfg, grammar, strength, _ = env_setup
        # Sun in H1 (Pakka Ghar). 
        # Caster: Saturn in H1 hits H7? No.
        # Let's use Moon (Pakka H4) vs Ketu (Enemy of Moon hitting H4).
        # Ketu in H6 aspecting H4? No.
        # Let's use Sun in H1 and Saturn in H7 (100% direct hit).
        chart = {
            "planets_in_houses": {
                "Sun": {"house": 1},
                "Saturn": {"house": 7}
            }
        }
        enriched = strength.calculate_chart_strengths(chart)
        # Force the hit if the automated calculator is being subtle
        enriched["Saturn"]["aspects"] = [{"target": "Sun", "aspect_type": "100 Percent", "relationship": "enemy"}]
        
        grammar.apply_grammar_rules(chart, enriched)
        assert enriched["Sun"].get("kaayam_status") != "Kaayam"

    def test_masnui_jupiter_formation(self, env_setup):
        """Sun + Venus = Artificial Jupiter."""
        cfg, grammar, strength, _ = env_setup
        chart = {
            "planets_in_houses": {
                "Sun": {"house": 1},
                "Venus": {"house": 1}
            }
        }
        enriched = strength.calculate_chart_strengths(chart)
        grammar.apply_grammar_rules(chart, enriched)
        
        assert "Masnui Jupiter" in enriched
        # Feedback to parents
        assert enriched["Sun"]["strength_breakdown"]["masnui_feedback"] > 0

    def test_masnui_negative_no_conjunction(self, env_setup):
        """Non-masnui conjunctions (e.g. Sun + Moon) should NOT form artificial planets."""
        cfg, _, strength, _ = env_setup
        chart = {
            "planets_in_houses": {
                "Sun": {"house": 4},
                "Moon": {"house": 4}
            }
        }
        enriched = strength.calculate_chart_strengths(chart)
        # Should not find Moon-Sun artificial in our MASNUI_FORMATION_RULES
        assert not any(ep.get("is_masnui") for ep in enriched.values())

    def test_bil_mukabil_hostility_tag(self, env_setup):
        """Hostility tag 'bilmukabil_hostile_to' should populate under 3-step logic."""
        cfg, grammar, strength, _ = env_setup
        # Jupiter (2) vs Sun (5). 
        # Foundational house of Sun is 5. 
        # Venus (Enemy of Jupiter) in 5.
        chart = {
            "planets_in_houses": {
                "Jupiter": {"house": 2},
                "Sun": {"house": 5},
                "Venus": {"house": 5}
            }
        }
        enriched = strength.calculate_chart_strengths(chart)
        # Inject the aspect into planets_in_houses (the schema detect_bilmukabil reads)
        # aspecting_planet = who aspects Jupiter
        chart["planets_in_houses"]["Jupiter"]["aspects"] = [
            {"aspecting_planet": "Sun", "aspect_type": "100 Percent", "relationship": "neutral"}
        ]
        
        grammar.apply_grammar_rules(chart, enriched)
        assert "Sun" in enriched["Jupiter"]["bilmukabil_hostile_to"]

    def test_dharmi_planet_negative(self, env_setup):
        """Jupiter in H10 (Debilitated) should NOT be tagged as Dharmi Planet."""
        cfg, grammar, strength, _ = env_setup
        chart = {"planets_in_houses": {"Jupiter": {"house": 10}}}
        enriched = strength.calculate_chart_strengths(chart)
        grammar.apply_grammar_rules(chart, enriched)
        assert enriched["Jupiter"].get("dharmi_status") != "Dharmi Planet"

    def test_sleeping_planet_and_house(self, env_setup):
        """Planet sleeps if no aspect hits it. House sleeps if unoccupied."""
        cfg, grammar, strength, _ = env_setup
        chart = {
            "planets_in_houses": {
                "Sun": {"house": 2} # Sun (Pakka 1) in 2, but no aspects
            }
        }
        enriched = strength.calculate_chart_strengths(chart)
        grammar.apply_grammar_rules(chart, enriched)
        
        assert enriched["Sun"]["sleeping_status"] == "Sleeping Planet"

    def test_sleeping_negative_aspect_exists(self, env_setup):
        """Planet should NOT be sleeping if an aspect hits its house."""
        cfg, grammar, strength, _ = env_setup
        # Jupiter in H4 (Pakka) aspects H10 (100% direct / Significant)
        # H10 only aspects H4 via 'General Condition' (Non-significant).
        chart = {
            "planets_in_houses": {
                "Sun": {"house": 10},
                "Jupiter": {"house": 4} 
            }
        }
        enriched = strength.calculate_chart_strengths(chart)
        grammar.apply_grammar_rules(chart, enriched)
        # Sun in H10 is hit by 100% aspect. Should NOT be sleeping.
        assert enriched["Sun"].get("sleeping_status") != "Sleeping Planet"

    def test_rules_engine_invocation(self, env_setup):
        """Verify that the RulesEngine correctly detects Rule-Hits from the DB."""
        cfg, _, _, rules_engine = env_setup
        
        # Scenario for RULE_SUN_H4
        chart = {
            "planets_in_houses": {
                "Sun": {"house": 4}
            }
        }
        context = UnifiedAstrologicalContext(enriched=EnrichedChart(source=chart))
        hits = rules_engine.evaluate_chart(context)
        hit_ids = [h.rule_id for h in hits]
        assert "RULE_SUN_H4" in hit_ids

        # Scenario for RULE_TAK_MOON_VEN (Confrontation)
        # We need aspects to trigger confrontation in RuleEngine
        chart_confront = {
            "planets_in_houses": {
                "Moon": {"house": 1, "aspects": [{"target": "Venus", "aspect_type": "100 Percent"}]},
                "Venus": {"house": 7}
            }
        }
        context_cf = UnifiedAstrologicalContext(enriched=EnrichedChart(source=chart_confront))
        hits_cf = rules_engine.evaluate_chart(context_cf)
        hit_ids_cf = [h.rule_id for h in hits_cf]
        assert "RULE_TAK_MOON_VEN" in hit_ids_cf

    def test_rules_engine_negative_mismatch(self, env_setup):
        """RulesEngine should NOT hit if conditions are nearly-met but different."""
        cfg, _, _, rules_engine = env_setup
        # Place Sun in House 5 (Rule is for House 4)
        chart = {"planets_in_houses": {"Sun": {"house": 5}}}
        context = UnifiedAstrologicalContext(enriched=EnrichedChart(source=chart))
        hits = rules_engine.evaluate_chart(context)
        hit_ids = [h.rule_id for h in hits]
        assert "RULE_SUN_H4" not in hit_ids
