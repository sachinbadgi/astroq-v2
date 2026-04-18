"""
Phase 4 Tests: LSE Orchestrator (AutoResearch 2.0)

Tests for: LSEOrchestrator, solve_chart loop, convergence, worked example.
"""

import pytest
from unittest.mock import MagicMock, patch
from astroq.lk_prediction.lse_orchestrator import LSEOrchestrator
from astroq.lk_prediction.data_contracts import (
    ChartData,
    LifeEventLog,
    LKPrediction,
    LSESolveResult,
    ChartDNA
)
from astroq.lk_prediction.config import ModelConfig


@pytest.fixture
def mock_config():
    config = MagicMock(spec=ModelConfig)
    config.get.return_value = 0.0
    config._db_path = "mock.db"
    return config


@pytest.fixture
def orchestrator(mock_config):
    return LSEOrchestrator(mock_config)


def _make_lk(age: int, domain: str, source_planets: list[str] = None) -> LKPrediction:
    return LKPrediction(
        domain=domain,
        event_type="test",
        prediction_text="Event text",
        confidence="possible",
        polarity="benefic",
        peak_age=age,
        probability=0.8,
        source_planets=source_planets or ["Sun"]
    )


def _make_le(age: int, domain: str) -> dict:
    return {
        "age": age,
        "domain": domain,
        "description": f"Known {domain} event",
        "is_verified": True
    }


# --------------------------------------------------------------------------
# Test 1: Orchestrator converges on a simple delay
# --------------------------------------------------------------------------

def test_orchestrator_converges_on_delay(orchestrator, mock_config):
    # Birth chart
    birth_chart: ChartData = {"planets_in_houses": {"Sun": {"house": 1}}}
    annual_charts = {24: {"chart_type": "Yearly", "chart_period": 24, "planets_in_houses": {}}}
    
    # Life events: Profession at 24
    life_events = [_make_le(24, "profession")]

    # Mock Pipeline
    mock_pipeline = MagicMock()
    mock_pipeline.generate_predictions.side_effect = [
        [_make_lk(21, "profession")], # Iteration 0 (Initial)
        [_make_lk(24, "profession")]  # Iteration 1 (After Delay hypothesis)
    ]
    
    # Inject Mock Researcher
    mock_researcher = MagicMock()
    mock_researcher.generate_hypotheses.return_value = [
        {"type": "Delay", "key": "delay.sun_h1", "value": 2.0, "rationale": "Test"}
    ]
    mock_researcher.rank_hypotheses.side_effect = lambda x: x
    orchestrator.researcher = mock_researcher
    
    with patch("astroq.lk_prediction.lse_orchestrator.LKPredictionPipeline", return_value=mock_pipeline):
        result = orchestrator.solve_chart(
            birth_chart=birth_chart,
            annual_charts=annual_charts,
            life_event_log=life_events,
            figure_id="test_figure"
        )
        
        assert result.converged is True
        assert result.iterations_run == 1
        assert result.chart_dna.back_test_hit_rate == 1.0
        assert result.chart_dna.delay_constants.get("delay.sun_h1") == 2.0


# --------------------------------------------------------------------------
# Test 2: Orchestrator stops at max_iterations
# --------------------------------------------------------------------------

def test_orchestrator_iteration_cap(orchestrator, mock_config):
    birth_chart: ChartData = {"planets_in_houses": {"Sun": {"house": 1}}}
    annual_charts = {24: {"planets_in_houses": {}}}
    life_events = [_make_le(24, "profession")]

    mock_pipeline = MagicMock()
    # Return a prediction that will NEVER match the life event (24) even with delay (18+2=20 -> abs=4)
    mock_pipeline.generate_predictions.return_value = [_make_lk(18, "profession", source_planets=["Sun"])]
    
    mock_researcher = MagicMock()
    mock_researcher.generate_hypotheses.return_value = [
        {"type": "Delay", "key": "delay.sun_h1", "value": 2.0, "rationale": "Test"}
    ]
    mock_researcher.rank_hypotheses.side_effect = lambda x: x
    orchestrator.researcher = mock_researcher

    with patch("astroq.lk_prediction.lse_orchestrator.LKPredictionPipeline", return_value=mock_pipeline):
        result = orchestrator.solve_chart(
            birth_chart=birth_chart,
            annual_charts=annual_charts,
            life_event_log=life_events,
            figure_id="test_figure",
            max_iterations=5
        )
        
        assert result.converged is False
        assert result.iterations_run == 5


# --------------------------------------------------------------------------
# Test 3: Zero Life Events returns generic result
# --------------------------------------------------------------------------

def test_orchestrator_zero_events(orchestrator, mock_config):
    birth_chart: ChartData = {"planets_in_houses": {}}
    annual_charts = {20: {}}
    
    mock_pipeline = MagicMock()
    mock_pipeline.generate_predictions.return_value = [_make_lk(20, "education")]
    
    with patch("astroq.lk_prediction.lse_orchestrator.LKPredictionPipeline", return_value=mock_pipeline):
        result = orchestrator.solve_chart(
            birth_chart=birth_chart,
            annual_charts=annual_charts,
            life_event_log=[],
            figure_id="test_figure"
        )
        
        assert result.iterations_run == 0
        assert len(result.future_predictions) == 1
        assert result.future_predictions[0].confidence_source == "generic"


# --------------------------------------------------------------------------
# Test 4: Worked Example Logic (Mocked convergence)
# --------------------------------------------------------------------------

def test_orchestrator_worked_example_path(orchestrator, mock_config):
    birth_chart: ChartData = {"planets_in_houses": {"Mars": {"house": 8}}}
    annual_charts = {24: {}}
    life_events = [_make_le(24, "profession")]

    mock_pipeline = MagicMock()
    mock_pipeline.generate_predictions.side_effect = [
        [_make_lk(21, "profession", source_planets=["Mars"])],   # Baseline
        [_make_lk(24.5, "profession", source_planets=["Mars"])]  # After Mars H8 delay
    ]
    
    mock_researcher = MagicMock()
    mock_researcher.generate_hypotheses.return_value = [
        {"type": "Delay", "key": "delay.mars_h8_delay_constant", "value": 2.5, "rationale": "LSE Spec"}
    ]
    mock_researcher.rank_hypotheses.side_effect = lambda x: x
    orchestrator.researcher = mock_researcher

    with patch("astroq.lk_prediction.lse_orchestrator.LKPredictionPipeline", return_value=mock_pipeline):
        result = orchestrator.solve_chart(
            birth_chart=birth_chart,
            annual_charts=annual_charts,
            life_event_log=life_events,
            figure_id="worked_example"
        )
        
        assert result.converged is True
        assert result.chart_dna.delay_constants.get("delay.mars_h8_delay_constant") == 2.5
        assert result.future_predictions[0].confidence_source == "back_test_100pct"
