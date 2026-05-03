import os
import sys
import json
import random
from typing import Dict, Any

# Ensure we can import from backend
sys.path.append(os.path.abspath("backend"))

from astroq.lk_prediction.varshphal_timing_engine import VarshphalTimingEngine
from astroq.lk_prediction.astrological_context import UnifiedAstrologicalContext
from astroq.lk_prediction.data_contracts import EnrichedChart
from tests.graphify_test.orchestrator import GraphifyTestOrchestrator
from tests.graphify_test.fuzzer import ConstraintAwareFuzzer
from tests.graphify_test.coverage_analyzer import CoverageAnalyzer

def main():
    graph_path = "graphify-out/graph.json"
    coverage_map_path = "backend/tests/graphify_test/coverage_map.json"
    output_report_path = "backend/tests/graphify_test/full_audit_report.json"

    orchestrator = GraphifyTestOrchestrator(graph_path)
    fuzzer = ConstraintAwareFuzzer(coverage_map_path)
    analyzer = CoverageAnalyzer(coverage_map_path)
    
    engine = VarshphalTimingEngine()

    print(f"Starting FULL SEMANTIC AUDIT for {len(fuzzer.rules)} rules...")

    for i, rule in enumerate(fuzzer.rules):
        rule_id = rule["rule_id"]
        if (i+1) % 50 == 0:
            print(f"  Processed {i+1} rules...")

        chart_data = fuzzer.generate_chart_for_rule(rule)
        
        # Prepare context
        context = UnifiedAstrologicalContext(enriched=EnrichedChart(source=chart_data))
        context.age = 30 
        
        with orchestrator.start_trace() as trace:
            try:
                # Dispatch based on domain/type (currently all are varshphal triggers)
                results = engine.evaluate_varshphal_triggers(context, rule["domain"])
                
                is_hit = any(r.get("desc") == rule_id for r in results)
                analyzer.log_result(rule_id, is_hit, trace.hits)
                
            except Exception as e:
                analyzer.log_result(rule_id, False, trace.hits, error=str(e))

    # Save results
    report = analyzer.generate_summary()
    report["detailed_results"] = analyzer.results
    
    with open(output_report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nAudit Complete! Report saved to {output_report_path}")
    analyzer.print_report()

if __name__ == "__main__":
    main()
