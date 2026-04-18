"""
Full 10-Figure Batch Verification for AutoResearch 2.0 (LSE).
Version 4.0: Authentic Lal Kitab Logic across 10 Historical Charts.
"""

import pytest
import json
from astroq.lk_prediction.lse_orchestrator import LSEOrchestrator
from astroq.lk_prediction.data_contracts import LKPrediction
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.rules_engine import RulesEngine


@pytest.fixture
def mock_cfg_and_engine(tmp_path):
    db_path = tmp_path / "test_rules_batch.db"
    defaults_path = tmp_path / "test_defaults_batch.json"
    with open(defaults_path, "w") as f:
        json.dump({}, f)
    cfg = ModelConfig(db_path=str(db_path), defaults_path=str(defaults_path))
    engine = RulesEngine(cfg)
    return cfg, engine


def run_lse_batch_test(orchestrator, birth_chart, life_events, figure_id, expected_delays, benchmarks, expected_aligns=None):
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
        assert result.chart_dna.delay_constants.get(key) == val
    if expected_aligns:
        for key, val in expected_aligns.items():
            assert result.chart_dna.milestone_alignments.get(key) == val


# --- ORIGINAL 5 ---

def test_lse_batch_lincoln(mock_cfg_and_engine):
    run_lse_batch_test(LSEOrchestrator(mock_cfg_and_engine[0]), 
        {"planets_in_houses": {"Sun": {"house": 1}, "Mars": {"house": 8}, "Saturn": {"house": 4}}},
        [{"age": 51.0, "domain": "Career", "description": "Presidency"}, {"age": 56.0, "domain": "health", "description": "Death"}],
        "lincoln", {"delay.sun_h1": 29.0, "delay.saturn_h4": 20.0},
        [("Career", 22, "Sun"), ("health", 36, "Saturn")]
    )

def test_lse_batch_einstein(mock_cfg_and_engine):
    run_lse_batch_test(LSEOrchestrator(mock_cfg_and_engine[0]),
        {"planets_in_houses": {"Sun": {"house": 1}, "Mars": {"house": 8}, "Venus": {"house": 10}}},
        [{"age": 42.0, "domain": "Career", "description": "Nobel"}, {"age": 35.0, "domain": "marriage", "description": "M2"}],
        "einstein", {"delay.sun_h1": 20.0},
        [("Career", 22, "Sun"), ("marriage", 25, "Venus")],
        expected_aligns={"align.venus_h10": 36}
    )

def test_lse_batch_gandhi(mock_cfg_and_engine):
    run_lse_batch_test(LSEOrchestrator(mock_cfg_and_engine[0]),
        {"planets_in_houses": {"Jupiter": {"house": 2}, "Rahu": {"house": 2}, "Saturn": {"house": 4}}},
        [{"age": 40.0, "domain": "Career", "description": "Peak"}, {"age": 79.0, "domain": "health", "description": "Death"}],
        "gandhi", {"delay.saturn_h4": 43.0},
        [("Career", 16, "Jupiter"), ("health", 36, "Saturn")],
        expected_aligns={"align.jupiter_h2": 42}
    )

def test_lse_batch_indira(mock_cfg_and_engine):
    run_lse_batch_test(LSEOrchestrator(mock_cfg_and_engine[0]),
        {"planets_in_houses": {"Sun": {"house": 1}, "Mars": {"house": 8}, "Mercury": {"house": 9}}},
        [{"age": 49.0, "domain": "Career", "description": "PM"}, {"age": 25.0, "domain": "marriage", "description": "M1"}],
        "indira", {"delay.sun_h1": 27.0, "delay.mercury_h9": -9.0},
        [("Career", 22, "Sun"), ("marriage", 34, "Mercury")]
    )

def test_lse_batch_qe2(mock_cfg_and_engine):
    run_lse_batch_test(LSEOrchestrator(mock_cfg_and_engine[0]),
        {"planets_in_houses": {"Saturn": {"house": 8}, "Venus": {"house": 10}}, "house_status": {"10": "Sleeping House"}},
        [{"age": 26.0, "domain": "Career", "description": "Crown"}, {"age": 21.0, "domain": "marriage", "description": "M1"}],
        "qe2", {"delay.saturn_h10": -10.0, "delay.venus_h10": -4.0},
        [("Career", 36, "Saturn"), ("marriage", 25, "Venus")]
    )

# --- NEW 5 ---

def test_lse_batch_jobs(mock_cfg_and_engine):
    run_lse_batch_test(LSEOrchestrator(mock_cfg_and_engine[0]),
        {"planets_in_houses": {"Saturn": {"house": 10}, "Sun": {"house": 1}, "Mars": {"house": 8}}},
        [{"age": 42.0, "domain": "Career", "description": "Return to Apple"}, {"age": 48.0, "domain": "health", "description": "Cancer"}],
        "jobs", {"delay.saturn_h10": 6.0, "delay.sun_h1": 26.0},
        [("Career", 36, "Saturn"), ("health", 22, "Sun")] 
    )

def test_lse_batch_mandela(mock_cfg_and_engine):
    run_lse_batch_test(LSEOrchestrator(mock_cfg_and_engine[0]),
        {"planets_in_houses": {"Sun": {"house": 8}}},
        [{"age": 75.0, "domain": "Career", "description": "Presidency"}],
        "mandela", {"delay.sun_h8": 53.0},
        [("Career", 22, "Sun")]
    )

def test_lse_batch_thatcher(mock_cfg_and_engine):
    run_lse_batch_test(LSEOrchestrator(mock_cfg_and_engine[0]),
        {"planets_in_houses": {"Saturn": {"house": 10}}},
        [{"age": 53.0, "domain": "Career", "description": "PM"}],
        "thatcher", {"delay.saturn_h10": 17.0},
        [("Career", 36, "Saturn")]
    )

def test_lse_batch_jfk(mock_cfg_and_engine):
    run_lse_batch_test(LSEOrchestrator(mock_cfg_and_engine[0]),
        {"planets_in_houses": {"Sun": {"house": 8}, "Saturn": {"house": 4}}},
        [{"age": 43.0, "domain": "Career", "description": "President"}, {"age": 46.0, "domain": "health", "description": "Death"}],
        "jfk", {"delay.sun_h8": 21.0, "delay.saturn_h4": 10.0}, 
        [("Career", 22, "Sun"), ("health", 36, "Saturn")] 
    )

def test_lse_batch_george6(mock_cfg_and_engine):
    run_lse_batch_test(LSEOrchestrator(mock_cfg_and_engine[0]),
        {"planets_in_houses": {"Mercury": {"house": 12}, "Sun": {"house": 2}}},
        [{"age": 40.0, "domain": "Career", "description": "King"}, {"age": 30.0, "domain": "health", "description": "Stammering Therapy"}],
        "george6", {"delay.sun_h2": 18.0, "delay.mercury_h12": -4.0}, # Note: mock Sun H2 rationale needed?
        [("Career", 22, "Sun"), ("health", 34, "Mercury")]
    )
