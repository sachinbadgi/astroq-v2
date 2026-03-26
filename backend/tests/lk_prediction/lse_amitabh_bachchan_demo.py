"""
LSE Demonstration: Amitabh Bachchan
Shows start-to-finish processing of a public figure chart.
"""

import os
import sys

# Ensure backend is in path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from astroq.lk_prediction.lse_orchestrator import LSEOrchestrator
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.data_contracts import LifeEvent

def run_amitabh_demo():
    print("=== AutoResearch 2.0 (LSE) Demo: Amitabh Bachchan ===")
    
    # 1. Setup Config
    project_root = os.getcwd()
    db_path = os.path.join(project_root, "backend/data/api_config.db")
    defaults_path = os.path.join(project_root, "backend/data/model_defaults.json")
    
    config = ModelConfig(db_path=db_path, defaults_path=defaults_path)
    orchestrator = LSEOrchestrator(config)
    
    # 2. Input Data (Amitabh Bachchan)
    # Sun in H7, Moon in H1, Jupiter in H4, etc.
    birth_chart = {
        "planets_in_houses": {
            "Sun": {"house": 7},
            "Moon": {"house": 1},
            "Mercury": {"house": 8},
            "Venus": {"house": 8},
            "Mars": {"house": 8},
            "Jupiter": {"house": 4},
            "Saturn": {"house": 2},
            "Rahu": {"house": 7},
            "Ketu": {"house": 1}
        }
    }
    
    # Life Events from ground truth
    life_events = [
        {"age": 31, "domain": "career", "description": "Zanjeer (Stardom)", "is_verified": True},
        {"age": 40, "domain": "health", "description": "Coolie accident", "is_verified": True}
    ]
    
    # Annual charts (Simplified for demo - normally generated)
    annual_charts = {age: {"chart_type": "Yearly", "chart_period": age, "planets_in_houses": {}} for age in [31, 40]}
    
    # 3. Solve Chart
    print(f"Starting LSE solve for figure: Amitabh Bachchan...")
    
    # MOCK PIPELINE to simulate baseline gaps for demonstration
    from unittest.mock import patch, MagicMock
    from astroq.lk_prediction.data_contracts import LKPrediction

    def _make_lk(age: float, domain: str, text: str) -> LKPrediction:
        return LKPrediction(
            domain=domain, event_type="test", prediction_text=text,
            confidence="possible", polarity="benefic", peak_age=age, probability=0.8
        )

    mock_pipeline = MagicMock()
    
    # Track iterations manually for the mock
    state = {"iter": 0}
    
    def side_effect_fn(chart):
        age = chart.get("chart_period", 0)
        it = state["iter"]
        if it == 0:
            if age == 31: return [_make_lk(27, "career", "Career peak")]
            if age == 40: return [_make_lk(38, "health", "Health issue")]
        else:
            # After delays applied
            if age == 31: return [_make_lk(31, "career", "Career peak")]
            if age == 40: return [_make_lk(40, "health", "Health issue")]
        return []

    mock_pipeline.generate_predictions.side_effect = side_effect_fn
    
    # We also need to increment the iteration state when the pipeline is 're-run'
    # The orchestrator re-instantiates or re-runs. 
    # In my implementation, solve_chart re-runs the loop.
    # To catch the 'next iteration', we can hook into Researcher or just check the config.
    
    # Researcher mock to return the fix on first miss
    mock_researcher = MagicMock()
    mock_researcher.generate_hypotheses.side_effect = [
        [{"type": "Delay", "key": "delay.saturn_h2", "value": 4.0, "rationale": "Aligning Zanjeer"}], # it 0
        [] # it 1
    ]
    mock_researcher.rank_hypotheses.side_effect = lambda x: x
    orchestrator.researcher = mock_researcher

    # Wrapper to switch mock state after first run
    original_solve = orchestrator._run_pipeline
    def run_pipeline_spy(*args, **kwargs):
        res = original_solve(*args, **kwargs)
        state["iter"] += 1
        return res
    
    with patch("astroq.lk_prediction.lse_orchestrator.LKPredictionPipeline", return_value=mock_pipeline):
        # We also need to mock orchestrator's _run_pipeline to increment state
        with patch.object(orchestrator, "_run_pipeline", side_effect=run_pipeline_spy):
            result = orchestrator.solve_chart(
                birth_chart=birth_chart,
                annual_charts=annual_charts,
                life_event_log=life_events,
                figure_id="amitabh_bachchan_demo"
            )
    
    # 4. Report Results
    print("\n--- LSE Results ---")
    print(f"Converged: {result.converged}")
    print(f"Iterations: {result.iterations_run}")
    print(f"Final Hit Rate: {result.chart_dna.back_test_hit_rate * 100:.1f}%")
    print(f"Mean Offset: {result.chart_dna.mean_offset_years:.2f} years")
    print(f"Confidence Score: {result.chart_dna.confidence_score:.2f}")
    
    print("\n--- Discovered ChartDNA ---")
    print(f"Delay Constants: {result.chart_dna.delay_constants}")
    print(f"Grammar Overrides: {result.chart_dna.grammar_overrides}")
    
    print("\n--- Personalised Future Predictions ---")
    for pred in result.future_predictions[:3]:
        print(f"[{pred.domain}] {pred.prediction_text} at age {pred.peak_age} (Adjusted: {pred.adjusted_peak_age})")

if __name__ == "__main__":
    run_amitabh_demo()
