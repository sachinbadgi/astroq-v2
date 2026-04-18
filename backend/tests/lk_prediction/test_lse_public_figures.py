"""
Public Figure Verification Tests for AutoResearch 2.0 (LSE).
Version 3.1: Authentic Lal Kitab Logic with Source Planet Disambiguation.

Demonstrates LSE discovery using canonical benchmarks (Sun=22, Saturn=36, etc.).
"""

import pytest
import json
from astroq.lk_prediction.lse_orchestrator import LSEOrchestrator
from astroq.lk_prediction.data_contracts import LKPrediction
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.rules_engine import RulesEngine


@pytest.fixture
def mock_cfg_and_engine(tmp_path):
    db_path = tmp_path / "test_rules.db"
    defaults_path = tmp_path / "test_defaults.json"
    with open(defaults_path, "w") as f:
        json.dump({}, f)
        
    cfg = ModelConfig(db_path=str(db_path), defaults_path=str(defaults_path))
    engine = RulesEngine(cfg)
    return cfg, engine


def test_lse_abraham_lincoln_authentic(mock_cfg_and_engine):
    """
    Abraham Lincoln:
    1. Career: Mars H8 vs Sun H1. Sun Bench=22. Actual Presidency=51. Gap=29.0
    2. Health: Saturn H4 (Snake in Water). Sat Bench=36. Actual Death=56. Gap=20.0
    """
    cfg, engine = mock_cfg_and_engine
    orchestrator = LSEOrchestrator(cfg)
    orchestrator.researcher.rules_engine = engine
    
def test_lse_abraham_lincoln_authentic(mock_cfg_and_engine):
    """
    Abraham Lincoln:
    1. Career: Mars H8 vs Sun H1. Sun Bench=22. Actual Presidency=51. Gap=29.0
    2. Health: Saturn H4 (Snake in Water). Sat Bench=36. Actual Death=56. Gap=20.0
    """
    cfg, engine = mock_cfg_and_engine
    orchestrator = LSEOrchestrator(cfg)
    orchestrator.researcher.rules_engine = engine
    
    def mock_run_pipeline(birth, annual, fig):
        # Mocks should return the BASELINE (22, 36) without delay
        return [
            LKPrediction(
                domain="Career", event_type="presidency", prediction_text="Presidency",
                peak_age=22, source_planets=["Sun"], confidence="certain", polarity="benefic"
            ),
            LKPrediction(
                domain="health", event_type="assassination", prediction_text="Death",
                peak_age=36, source_planets=["Saturn"], confidence="certain", polarity="malefic"
            )
        ]
    orchestrator._run_pipeline = mock_run_pipeline

    birth_chart = {
        "planets_in_houses": {
            "Sun": {"house": 1},
            "Mars": {"house": 8},
            "Saturn": {"house": 4},
        }
    }
    
    life_events = [
        {"age": 51.0, "domain": "Career", "description": "Presidency", "is_verified": True},
        {"age": 56.0, "domain": "health", "description": "Assassination", "is_verified": True}
    ]
    annual_charts = {51: birth_chart, 56: birth_chart}

    result = orchestrator.solve_chart(birth_chart, annual_charts, life_events, figure_id="lincoln")
    assert result.converged
    assert result.chart_dna.delay_constants.get("delay.sun_h1") == 29.0
    assert result.chart_dna.delay_constants.get("delay.saturn_h4") == 20.0


def test_lse_albert_einstein_authentic(mock_cfg_and_engine):
    """
    Albert Einstein:
    1. Career: Mars H8 vs Sun H1 (Ruthless Clash). Sun Bench=22. Actual Nobel=42. Gap=20.0
    2. Marriage: Venus H10 (Imaginary Saturn). Venus Bench=25. Actual Marriage=35. Gap=10.0
    """
    cfg, engine = mock_cfg_and_engine
    orchestrator = LSEOrchestrator(cfg)
    orchestrator.researcher.rules_engine = engine
    
    def mock_run_pipeline(birth, annual, fig):
        return [
            LKPrediction(
                domain="Career", event_type="nobel", peak_age=22, 
                source_planets=["Sun"], confidence="highly_likely", polarity="benefic", prediction_text="Nobel"
            ),
            LKPrediction(
                domain="marriage", event_type="m", peak_age=25, 
                source_planets=["Venus"], confidence="certain", polarity="mixed", prediction_text="Marriage"
            )
        ]
    orchestrator._run_pipeline = mock_run_pipeline

    birth_chart = {
        "planets_in_houses": {
            "Sun": {"house": 1},
            "Mars": {"house": 8},
            "Venus": {"house": 10},
        }
    }
    
    life_events = [
        {"age": 42.0, "domain": "Career", "description": "Nobel", "is_verified": True},
        {"age": 35.0, "domain": "marriage", "description": "Second Marriage", "is_verified": True}
    ]
    annual_charts = {42: birth_chart, 35: birth_chart}

    result = orchestrator.solve_chart(birth_chart, annual_charts, life_events, figure_id="einstein")
    assert result.converged
    assert result.chart_dna.delay_constants.get("delay.sun_h1") == 20.0
    assert result.chart_dna.milestone_alignments.get("align.venus_h10") == 36


