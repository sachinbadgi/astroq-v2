import json
import os

def enhanced_filter_graph():
    graph_path = "graphify-out/graph.json"
    report_path = "backend/tests/graphify_test/full_system_report.json"
    coverage_map_path = "backend/tests/graphify_test/coverage_map.json"
    output_json = "graphify-out/graph_system.json"
    output_html = "graphify-out/graph_system.html"

    if not os.path.exists(report_path):
        print(f"Error: {report_path} not found. Run system_orchestrator.py first.")
        return

    with open(graph_path, "r") as f:
        graph = json.load(f)

    with open(report_path, "r") as f:
        report = json.load(f)

    with open(coverage_map_path, "r") as f:
        coverage_map = json.load(f)

    rule_to_engine = {r["rule_id"]: r["node_id"] for r in coverage_map}
    
    new_nodes = []
    new_links = []
    engine_node_ids = set()

    # 1. Inject Rule Nodes (Rule Audit)
    for res in report.get("detailed_results", []):
        if not res.get("node_hit"): continue
        
        rid = res["rule_id"]
        engine_node_id = res["target_node"]
        engine_node_ids.add(engine_node_id)
        
        safe_rid = rid.lower().replace(" ", "_").replace(",", "").replace("+", "_")
        rule_node_id = f"rule_{safe_rid}"
        
        status = "PASSED" if res["success"] else "FAILED_SEMANTIC"
        
        new_nodes.append({
            "id": rule_node_id,
            "label": rid,
            "file_type": "rationale",
            "status": status,
            "community": 999
        })
        
        new_links.append({
            "source": rule_node_id,
            "target": engine_node_id,
            "relation": "verified_by",
            "confidence": "EXTRACTED",
            "weight": 2.0 if res["success"] else 0.5
        })

    # 2. Inject Forensic Nodes (Figures & Events)
    for figure in report.get("forensic_results", []):
        fig_node_id = f"figure_{figure['figure_id']}"
        new_nodes.append({
            "id": fig_node_id,
            "label": figure["name"],
            "file_type": "person",
            "status": "FORENSIC",
            "community": 888
        })
        
        # Link to Domains for Natal Promise
        for fate in figure.get("natal_fates", []):
            domain = fate["domain"]
            fate_type = fate["fate_type"]
            
            # Map domain to a central node if possible, or just a label
            domain_node_id = f"domain_{domain}"
            if not any(n["id"] == domain_node_id for n in new_nodes):
                new_nodes.append({
                    "id": domain_node_id,
                    "label": f"Domain: {domain}",
                    "file_type": "domain",
                    "status": "DOMAIN",
                    "community": 777
                })
            
            label = "Fixed Fate (Graha Phal)" if fate_type == "GRAHA_PHAL" else "Doubtful Fate (Mashkooq)"
            new_links.append({
                "source": fig_node_id,
                "target": domain_node_id,
                "relation": label,
                "weight": 3.0 if fate_type == "GRAHA_PHAL" else 1.0
            })

        # Inject Events
        for ev in figure.get("event_results", []):
            safe_ev_name = ev["event"].lower().replace(" ", "_")[:30]
            ev_node_id = f"event_{figure['figure_id']}_{safe_ev_name}"
            
            status = "PASSED" if ev["hit"] else "FAILED_FORENSIC"
            
            new_nodes.append({
                "id": ev_node_id,
                "label": f"{ev['event']} (Age {ev['age']})",
                "file_type": "event",
                "status": status,
                "community": 888
            })
            
            new_links.append({
                "source": fig_node_id,
                "target": ev_node_id,
                "relation": "experienced",
                "weight": 2.0
            })
            
            # Link Event to Triggers (Rules)
            for trigger in ev.get("triggers", []):
                trigger_id = trigger
                # Find the rule node ID
                safe_trid = trigger_id.lower().replace(" ", "_").replace(",", "").replace("+", "_")
                rule_node_id = f"rule_{safe_trid}"
                
                # Only link if we have the rule node
                if any(n["id"] == rule_node_id for n in new_nodes):
                    new_links.append({
                        "source": ev_node_id,
                        "target": rule_node_id,
                        "relation": "timed_by",
                        "weight": 2.5
                    })

    # 3. Filter existing graph for context
    all_target_ids = set(l["target"] for l in new_links if l["target"] in graph["nodes"]) # engine nodes
    existing_links = [l for l in graph["links"] if l["source"] in engine_node_ids or l["target"] in engine_node_ids]
    
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

    print(f"Saved enhanced system graph to {output_json}")

    # Generate HTML
    try:
        from graphify.export import to_html
        import networkx as nx
        
        G = nx.Graph()
        for n in final_nodes:
            G.add_node(n["id"], **n)
        for l in final_links:
            G.add_edge(l["source"], l["target"], **l)
            
        communities = {
            0: [n["id"] for n in final_nodes if n.get("status") == "PASSED"],
            1: [n["id"] for n in final_nodes if n.get("status") == "FORENSIC"],
            2: [n["id"] for n in final_nodes if n.get("status") == "DOMAIN"],
            3: [n["id"] for n in final_nodes if "FAILED" in str(n.get("status"))]
        }
        
        labels = {0: "PASSED RULES", 1: "PUBLIC FIGURES", 2: "DOMAINS", 3: "FAILED REGRESSIONS"}
        
        to_html(G, communities, output_html, community_labels=labels)
        print(f"Generated enhanced visualizer at {output_html}")
    except Exception as e:
        print(f"Could not generate HTML: {e}")

if __name__ == "__main__":
    enhanced_filter_graph()
