"""
Tests for Module 7: Prediction Translator.

Tests the mapping from raw RuleHit objects to human-readable LKPrediction contracts.
"""

import pytest
from astroq.lk_prediction.data_contracts import RuleHit, LKPrediction

class TestPredictionTranslator:

    def _make_translator(self, tmp_db, tmp_defaults):
        from astroq.lk_prediction.config import ModelConfig
        from astroq.lk_prediction.prediction_translator import PredictionTranslator
        cfg = ModelConfig(db_path=tmp_db, defaults_path=tmp_defaults)
        return PredictionTranslator(cfg)

    # -- 1. Magnitude Sensitivity --
    def test_translate_magnitude_reflects_strength(self, tmp_db, tmp_defaults):
        """Magnitude should be preserved in the translated prediction."""
        t = self._make_translator(tmp_db, tmp_defaults)
        hit = RuleHit(
            rule_id="R1", domain="Career", description="Sun in 10", 
            verdict="Benefic", magnitude=8.5, scoring_type="boost",
            primary_target_planets=["Sun"], target_houses=[10]
        )
        preds = t.translate([hit])
        assert preds[0].magnitude == 8.5

    # -- 2. Entity Resolution (People & Items) --
    def test_resolve_affected_people_from_planet(self, tmp_db, tmp_defaults):
        """Sun targets Self/Father, Moon targets Mother, etc."""
        t = self._make_translator(tmp_db, tmp_defaults)
        hit = RuleHit(
            rule_id="R1", domain="Career", description="Sun in 10", 
            verdict="Benefic", magnitude=5.0, scoring_type="boost",
            primary_target_planets=["Sun"], target_houses=[10]
        )
        preds = t.translate([hit])
        people = preds[0].affected_people
        assert "Self" in people or "Father" in people
        
    def test_resolve_affected_items_from_house(self, tmp_db, tmp_defaults):
        """House 4 targets Property/Vehicles."""
        t = self._make_translator(tmp_db, tmp_defaults)
        hit = RuleHit(
            rule_id="R1", domain="Home", description="Venus in 4", 
            verdict="Benefic", magnitude=5.0, scoring_type="boost",
            primary_target_planets=["Venus"], target_houses=[4]
        )
        preds = t.translate([hit])
        items = preds[0].affected_items
        assert "Property" in items or "Vehicles" in items or "Home" in items

    # -- 3. Remedy Generation --
    def test_remedy_hints_generated_for_malefic_hits(self, tmp_db, tmp_defaults):
        """Malefic hits should trigger remedy suggestions."""
        t = self._make_translator(tmp_db, tmp_defaults)
        hit = RuleHit(
            rule_id="R1", domain="Health", description="Saturn in 8", 
            verdict="Malefic", magnitude=-8.0, scoring_type="penalty",
            primary_target_planets=["Saturn"], target_houses=[8]
        )
        preds = t.translate([hit])
        assert preds[0].remedy_applicable is True
        assert len(preds[0].remedy_hints) > 0
        assert any("Saturn" in h for h in preds[0].remedy_hints)

    # -- 4. Text Synthesis --
    def test_generate_text_combines_description_and_verdict(self, tmp_db, tmp_defaults):
        t = self._make_translator(tmp_db, tmp_defaults)
        hit = RuleHit(
            rule_id="R1", domain="Self", description="Mars in 1", 
            verdict="Strong physical energy.", magnitude=5.0, scoring_type="boost",
            primary_target_planets=["Mars"], target_houses=[1]
        )
        preds = t.translate([hit])
        text = preds[0].prediction_text
        assert "Mars in 1" in text
        assert "Strong physical energy." in text

    # -- 5. Pipeline Translation --
    def test_translate_creates_lkprediction_standard_contract(self, tmp_db, tmp_defaults):
        t = self._make_translator(tmp_db, tmp_defaults)
        hit = RuleHit(
            rule_id="R1", domain="Marriage", description="Venus in 7", 
            verdict="Good prospects", magnitude=6.5, scoring_type="boost",
            primary_target_planets=["Venus"], target_houses=[7]
        )
        
        preds = t.translate([hit])
        assert len(preds) == 1
        
        p = preds[0]
        assert isinstance(p, LKPrediction)
        assert p.domain == "Marriage"
        assert p.polarity == "BENEFIC"
        assert p.magnitude == 6.5
        assert "Venus" in p.source_planets
        assert 7 in p.source_houses