def test_lse_gandhi_authentic(mock_cfg_and_engine):
    """
    Mahatma Gandhi:
    1. Career: Eclipsed Fortune (Jup + Rahu). Jup Bench=16. Actual Peak=40. Gap=24.0
    2. Health: Saturn H4 (Snake in Water). Sat Bench=36. Actual Death=79. Gap=43.0
    """
    cfg, engine = mock_cfg_and_engine
    orchestrator = LSEOrchestrator(cfg)
    orchestrator.researcher.rules_engine = engine
    
    def mock_run_pipeline(birth, annual, fig):
        return [
            LKPrediction(domain="Career", event_type="peak", peak_age=16, source_planets=["Jupiter"], confidence="highly_likely", polarity="benefic", prediction_text="Peak"),
            LKPrediction(domain="health", event_type="fatality", peak_age=36, source_planets=["Saturn"], confidence="certain", polarity="malefic", prediction_text="Death")
        ]
    orchestrator._run_pipeline = mock_run_pipeline

    birth_chart = {
        "planets_in_houses": {
            "Jupiter": {"house": 2},
            "Rahu": {"house": 2},
            "Saturn": {"house": 4},
        }
    }
    
    life_events = [
        {"age": 40.0, "domain": "Career", "description": "Peak", "is_verified": True},
        {"age": 79.0, "domain": "health", "description": "Assassination", "is_verified": True}
    ]
    annual_charts = {40: birth_chart, 79: birth_chart}

    result = orchestrator.solve_chart(birth_chart, annual_charts, life_events, figure_id="gandhi")
    assert result.converged
    assert result.chart_dna.milestone_alignments.get("align.jupiter_h2") == 42
    assert result.chart_dna.delay_constants.get("delay.saturn_h4") == 43.0


def test_lse_indira_gandhi_authentic(mock_cfg_and_engine):
    """
    Indira Gandhi:
    1. Career: Mars H8 vs Sun H1. 22 + Gap = 49. Gap=27.0
    2. Marriage: Mercury H9 (Malefic till 34). 34 + Gap = 25. Gap=-9.0
    """
    cfg, engine = mock_cfg_and_engine
    orchestrator = LSEOrchestrator(cfg)
    orchestrator.researcher.rules_engine = engine
    
    def mock_run_pipeline(birth, annual, fig):
        return [
            LKPrediction(domain="Career", event_type="pm", peak_age=22, source_planets=["Sun"], confidence="highly_likely", polarity="benefic", prediction_text="PM"),
            LKPrediction(domain="marriage", event_type="m", peak_age=34, source_planets=["Mercury"], confidence="certain", polarity="mixed", prediction_text="Marriage")
        ]
    orchestrator._run_pipeline = mock_run_pipeline

    birth_chart = {
        "planets_in_houses": {
            "Sun": {"house": 1},
            "Mars": {"house": 8},
            "Mercury": {"house": 9},
        }
    }
    
    life_events = [
        {"age": 49.0, "domain": "Career", "description": "PM", "is_verified": True},
        {"age": 25.0, "domain": "marriage", "description": "Marriage", "is_verified": True}
    ]
    annual_charts = {49: birth_chart, 25: birth_chart}

    result = orchestrator.solve_chart(birth_chart, annual_charts, life_events, figure_id="indira")
    assert result.converged
    assert result.chart_dna.delay_constants.get("delay.sun_h1") == 27.0
    assert result.chart_dna.delay_constants.get("delay.mercury_h9") == -9.0


def test_lse_elizabeth_ii_authentic(mock_cfg_and_engine):
    """
    Elizabeth II:
    1. Career: Soya Ghar H10. 36 + Gap = 26. Gap=-10.0
    2. Marriage: Venus H10. 25 + Gap = 21. Gap=-4.0
    """
    cfg, engine = mock_cfg_and_engine
    orchestrator = LSEOrchestrator(cfg)
    orchestrator.researcher.rules_engine = engine
    
    def mock_run_pipeline(birth, annual, fig):
        return [
            LKPrediction(domain="Career", event_type="coronation", peak_age=36, source_planets=["Saturn"], confidence="highly_likely", polarity="benefic", prediction_text="Coronation"),
            LKPrediction(domain="marriage", event_type="m", peak_age=25, source_planets=["Venus"], confidence="certain", polarity="benefic", prediction_text="Marriage")
        ]
    orchestrator._run_pipeline = mock_run_pipeline

    birth_chart = {
        "planets_in_houses": {
            "Saturn": {"house": 8},
            "Venus": {"house": 10},
            "Sun": {"house": 10},
        },
        "house_status": {"10": "Sleeping House"}
    }
    
    life_events = [
        {"age": 26.0, "domain": "Career", "description": "Coronation", "is_verified": True},
        {"age": 21.0, "domain": "marriage", "description": "Marriage", "is_verified": True}
    ]
    annual_charts = {26: birth_chart, 21: birth_chart}

    result = orchestrator.solve_chart(birth_chart, annual_charts, life_events, figure_id="qe2")
    assert result.converged
    assert result.chart_dna.delay_constants.get("delay.saturn_h10") == -10.0
    assert result.chart_dna.delay_constants.get("delay.venus_h10") == -4.0
