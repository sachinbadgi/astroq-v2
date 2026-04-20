"""
Advanced Integrated Concepts Tests.

Validates complex interactions discovered in the wiki audit:
1. Scapegoat Redistribution (Negative strength propagation).
2. 35-Year Life Cycle Ruler Boost.
3. Masnui (Artificial) Conjunctions with multi-planet interference (issubset check).
"""

import pytest
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.grammar_analyser import GrammarAnalyser
from astroq.lk_prediction.strength_engine import StrengthEngine

@pytest.fixture
def integrated_suite(tmp_path):
    # Setup paths
    db_path = tmp_path / "rules_integrated.db"
    defaults_path = tmp_path / "defaults_integrated.json"
    
    import json
    with open(defaults_path, "w") as f:
        # Use FLAT keys per ModelConfig documentation
        json.dump({
            "strength.natal.pakka_ghar": 2.2,
            "strength.natal.exalted": 5.0,
            "strength.natal.debilitated": -5.0,
            "strength.cycle_35yr_boost": 1.25,
            "strength.masnui_parent_feedback": 0.3
        }, f)
        
    cfg = ModelConfig(db_path=str(db_path), defaults_path=str(defaults_path))
    return cfg, GrammarAnalyser(cfg), StrengthEngine(cfg)

class TestAdvancedIntegration:

    def test_scapegoat_redistribution_saturn(self, integrated_suite):
        """Saturn negative strength redistributes to Rahu(50%), Ketu(30%), Venus(20%)."""
        cfg, grammar, strength = integrated_suite
        # Saturn in H1 (Sun's house, Sun is enemy).
        # We'll artificially force negative strength via debilitation.
        # Saturn in H1 is debilitated -> -5.0.
        chart = {
            "chart_type": "Birth",
            "planets_in_houses": {
                "Saturn": {"house": 1},   # Debilitated (-5.0)
                "Rahu": {"house": 8},     # Neutral house
                "Ketu": {"house": 11},    # Neutral house
                "Venus": {"house": 12}    # Neutral house
            }
        }
        enriched = strength.calculate_chart_strengths(chart)
        print(f"\nDEBUG SCAPEGOAT BREAKDOWN SATURN: {enriched['Saturn']}")
        print(f"DEBUG SCAPEGOAT BREAKDOWN RAHU: {enriched['Rahu']}")
        
        # Saturn's total should be 0 (all redistributed)
        assert enriched["Saturn"]["strength_total"] == 0.0
        
        # Saturn total was -7.0 (-2 aspect, -5 dignity). 
        # Rahu gets 50% = -3.5. 
        # Rahu also has +0.5 aspect (Outside Help to Venus). Total = -3.0.
        assert enriched["Rahu"]["strength_total"] == -3.0
        # Ketu gets 30% = -2.1. 
        # Ketu (H11) also aspects friend Rahu (H8) -> +1.0 boost. Total = -1.1.
        assert enriched["Ketu"]["strength_total"] == -1.1
        # Venus gets 20% = -1.4.
        # Venus (H12) is Exalted (+5.0).
        # Venus (H12) also aspects Rahu (H8) -> +2.0 boost. 
        # Total = 5.0 + 2.0 - 1.4 = 5.6.
        assert enriched["Venus"]["strength_total"] == pytest.approx(5.6)

    def test_35_year_cycle_boost(self, integrated_suite):
        """Planet gets a 25% boost if it is the ruler of the 35-year cycle period."""
        cfg, grammar, strength = integrated_suite
        # Age 1 (Saturn rules Age 1-6)
        chart = {
            "chart_type": "Yearly",
            "chart_period": 1,
            "planets_in_houses": {
                "Saturn": {"house": 10} 
            }
        }
        
        enriched = strength.calculate_chart_strengths(chart)
        grammar.apply_grammar_rules(chart, enriched)
        
        # High-fidelity integrated total (Dignity 1.85 + Kaayam 0.277 - Dhoka 0.638 + 35yr 0.372)
        sat_total = enriched["Saturn"]["strength_total"]
        assert sat_total == pytest.approx(1.8615, abs=1e-3)
        # 35yr boost component should be present
        assert enriched["Saturn"]["strength_breakdown"]["cycle_35yr"] > 0

    def test_masnui_formation_with_interference(self, integrated_suite):
        """Masnui forms even if other planets are in the same house (subset check)."""
        cfg, grammar, strength = integrated_suite
        # Sun + Venus in H1 forms Artificial Jupiter.
        # We add Mercury to H1.
        chart = {
            "chart_type": "Birth",
            "planets_in_houses": {
                "Sun": {"house": 1},
                "Venus": {"house": 1},
                "Mercury": {"house": 1}
            }
        }
        
        # We haven't fixed the code yet, so this might FAIL initially.
        # Once we change '==' to 'issubset', it should PASS.
        # For now, let's keep it and see.
        enriched = strength.calculate_chart_strengths(chart)
        grammar.apply_grammar_rules(chart, enriched)
        
        # Check if Artificial Jupiter (or Masnui Jupiter) is in enriched
        masnui_keys = [k for k in enriched.keys() if "Artificial" in k or "Masnui" in k]
        assert any("Jupiter" in k for k in masnui_keys)
