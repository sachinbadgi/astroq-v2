"""
Full Ground-Truth Batch Verification for AutoResearch 2.0 (LSE).
Version 6.0: Refined for Single-Event Convergence across 10 figures.
"""

import pytest
import json
from astroq.lk_prediction.lse_orchestrator import LSEOrchestrator
from astroq.lk_prediction.data_contracts import LKPrediction
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.rules_engine import RulesEngine


@pytest.fixture
def mock_cfg_and_engine(tmp_path):
    db_path = tmp_path / "test_rules_ground.db"
    defaults_path = tmp_path / "test_defaults_ground.json"
    with open(defaults_path, "w") as f:
        json.dump({}, f)
    cfg = ModelConfig(db_path=str(db_path), defaults_path=str(defaults_path))
    engine = RulesEngine(cfg)
    return cfg, engine


def run_ground_truth_test(orchestrator, birth_chart, life_events, figure_id, expected_delays, benchmarks):
    def mock_run_pipeline(birth, annual, fig):
        preds = []
        for domain, bench, planet in benchmarks:
            preds.append(LKPrediction(
                domain=domain, event_type="generic", peak_age=bench, 
                source_planets=[planet], confidence="certain", polarity="mixed", prediction_text=f"{domain} event"
            ))
        return preds

    orchestrator._run_pipeline = mock_run_pipeline
    annual_charts = {e["age"]: birth_chart for e in life_events}
    
    result = orchestrator.solve_chart(birth_chart, annual_charts, life_events, figure_id=figure_id)
    assert result.converged
    for key, val in expected_delays.items():
        assert abs(result.chart_dna.delay_constants.get(key, 0.0) - val) < 0.1


def test_lse_ground_truth_bachchan(mock_cfg_and_engine):
    run_ground_truth_test(LSEOrchestrator(mock_cfg_and_engine[0]),
        {"planets_in_houses": {"Sun": {"house": 1}, "Saturn": {"house": 8}}},
        [{"age": 31, "domain": "career"}, {"age": 40, "domain": "health"}],
        "bachchan", {"delay.sun_h1": 9.0, "delay.saturn_h8": 4.0},
        [("career", 22, "Sun"), ("health", 36, "Saturn")]
    )

def test_lse_ground_truth_tendulkar(mock_cfg_and_engine):
    run_ground_truth_test(LSEOrchestrator(mock_cfg_and_engine[0]),
        {"planets_in_houses": {"Sun": {"house": 1}, "Venus": {"house": 10}}},
        [{"age": 16, "domain": "career"}, {"age": 22, "domain": "marriage"}],
        "sachin", {"delay.sun_h1": -6.0, "delay.venus_h10": -3.0},
        [("career", 22, "Sun"), ("marriage", 25, "Venus")]
    )

def test_lse_ground_truth_modi(mock_cfg_and_engine):
    run_ground_truth_test(LSEOrchestrator(mock_cfg_and_engine[0]),
        {"planets_in_houses": {"Sun": {"house": 1}, "Mars": {"house": 8}}},
        [{"age": 51, "domain": "career"}],
        "modi", {"delay.sun_h1": 29.0},
        [("career", 22, "Sun")]
    )

def test_lse_ground_truth_jobs(mock_cfg_and_engine):
    run_ground_truth_test(LSEOrchestrator(mock_cfg_and_engine[0]),
        {"planets_in_houses": {"Saturn": {"house": 10}, "Sun": {"house": 1}, "Mars": {"house": 8}}},
        [{"age": 42, "domain": "career"}, {"age": 56, "domain": "health"}],
        "jobs", {"delay.saturn_h10": 6.0, "delay.sun_h1": 34.0},
        [("career", 36, "Saturn"), ("health", 22, "Sun")]
    )

def test_lse_ground_truth_gates(mock_cfg_and_engine):
    run_ground_truth_test(LSEOrchestrator(mock_cfg_and_engine[0]),
        {"planets_in_houses": {"Sun": {"house": 1}, "Venus": {"house": 10}}},
        [{"age": 20, "domain": "career"}, {"age": 39, "domain": "marriage"}],
        "gates", {"delay.sun_h1": 0.0, "delay.venus_h10": 14.0},
        [("career", 22, "Sun"), ("marriage", 25, "Venus")]
    )

def test_lse_ground_truth_diana(mock_cfg_and_engine):
    run_ground_truth_test(LSEOrchestrator(mock_cfg_and_engine[0]),
        {"planets_in_houses": {"Venus": {"house": 10}, "Saturn": {"house": 8}}},
        [{"age": 20, "domain": "marriage"}, {"age": 36, "domain": "health"}],
        "diana", {"delay.venus_h10": -5.0, "delay.saturn_h8": 0.0},
        [("marriage", 25, "Venus"), ("health", 36, "Saturn")]
    )

def test_lse_ground_truth_srk(mock_cfg_and_engine):
    run_ground_truth_test(LSEOrchestrator(mock_cfg_and_engine[0]),
        {"planets_in_houses": {"Venus": {"house": 10}, "Sun": {"house": 1}}},
        [{"age": 26, "domain": "marriage"}, {"age": 27, "domain": "career"}],
        "srk", {"delay.venus_h10": 0.0, "delay.sun_h1": 5.0}, # Venus 25 vs 26 is a hit (offset 1.0)
        [("marriage", 25, "Venus"), ("career", 22, "Sun")]
    )

def test_lse_ground_truth_jackson(mock_cfg_and_engine):
    run_ground_truth_test(LSEOrchestrator(mock_cfg_and_engine[0]),
        {"planets_in_houses": {"Mercury": {"house": 12}, "Sun": {"house": 8}}},
        [{"age": 11, "domain": "career"}, {"age": 51, "domain": "health"}],
        "jackson", {"delay.mercury_h12": -23.0, "delay.sun_h8": 29.0},
        [("career", 34, "Mercury"), ("health", 22, "Sun")]
    )

def test_lse_ground_truth_indira(mock_cfg_and_engine):
    run_ground_truth_test(LSEOrchestrator(mock_cfg_and_engine[0]),
        {"planets_in_houses": {"Sun": {"house": 1}, "Mars": {"house": 8}, "Saturn": {"house": 4}}},
        [{"age": 49, "domain": "career"}, {"age": 67, "domain": "health"}],
        "indira", {"delay.sun_h1": 27.0, "delay.saturn_h4": 31.0},
        [("career", 22, "Sun"), ("health", 36, "Saturn")]
    )

def test_lse_ground_truth_musk(mock_cfg_and_engine):
    run_ground_truth_test(LSEOrchestrator(mock_cfg_and_engine[0]),
        {"planets_in_houses": {"Mercury": {"house": 1}, "Sun": {"house": 8}}},
        [{"age": 31, "domain": "career"}],
        "musk", {"delay.mercury_h1": -3.0},
        [("career", 34, "Mercury")]
    )
