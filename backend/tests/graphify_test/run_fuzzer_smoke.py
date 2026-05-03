import os
import sys
import json
from typing import Dict, Any

# Ensure we can import from backend
sys.path.append(os.path.abspath("backend"))

from astroq.lk_prediction.varshphal_timing_engine import VarshphalTimingEngine
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.astrological_context import UnifiedAstrologicalContext
from astroq.lk_prediction.data_contracts import EnrichedChart
from tests.graphify_test.orchestrator import GraphifyTestOrchestrator
from tests.graphify_test.fuzzer import ConstraintAwareFuzzer
from tests.graphify_test.coverage_analyzer import CoverageAnalyzer

def main():
    graph_path = "graphify-out/graph.json"
    coverage_map_path = "backend/tests/graphify_test/coverage_map.json"
    db_path = "backend/data/public_figures.db"
    config_path = "backend/data/model_defaults.json"

    orchestrator = GraphifyTestOrchestrator(graph_path)
    fuzzer = ConstraintAwareFuzzer(coverage_map_path)
    analyzer = CoverageAnalyzer(coverage_map_path)
    
    # Setup engine
    engine = VarshphalTimingEngine()

    # We'll test 10 random rules for the smoke test
    test_rules = random.sample(fuzzer.rules, min(10, len(fuzzer.rules)))
    
    print(f"Starting smoke test for {len(test_rules)} rules...")

    for rule in test_rules:
        rule_id = rule["rule_id"]
        chart_data = fuzzer.generate_chart_for_rule(rule)
        
        # Prepare context
        context = UnifiedAstrologicalContext(enriched=EnrichedChart(source=chart_data))
        context.age = 30 # Default age for testing
        
        with orchestrator.start_trace() as trace:
            try:
                # We call evaluate_varshphal_triggers directly for these rules
                results = engine.evaluate_varshphal_triggers(context, rule["domain"])
                
                # Check if the specific rule was actually 'Hit' by the engine logic
                # (The fuzzer satisfies the constraints, but the engine must return the result)
                is_hit = any(r.get("desc") == rule_id for r in results)
                
                # We consider it a "Semantic Hit" if the node was hit AND the rule matched
                analyzer.log_result(rule_id, is_hit, trace.hits)
                
            except Exception as e:
                analyzer.log_result(rule_id, False, trace.hits, error=str(e))

    analyzer.print_report()

if __name__ == "__main__":
    import random
    main()
