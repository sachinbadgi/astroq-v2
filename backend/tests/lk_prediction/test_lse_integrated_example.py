from unittest.mock import MagicMock, patch
from astroq.lk_prediction.lse_orchestrator import LSEOrchestrator
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.lse_chart_dna import ChartDNARepository
from astroq.lk_prediction.data_contracts import LKPrediction
import os

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

def test_worked_example_integration(tmp_path):
    """
    End-to-end test for the LSE loop using real components but mocked pipeline outcome.
    Verifies Orchestration -> Research -> Validation -> Persistence.
    """
    db_path = str(tmp_path / "api_config.db")
    defaults_path = str(tmp_path / "model_defaults.json")
    with open(defaults_path, "w") as f:
        import json
        json.dump({}, f)
    
    config = ModelConfig(db_path=db_path, defaults_path=defaults_path)
    orchestrator = LSEOrchestrator(config)
    repo = ChartDNARepository(db_path)
    
    # Chart: Sun in H1
    birth_chart = {"planets_in_houses": {"Sun": {"house": 1}}}
    
    # Event: Profession at 24
    life_events = [
        {"age": 24, "domain": "profession", "description": "Actual Profession Hit", "is_verified": True}
    ]
    
    # MOCK PIPELINE
    mock_pipeline = MagicMock()
    # Iteration 0: predict at 21. Iteration 1: predict at 24.5 (Hit)
    mock_pipeline.generate_predictions.side_effect = [
        [_make_lk(21, "profession", source_planets=["Sun"])],
        [_make_lk(24.5, "profession", source_planets=["Sun"])]
    ]
    
    # MOCK RESEARCHER to return the worked example hypothesis
    mock_researcher = MagicMock()
    mock_researcher.generate_hypotheses.return_value = [
        {"type": "Delay", "key": "delay.sun_h1", "value": 2.5, "rationale": "LSE Spec"}
    ]
    mock_researcher.rank_hypotheses.side_effect = lambda x: x
    orchestrator.researcher = mock_researcher

    with patch("astroq.lk_prediction.lse_orchestrator.LKPredictionPipeline", return_value=mock_pipeline):
        result = orchestrator.solve_chart(
            birth_chart=birth_chart,
            annual_charts={24: {}},
            life_event_log=life_events,
            figure_id="integrated_success_test"
        )
    
        # 1. Verify Convergence
        assert result.converged is True
        assert result.iterations_run == 1
        assert result.chart_dna.back_test_hit_rate == 1.0
        assert result.chart_dna.delay_constants.get("delay.sun_h1") == 2.5
        
        # 2. Verify Persistence
        repo.save(result.chart_dna)
        loaded = repo.load("integrated_success_test")
        assert loaded is not None
        assert loaded.back_test_hit_rate == 1.0
        assert loaded.delay_constants.get("delay.sun_h1") == 2.5
        
        print("Integration Test Passed: System converged and DNA persisted.")
