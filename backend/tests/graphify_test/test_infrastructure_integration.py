import pytest
import os
from astroq.lk_prediction.engine_runner import LKEngineRunner
from backend.tests.graphify_test.orchestrator import GraphifyTestOrchestrator

@pytest.fixture
def orchestrator():
    # Use the real graph.json from graphify-out
    graph_path = os.path.abspath("graphify-out/graph.json")
    return GraphifyTestOrchestrator(graph_path)

@pytest.fixture
def engine_runner():
    # Use relative path from the perspective of where pytest is run (root)
    db_path = "backend/data/public_figures.db"
    config_path = "backend/data/model_defaults.json"
    return LKEngineRunner(db_path, config_path)

def test_full_infrastructure_trace(orchestrator, engine_runner):
    # Setup sample birth data (Sachin Tendulkar - already in GEO_MAP)
    dob = "1973-04-24"
    tob = "18:20"
    place = "Mumbai, India"
    
    with orchestrator.start_trace() as trace:
        # Run a minimal prediction
        engine_runner.run(dob, tob, place, age=1)
    
    # Verify we captured hits
    assert len(trace.hits) > 0
    
    # Verify specific expected hits (God Nodes)
    expected_hits = [
        "lk_prediction_engine_runner_lkenginerunner_run",
        "lk_prediction_engine_runner_lkenginerunner_build_chart",
        "lk_prediction_engine_runner_lkenginerunner_build_pipeline",
        "lk_prediction_pipeline_lkpredictionpipeline_generate_predictions"
    ]
    
    for hit in expected_hits:
        assert hit in trace.hits, f"Expected hit {hit} not found in trace"
    
    # Verify hits exist in the index
    for hit_id in trace.hits:
        node = orchestrator.index.get_node_by_id(hit_id)
        assert node is not None, f"Hit node {hit_id} not found in GraphIndex"
