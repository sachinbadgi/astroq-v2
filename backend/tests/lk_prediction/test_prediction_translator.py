"""
Tests for Module 7: Prediction Translator.

Tests written FIRST (TDD Red phase) — 11 unit tests covering
confidence mapping, agent/item resolution, text generation,
and the full translation pipeline to LKPrediction.
"""

import pytest

from astroq.lk_prediction.data_contracts import ClassifiedEvent, LKPrediction

class TestPredictionTranslator:

    def _make_translator(self, tmp_db, tmp_defaults):
        from astroq.lk_prediction.config import ModelConfig
        from astroq.lk_prediction.prediction_translator import PredictionTranslator
        cfg = ModelConfig(db_path=tmp_db, defaults_path=tmp_defaults)
        return PredictionTranslator(cfg)

    # -- 1. Confidence Mapping --
    def test_map_confidence_certain(self, tmp_db, tmp_defaults):
        """Probability > 0.85 should map to CERTAIN."""
        t = self._make_translator(tmp_db, tmp_defaults)
        assert t._map_confidence(0.90) == "CERTAIN"

    def test_map_confidence_highly_likely(self, tmp_db, tmp_defaults):
        t = self._make_translator(tmp_db, tmp_defaults)
        assert t._map_confidence(0.75) == "HIGHLY_LIKELY"

    def test_map_confidence_possible(self, tmp_db, tmp_defaults):
        t = self._make_translator(tmp_db, tmp_defaults)
        assert t._map_confidence(0.50) == "POSSIBLE"
        
    def test_map_confidence_unlikely(self, tmp_db, tmp_defaults):
        t = self._make_translator(tmp_db, tmp_defaults)
        assert t._map_confidence(0.20) == "UNLIKELY"

    # -- 2. Entity Resolution (People & Items) --
    def test_resolve_affected_people_from_planet(self, tmp_db, tmp_defaults):
        """Sun targets Self/Father, Moon targets Mother, etc."""
        t = self._make_translator(tmp_db, tmp_defaults)
        ev = ClassifiedEvent(
            planet="Sun", house=10, domains=["Career"], sentiment="BENEFIC",
            probability=0.9, magnitude=5.0, is_peak=True, peak_type="ABSOLUTE", prediction_text=""
        )
        people = t._resolve_affected_people(ev)
        assert "Self" in people or "Father" in people
        
    def test_resolve_affected_items_from_house(self, tmp_db, tmp_defaults):
        """House 4 targets Property/Vehicles."""
        t = self._make_translator(tmp_db, tmp_defaults)
        ev = ClassifiedEvent(
            planet="Venus", house=4, domains=["Home"], sentiment="BENEFIC",
            probability=0.9, magnitude=5.0, is_peak=True, peak_type="ABSOLUTE", prediction_text=""
        )
        items = t._resolve_affected_items(ev)
        assert "Property" in items or "Vehicles" in items or "Home" in items

    # -- 3. Remedy Generation --
    def test_remedy_hints_generated_for_malefic_events(self, tmp_db, tmp_defaults):
        """Malefic events should trigger remedy suggestions."""
        t = self._make_translator(tmp_db, tmp_defaults)
        ev = ClassifiedEvent(
            planet="Saturn", house=8, domains=["Health"], sentiment="MALEFIC",
            probability=0.9, magnitude=-8.0, is_peak=True, peak_type="ABSOLUTE", prediction_text=""
        )
        needs_remedy, hints = t._generate_remedies(ev)
        assert needs_remedy is True
        assert len(hints) > 0
        assert any("Saturn" in h for h in hints) or any("House 8" in h for h in hints)

    def test_no_remedy_needed_for_benefic_events(self, tmp_db, tmp_defaults):
        t = self._make_translator(tmp_db, tmp_defaults)
        ev = ClassifiedEvent(
            planet="Jupiter", house=9, domains=["Fortune"], sentiment="BENEFIC",
            probability=0.9, magnitude=8.0, is_peak=True, peak_type="ABSOLUTE", prediction_text=""
        )
        needs_remedy, hints = t._generate_remedies(ev)
        assert needs_remedy is False
        assert len(hints) == 0

    # -- 4. Text Generation --
    def test_generate_prediction_text_uses_rule_desc_if_present(self, tmp_db, tmp_defaults):
        t = self._make_translator(tmp_db, tmp_defaults)
        ev = ClassifiedEvent(
            planet="Mars", house=1, domains=["Self"], sentiment="MALEFIC",
            probability=0.9, magnitude=-5.0, is_peak=True, peak_type="ABSOLUTE",
            prediction_text="Manglik rule matched exactly."
        )
        text = t._generate_text(ev)
        assert "Manglik rule matched exactly." in text

    def test_generate_prediction_text_fallback_generation(self, tmp_db, tmp_defaults):
        """If no rule description, generate a smart fallback text."""
        t = self._make_translator(tmp_db, tmp_defaults)
        ev = ClassifiedEvent(
            planet="Mars", house=1, domains=["Self"], sentiment="MALEFIC",
            probability=0.9, magnitude=-5.0, is_peak=True, peak_type="ABSOLUTE",
            prediction_text="" # Empty
        )
        text = t._generate_text(ev)
        assert "Mars" in text
        assert "House 1" in text or "Self" in text
        assert "malefic" in text.lower() or "challenging" in text.lower() or "negative" in text.lower()

    # -- 5. Pipeline Translation --
    def test_translate_event_creates_lkprediction_contract(self, tmp_db, tmp_defaults):
        t = self._make_translator(tmp_db, tmp_defaults)
        ev = ClassifiedEvent(
            planet="Venus", house=7, domains=["Marriage"], sentiment="BENEFIC",
            probability=0.88, magnitude=6.5, is_peak=True, peak_type="MOMENTUM",
            prediction_text="Excellent marriage prospects", peak_age=25
        )
        
        preds = t.translate([ev])
        assert len(preds) == 1
        
        p = preds[0]
        assert isinstance(p, LKPrediction)
        assert p.domain == "Marriage"
        assert p.polarity == "BENEFIC"
        assert p.confidence == "CERTAIN"
        assert p.peak_age == 25
        assert p.probability == 0.88
        assert p.remedy_applicable is False
        assert "Venus" in p.source_planets
        assert 7 in p.source_houses
