"""
Phase C: Integration tests for PredictionTranslator + RemedyEngine.
"""

from __future__ import annotations

import json
import sqlite3
import pytest
from pathlib import Path

from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.data_contracts import ClassifiedEvent, LKPrediction
from astroq.lk_prediction.prediction_translator import PredictionTranslator
from astroq.lk_prediction.remedy_engine import RemedyEngine, PlanetShiftingResult, ShiftingOption


class MockRemedyEngine:
    """Mock engine to test integration logic without complex chart setups."""
    def __init__(self, safe_options: list[ShiftingOption] = None):
        self.safe_options = safe_options or []
        
    def get_year_shifting_options(self, birth_chart, annual_chart, age):
        # We only return options for "Sun" in these tests
        return {
            "Sun": PlanetShiftingResult(
                planet="Sun",
                birth_house=1,
                annual_house=1,
                safe_matches=self.safe_options,
                other_options=[],
                conflicts={},
                llm_hint="Mock hint"
            ),
            "Moon": PlanetShiftingResult(
                planet="Moon",
                birth_house=2,
                annual_house=2,
                safe_matches=[],
                other_options=[],
                conflicts={},
                llm_hint="Mock hint"
            )
        }
        
    def generate_remedy_hints(self, year_options, chart=None):
        # Return exactly the hint formats checking the options
        hints = []
        for planet, res in year_options.items():
            for opt in res.safe_matches:
                hints.append(f"Shift {planet} to House {opt.house}")
        return hints[:3]


@pytest.fixture
def dummy_charts():
    return {"dummy": "birth"}, {"dummy": "annual"}


@pytest.fixture
def dummy_event():
    return ClassifiedEvent(
        planet="Sun",
        house=1,
        domains=["Career"],
        sentiment="MALEFIC",
        probability=0.9,
        magnitude=-5.0,
        is_peak=True,
        peak_type="ABSOLUTE",
        prediction_text="",
        peak_age=30
    )


def _make_translator(remedy_engine=None):
    from unittest.mock import MagicMock
    cfg = MagicMock()
    cfg.get.side_effect = lambda k, fallback=None: fallback
    return PredictionTranslator(cfg, remedy_engine=remedy_engine)


class TestPredictionTranslatorRemedyIntegration:

    def test_translator_populates_remedy_hints_when_safe_matches_exist(self, dummy_event, dummy_charts):
        """PredictionTranslator with RemedyEngine → LKPrediction.remedy_hints populated."""
        b_chart, a_chart = dummy_charts
        opt = ShiftingOption(house=5, score=60, rank="CRITICAL", rationale="test")
        mock_engine = MockRemedyEngine(safe_options=[opt])
        t = _make_translator(remedy_engine=mock_engine)
        
        preds = t.translate([dummy_event], enriched_natal=b_chart, enriched_annual=a_chart)
        p = preds[0]
        assert p.remedy_applicable is True
        assert len(p.remedy_hints) > 0
        assert "Shift Sun to House 5" in p.remedy_hints

    def test_translator_sets_remedy_applicable_false_when_no_safe_matches(self, dummy_event, dummy_charts):
        """No safe houses → remedy_applicable=False."""
        b_chart, a_chart = dummy_charts
        mock_engine = MockRemedyEngine(safe_options=[])  # Empty safe options
        t = _make_translator(remedy_engine=mock_engine)
        
        preds = t.translate([dummy_event], enriched_natal=b_chart, enriched_annual=a_chart)
        p = preds[0]
        assert p.remedy_applicable is False
        assert len(p.remedy_hints) == 0

    def test_translator_remedy_includes_planet_and_house(self, dummy_event, dummy_charts):
        """remedy_hints strings reference planet and house number."""
        b_chart, a_chart = dummy_charts
        opt = ShiftingOption(house=9, score=60, rank="CRITICAL", rationale="test")
        mock_engine = MockRemedyEngine(safe_options=[opt])
        t = _make_translator(remedy_engine=mock_engine)
        
        preds = t.translate([dummy_event], enriched_natal=b_chart, enriched_annual=a_chart)
        hint = preds[0].remedy_hints[0]
        assert "Sun" in hint
        assert "9" in hint

    def test_translator_remedy_hints_max_3_items(self, dummy_event, dummy_charts):
        """Even with many options, remedy_hints has at most 3 items."""
        b_chart, a_chart = dummy_charts
        # Create 5 options
        opts = [ShiftingOption(house=h, score=60, rank="CRITICAL", rationale="test") for h in range(1, 6)]
        mock_engine = MockRemedyEngine(safe_options=opts)
        t = _make_translator(remedy_engine=mock_engine)
        
        preds = t.translate([dummy_event], enriched_natal=b_chart, enriched_annual=a_chart)
        assert len(preds[0].remedy_hints) == 3

    def test_translator_without_remedy_engine_defaults_empty(self, dummy_event, dummy_charts):
        """PredictionTranslator(remedy_engine=None) safely falls back to standard hints."""
        b_chart, a_chart = dummy_charts
        # If no engine, it uses fallback strings for malefic
        t = _make_translator(remedy_engine=None)
        
        preds = t.translate([dummy_event], enriched_natal=b_chart, enriched_annual=a_chart)
        p = preds[0]
        # It IS applicable (since it's MALEFIC) but the hints are just generic 
        assert p.remedy_applicable is True
        assert "Lal Kitab remedy required for Sun" in p.remedy_hints[0]

    def test_translator_with_real_remedy_engine_and_wrapped_dicts(self, dummy_event):
        """Verifies the pipeline wrapper fix: Translation handles {'planets_in_houses': {...}} explicitly."""
        # Provide real config
        from astroq.lk_prediction.config import ModelConfig
        import os
        from unittest.mock import MagicMock
        cfg = MagicMock()
        # Make the stub config return appropriate values so we get a 'CRITICAL' score
        def _get_cfg(k, fallback=0):
            if "weight" in k: return 100
            if "threshold" in k: return 40
            return fallback
        cfg.get.side_effect = _get_cfg
        
        # Stub Resolver
        class FakeResolver:
            def get_planet_items(self, p, h):
                return ["Test Item"]
        
        real_engine = RemedyEngine(cfg, FakeResolver())
        t = PredictionTranslator(cfg, remedy_engine=real_engine)
        
        # The exact pipeline fix payload: wrapping dictionaries
        wrap_natal = {
            "planets_in_houses": {
                "Jupiter": {"house": 3, "strength_total": 5.0} # Note: House 9 is safe for Jupiter
            }
        }
        wrap_annual = {
            "planets_in_houses": {
                "Jupiter": {"house": 3, "strength_total": -5.0} # Needs remedy
            }
        }
        
        dummy_event.planet = "Jupiter"
        preds = t.translate([dummy_event], enriched_natal=wrap_natal, enriched_annual=wrap_annual)
        p = preds[0]
        
        assert p.remedy_applicable is True
        assert len(p.remedy_hints) > 0
        assert "Shift Jupiter" in p.remedy_hints[0]

