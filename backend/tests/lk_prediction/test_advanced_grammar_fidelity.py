"""
Advanced Grammar Fidelity Tests.

Validates complex structural concepts from the 1952 edition:
1. Nagrik/Nashtik Kundli classifications.
2. Nikami (Inert) planet status.
3. Multi-condition Dharmi status (Rahu H4, Saturn H11, Jup+Sat conjunction).
"""

import pytest
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.grammar_analyser import GrammarAnalyser
from astroq.lk_prediction.strength_engine import StrengthEngine

@pytest.fixture
def grammar_suite(tmp_path):
    # Setup paths
    db_path = tmp_path / "rules_fidelity.db"
    defaults_path = tmp_path / "defaults_fidelity.json"
    
    import json
    with open(defaults_path, "w") as f:
        json.dump({
            "strength": {
                "mangal_badh_divisor": 16.0, 
                "masnui_parent_feedback": 0.3,
            }
        }, f)
        
    cfg = ModelConfig(db_path=str(db_path), defaults_path=str(defaults_path))
    return cfg, GrammarAnalyser(cfg), StrengthEngine(cfg)

class TestGrammarFidelity:

    def test_nagrik_kundli_detection(self, grammar_suite):
        """Nagrik Kundli: All planets in H1 to H6."""
        cfg, grammar, strength = grammar_suite
        chart = {
            "planets_in_houses": {
                "Sun": {"house": 1},
                "Moon": {"house": 4},
                "Jupiter": {"house": 2}
            }
        }
        enriched = strength.calculate_chart_strengths(chart)
        grammar.apply_grammar_rules(chart, enriched)
        
        assert chart["structural_type"] == "Nagrik (Active/Self)"

    def test_nashtik_kundli_detection(self, grammar_suite):
        """Nashtik Kundli: All planets in H7 to H12."""
        cfg, grammar, strength = grammar_suite
        chart = {
            "planets_in_houses": {
                "Sun": {"house": 7},
                "Moon": {"house": 9},
                "Jupiter": {"house": 12}
            }
        }
        enriched = strength.calculate_chart_strengths(chart)
        grammar.apply_grammar_rules(chart, enriched)
        
        assert chart["structural_type"] == "Nashtik (Passive/Social)"

    def test_nikami_planet_detection(self, grammar_suite):
        """Nikami: Planet in enemy house AND 7th house empty."""
        cfg, grammar, strength = grammar_suite
        # Venus in H1 (Sun's Pakka Ghar). Sun is enemy of Venus.
        # 7th house from H1 is H7.
        chart = {
            "planets_in_houses": {
                "Venus": {"house": 1},
                "Mercury": {"house": 2} # Not in H7
            }
        }
        enriched = strength.calculate_chart_strengths(chart)
        grammar.apply_grammar_rules(chart, enriched)
        
        # Venus should be Nikami
        assert enriched["Venus"].get("is_nikami") is True
        
        # Negative test: Mercury in H2 (Jupiter's house). Jupiter is Friend of Mercury.
        # Should NOT be Nikami even if H8 is empty.
        assert enriched["Mercury"].get("is_nikami") is False

    def test_expanded_dharmi_logic(self, grammar_suite):
        """Verifies Rahu H4, Saturn H11, and Jup+Sat conjunction triggers."""
        cfg, grammar, strength = grammar_suite
        
        # 1. Rahu in H4
        chart_rahu = {"planets_in_houses": {"Rahu": {"house": 4}}}
        enr_rahu = strength.calculate_chart_strengths(chart_rahu)
        grammar.apply_grammar_rules(chart_rahu, enr_rahu)
        assert "Dharmi Rahu" in enr_rahu["Rahu"]["dharmi_status"]
        
        # 2. Saturn in H11
        chart_sat = {"planets_in_houses": {"Saturn": {"house": 11}}}
        enr_sat = strength.calculate_chart_strengths(chart_sat)
        grammar.apply_grammar_rules(chart_sat, enr_sat)
        assert "Dharmi Saturn" in enr_sat["Saturn"]["dharmi_status"]
        
        # 3. Jup + Sat Conjunction — triggers kundli-level "Dharmi Teva"
        chart_conj = {"planets_in_houses": {"Jupiter": {"house": 5}, "Saturn": {"house": 5}}}
        enr_conj = strength.calculate_chart_strengths(chart_conj)
        grammar.apply_grammar_rules(chart_conj, enr_conj)
        # Kundli-level Dharmi Teva takes priority over individual planet granular labels
        assert enr_conj["Jupiter"]["dharmi_status"] == "Dharmi Teva"
        assert enr_conj["Saturn"]["dharmi_status"] == "Dharmi Teva"
