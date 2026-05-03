import pytest
import os
import json
from backend.tests.graphify_test.graph_index import GraphIndex

def test_graph_index_loading(tmp_path):
    # Create a mock graph.json
    graph_data = {
        "nodes": [
            {
                "id": "node_1",
                "norm_label": "main()",
                "source_file": "server.py"
            },
            {
                "id": "node_2",
                "norm_label": "calculate()",
                "source_file": "engine.py"
            }
        ]
    }
    graph_file = tmp_path / "graph.json"
    with open(graph_file, "w") as f:
        json.dump(graph_data, f)
    
    index = GraphIndex(str(graph_file))
    
    assert index.get_node_by_id("node_1")["norm_label"] == "main()"
    assert index.get_node_by_id("node_2")["norm_label"] == "calculate()"
    assert index.get_node_by_id("non_existent") is None

def test_graph_index_lookup_by_label(tmp_path):
    graph_data = {
        "nodes": [
            {
                "id": "node_1",
                "norm_label": "main()",
                "source_file": "server.py"
            }
        ]
    }
    graph_file = tmp_path / "graph.json"
    with open(graph_file, "w") as f:
        json.dump(graph_data, f)
    
    index = GraphIndex(str(graph_file))
    
    nodes = index.get_nodes_by_label("main()")
    assert len(nodes) == 1
    assert nodes[0]["id"] == "node_1"
