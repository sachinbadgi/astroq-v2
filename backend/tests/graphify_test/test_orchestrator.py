import pytest
import os
import json
from backend.tests.graphify_test.orchestrator import GraphifyTestOrchestrator

def test_orchestrator_initialization(tmp_path):
    graph_data = {"nodes": [{"id": "node_1", "norm_label": "main()"}]}
    graph_file = tmp_path / "graph.json"
    with open(graph_file, "w") as f:
        json.dump(graph_data, f)
    
    orchestrator = GraphifyTestOrchestrator(str(graph_file))
    assert orchestrator.index.get_node_by_id("node_1") is not None
    assert orchestrator.tracer is not None

def test_orchestrator_tracing_flow(tmp_path):
    graph_data = {"nodes": [{"id": "node_1", "norm_label": "main()"}]}
    graph_file = tmp_path / "graph.json"
    with open(graph_file, "w") as f:
        json.dump(graph_data, f)
    
    orchestrator = GraphifyTestOrchestrator(str(graph_file))
    
    with orchestrator.start_trace() as trace:
        orchestrator.tracer.hit("node_1")
    
    assert trace.hits == ["node_1"]
