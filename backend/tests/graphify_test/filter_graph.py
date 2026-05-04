import json
import os
from pathlib import Path

def filter_graph():
    graph_path = "graphify-out/graph.json"
    passed_rules_path = "backend/tests/graphify_test/passed_rules.json"
    coverage_map_path = "backend/tests/graphify_test/coverage_map.json"
    output_json = "graphify-out/graph_passed.json"
    output_html = "graphify-out/graph_passed.html"

    if not os.path.exists(graph_path):
        print(f"Error: {graph_path} not found")
        return

    with open(graph_path, "r") as f:
        graph = json.load(f)

    with open(passed_rules_path, "r") as f:
        passed_rule_ids = json.load(f)

    with open(coverage_map_path, "r") as f:
        coverage_map = json.load(f)

    # 1. Map rule IDs to their Engine Node IDs
    rule_to_engine = {r["rule_id"]: r["node_id"] for r in coverage_map}
    
    # 2. Create new nodes for the Rules themselves
    new_nodes = []
    new_links = []
    passed_engine_node_ids = set()

    for rid in passed_rule_ids:
        engine_node_id = rule_to_engine.get(rid)
        if not engine_node_id: continue
        
        passed_engine_node_ids.add(engine_node_id)
        
        # Create a unique node for the rule
        safe_rid = rid.lower().replace(" ", "_").replace(",", "").replace("+", "_")
        rule_node_id = f"rule_{safe_rid}"
        
        new_nodes.append({
            "id": rule_node_id,
            "label": rid,
            "file_type": "rationale", # Marking as rationale for coloring
            "status": "PASSED",
            "community": 999 # Special community for passed rules
        })
        
        # Link rule to the engine function that evaluates it
        new_links.append({
            "source": rule_node_id,
            "target": engine_node_id,
            "relation": "verified_by",
            "confidence": "EXTRACTED",
            "weight": 2.0
        })

    print(f"Injecting {len(new_nodes)} passed rule nodes...")

    # 3. Filter existing graph for context
    # We include the engine nodes and their neighbors
    existing_links = [l for l in graph["links"] if l["source"] in passed_engine_node_ids or l["target"] in passed_engine_node_ids]
    
    context_node_ids = set()
    for l in existing_links:
        context_node_ids.add(l["source"])
        context_node_ids.add(l["target"])
    
    filtered_existing_nodes = [n for n in graph["nodes"] if n["id"] in context_node_ids]
    
    # Merge
    final_nodes = filtered_existing_nodes + new_nodes
    final_links = existing_links + new_links
    
    filtered_graph = {
        "directed": graph.get("directed", False),
        "multigraph": graph.get("multigraph", False),
        "graph": graph.get("graph", {}),
        "nodes": final_nodes,
        "links": final_links
    }

    with open(output_json, "w") as f:
        json.dump(filtered_graph, f, indent=2)

    print(f"Saved filtered graph to {output_json}")

    # Generate HTML
    try:
        from graphify.export import to_html
        import networkx as nx
        
        # Use simple construction to avoid build_from_json complexity
        G = nx.Graph()
        for n in final_nodes:
            G.add_node(n["id"], **n)
        for l in final_links:
            G.add_edge(l["source"], l["target"], **l)
            
        # Group by status/type for visual clarity
        communities = {
            0: [n["id"] for n in final_nodes if n.get("status") == "PASSED"],
            1: [n["id"] for n in final_nodes if n.get("status") != "PASSED"]
        }
        
        to_html(G, communities, output_html, community_labels={0: "PASSED RULES", 1: "ENGINE CONTEXT"})
        print(f"Generated filtered visualizer at {output_html}")
    except Exception as e:
        print(f"Could not generate HTML: {e}")

if __name__ == "__main__":
    filter_graph()
