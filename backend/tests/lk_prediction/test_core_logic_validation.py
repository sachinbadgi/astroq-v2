"""
Comprehensive Logic Validation Suite for Lal Kitab Engine.

This suite validates the core 'astrological truth' of the simplified engine, 
ensuring that critical grammar rules and strength modifiers are mathematically 
correct and grounded in canonical Lal Kitab theory.
"""

import pytest
import sqlite3
import json
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.grammar_analyser import GrammarAnalyser
from astroq.lk_prediction.strength_engine import StrengthEngine

@pytest.fixture
def tmp_db(tmp_path):
    db_path = tmp_path / "test_rules.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE deterministic_rules (id TEXT, condition TEXT, scoring_type TEXT, scale TEXT, domain TEXT, description TEXT, verdict TEXT, source_page TEXT, success_weight REAL)")
    conn.close()
    return str(db_path)

@pytest.fixture
def tmp_defaults(tmp_path):
    # Ensure all required weight keys are present to avoid fallback noise
    defaults = {
        "strength": {
            "natal": {
                "pakka_ghar": 2.2, 
                "exalted": 5.0, 
                "debilitated": -5.0,
                "fixed_house_lord": 1.5
            },
            "mangal_badh_divisor": 16.0,
            "kaayam_boost": 1.15,
            "dharmi_planet_boost": 1.5,
            "dharmi_kundli_boost": 1.2,
            "sleeping_planet_factor": 0.0,
            "sathi_boost_per_companion": 1.0,
            "bilmukabil_penalty_per_hostile": 1.5,
            "masnui_parent_feedback": 0.3,
            "dhoka_graha_factor": 0.7,
            "achanak_chot_penalty": 20.0
        }
    }
    path = tmp_path / "defaults.json"
    with open(path, "w") as f:
        json.dump(defaults, f)
    return str(path)

@pytest.fixture
def core_setup(tmp_db, tmp_defaults):
    cfg = ModelConfig(db_path=tmp_db, defaults_path=tmp_defaults)
    return cfg, GrammarAnalyser(cfg), StrengthEngine(cfg)

class TestCoreAstrologicalLogic:

    def test_mangal_badh_logic(self, core_setup):
        """Sun+Saturn conjunction triggers Mangal Badh Rule R1 and penalizes Mars."""
        cfg, grammar, strength = core_setup
        chart = {
            "planets_in_houses": {
                "Mars": {"house": 3}, # Mars Pakka Ghar (Strength > 0)
                "Sun": {"house": 10},
                "Saturn": {"house": 10} # Sun + Saturn = Mangal Badh R1 (Counter=1)
            },
            "chart_type": "Birth"
        }
        enriched = strength.calculate_chart_strengths(chart)
        grammar.apply_grammar_rules(chart, enriched)
        
        assert chart["mangal_badh_status"] == "Active"
        # Mars (H3) should have strength_total > 0 before Mangal Badh
        # and then a negative breakdown entry
        assert enriched["Mars"]["strength_breakdown"]["mangal_badh"] < 0

    def test_dharmi_teva_boost(self, core_setup):
        """Jupiter in H4 triggers individual Dharmi status (not kundli-level Dharmi Teva).
        Dharmi Teva (kundli-level) requires Saturn+Jupiter conjunction."""
        cfg, grammar, strength = core_setup
        chart = {
            "planets_in_houses": {
                "Jupiter": {"house": 4} 
            }
        }
        enriched = strength.calculate_chart_strengths(chart)
        grammar.apply_grammar_rules(chart, enriched)
        
        # Jupiter H4 is not Dharmi Teva (that needs Saturn+Jupiter conjunct)
        assert chart["dharmi_kundli_status"] != "Dharmi Teva"
        # But Jupiter does get individual dharmi status (Jupiter not in H10)
        assert enriched["Jupiter"]["dharmi_status"] != ""

    def test_scapegoat_transfer(self, core_setup):
        """If Saturn is malefic, its penalty should transfer to Rahu/Ketu/Venus."""
        cfg, grammar, strength = core_setup
        chart = {
            "planets_in_houses": {
                "Saturn": {"house": 1}, # Saturn in 1 (Debilitated -5)
                "Rahu": {"house": 10},
                "Ketu": {"house": 6},
                "Venus": {"house": 3}
            }
        }
        enriched = strength.calculate_chart_strengths(chart)
        
        saturn_adj = enriched["Saturn"].get("scapegoat_adjustment", 0)
        rahu_adj = enriched["Rahu"]["strength_breakdown"].get("scapegoat", 0)
        
        assert saturn_adj > 0
        assert rahu_adj < 0
        assert enriched["Saturn"]["strength_total"] == 0

    def test_achanak_chot_trigger(self, core_setup):
        """Sudden Strike triggered by H8/H10 pair and annual aspect."""
        cfg, grammar, strength = core_setup
        
        natal_chart = {
            "planets_in_houses": {
                "Mars": {"house": 8},
                "Saturn": {"house": 10} # {8, 10} is a strike pair
            }
        }
        
        annual_chart = {
            "planets_in_houses": {
                "Mars": {"house": 8},
                "Saturn": {"house": 2} # Annual Saturn in H2. H8 aspects H2 (25%).
            },
            "chart_type": "Yearly",
            "_mock_birth_chart": natal_chart
        }
        
        enriched = strength.calculate_chart_strengths(annual_chart)
        grammar.apply_grammar_rules(annual_chart, enriched)
        
        # Mars in H8 aspects Saturn in H2. 
        assert any(t["planets"][0] == "Mars" for t in annual_chart["achanak_chot_triggers"])

    def test_sleeping_planet_status(self, core_setup):
        """A planet sleeps if not in Pakka Ghar and no aspects are hitting another planet."""
        cfg, grammar, strength = core_setup
        chart = {
            "planets_in_houses": {
                "Sun": {"house": 2} # Sun Pakka Ghar is H1.
            }
        }
        enriched = strength.calculate_chart_strengths(chart)
        grammar.apply_grammar_rules(chart, enriched)
        
        # Sun in H2 sleeps if H6 is empty
        assert enriched["Sun"]["sleeping_status"] == "Sleeping Planet"
