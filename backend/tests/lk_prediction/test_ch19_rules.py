"""
Tests for Lal Kitab Chapter 19: Health and Diseases.
Following TDD approach: Write tests FIRST.
"""

import pytest
from astroq.lk_prediction.data_contracts import ChartData

class TestChapter19Rules:

    @pytest.fixture
    def rules_engine(self, tmp_db, tmp_defaults):
        import sys
        import os
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
        
        from astroq.lk_prediction.config import ModelConfig
        from astroq.lk_prediction.rules_engine import RulesEngine
        from scripts.add_gosvami_ch19_rules import seed_ch19_health_rules
        
        # Seed the rules into the temporary test database
        seed_ch19_health_rules(target_db=tmp_db)
        
        cfg = ModelConfig(db_path=tmp_db, defaults_path=tmp_defaults)
        return RulesEngine(cfg)

    @pytest.fixture
    def sample_chart(self) -> ChartData:
        return {
            "chart_type": "Birth",
            "chart_period": 0,
            "planets_in_houses": {
                "Sun": {"house": 1, "states": [], "aspects": [], "strength_total": 5.0},
                "Moon": {"house": 4, "states": [], "aspects": [], "strength_total": 5.0},
                "Mars": {"house": 3, "states": [], "aspects": [], "strength_total": 5.0},
                "Mercury": {"house": 7, "states": [], "aspects": [], "strength_total": 5.0},
                "Jupiter": {"house": 2, "states": [], "aspects": [], "strength_total": 5.0},
                "Venus": {"house": 7, "states": [], "aspects": [], "strength_total": 5.0},
                "Saturn": {"house": 10, "states": [], "aspects": [], "strength_total": 5.0},
                "Rahu": {"house": 12, "states": [], "aspects": [], "strength_total": 5.0},
                "Ketu": {"house": 6, "states": [], "aspects": [], "strength_total": 5.0}
            }
        }

    def test_asthma_rule_triggers(self, rules_engine, sample_chart):
        """Rule: Sun and Saturn in H1 (or together) -> Respiratory issues."""
        sample_chart["planets_in_houses"]["Sun"]["house"] = 1
        sample_chart["planets_in_houses"]["Saturn"]["house"] = 1
        
        # We expect a rule with ID starting with LK_GOSW_CH19_HEALTH_ASTHMA
        hits = rules_engine.evaluate_chart(sample_chart)
        astro_hits = [h for h in hits if "ASTHMA" in h.rule_id]
        
        assert len(astro_hits) > 0
        assert "respiratory" in astro_hits[0].description.lower() or "asthma" in astro_hits[0].description.lower()

    def test_blind_chart_eyesight_rule(self, rules_engine, sample_chart):
        """Rule: Sun in H4, Saturn in H10 (100% aspect) -> Weak eyesight."""
        # Andha Teva often defined as Sun in 4, Saturn in 7 or vice versa, or mutual aspects
        sample_chart["planets_in_houses"]["Sun"]["house"] = 4
        sample_chart["planets_in_houses"]["Saturn"]["house"] = 10
        
        hits = rules_engine.evaluate_chart(sample_chart)
        eye_hits = [h for h in hits if "EYESIGHT" in h.rule_id or "BLIND" in h.rule_id]
        
        assert len(eye_hits) > 0
        assert "eyesight" in eye_hits[0].description.lower()

    def test_skin_disease_mercury_rahu_h6(self, rules_engine, sample_chart):
        """Rule: Mercury and Rahu in H6 -> Skin related problems."""
        sample_chart["planets_in_houses"]["Mercury"]["house"] = 6
        sample_chart["planets_in_houses"]["Rahu"]["house"] = 6
        
        hits = rules_engine.evaluate_rules(sample_chart)
        skin_hits = [h for h in hits if "SKIN" in h.rule_id]
        
        assert len(skin_hits) > 0
        assert "skin" in skin_hits[0].description.lower()
