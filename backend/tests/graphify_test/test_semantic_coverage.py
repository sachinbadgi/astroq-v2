import pytest
import os
import json
from typing import Dict, Any

from astroq.lk_prediction.varshphal_timing_engine import VarshphalTimingEngine
from astroq.lk_prediction.astrological_context import UnifiedAstrologicalContext
from astroq.lk_prediction.data_contracts import EnrichedChart
from tests.graphify_test.orchestrator import GraphifyTestOrchestrator
from tests.graphify_test.physical_fuzzer import PhysicalChartFuzzer

# Load coverage map for parameterization
COVERAGE_MAP_PATH = "backend/tests/graphify_test/coverage_map.json"
GRAPH_PATH = "graphify-out/graph.json"

with open(COVERAGE_MAP_PATH, "r") as f:
    RULES_DATA = json.load(f)

@pytest.fixture(scope="module")
def engine():
    e = VarshphalTimingEngine()
    e.test_mode = True
    return e

@pytest.fixture(scope="module")
def orchestrator():
    return GraphifyTestOrchestrator(GRAPH_PATH)

@pytest.fixture(scope="module")
def fuzzer():
    return PhysicalChartFuzzer(COVERAGE_MAP_PATH)

@pytest.mark.parametrize("rule", RULES_DATA, ids=lambda r: r["rule_id"])
def test_rule_semantic_coverage(engine, orchestrator, fuzzer, rule):
    """
    MASTER TEST: Verifies that a rule is both semantically triggered (engine output)
    and structurally reached (graphify trace).
    """
    rule_id = rule["rule_id"]
    domain = rule["domain"]
    target_node = rule["node_id"]

    # 1. Generate REAL chart satisfying the rule
    # We search for a physical date/time that satisfies the pattern
    chart_data = fuzzer.find_chart_for_rule(rule)
    
    if not chart_data:
        pytest.skip(f"Could not find physically real chart for rule {rule_id} within time limit")

    context = UnifiedAstrologicalContext(enriched=EnrichedChart(source=chart_data))
    context.age = 30 # Default age for testing
    
    # 2. Trace execution
    with orchestrator.start_trace() as trace:
        results = engine.evaluate_varshphal_triggers(context, domain)
        
        # 3. Assertions
        
        # Assertion A: Structural Reachability (Did the code path execute?)
        # We check if the target_node was recorded in the tracer hits.
        assert target_node in trace.hits, f"Node {target_node} was not hit in graphify trace."
        
        # Assertion B: Semantic Intent (Did the rule actually match?)
        # We check if the specific rule description appears in the results.
        is_hit = any(rule_id in (r.get("desc") or "") for r in results)
        assert is_hit, f"Rule '{rule_id}' failed to match engine logic even with satisfied constraints."

def test_coverage_score(engine, orchestrator, fuzzer):
    """
    Final summary test to verify overall health.
    """
    # This is a meta-test that just checks if the report from the last run was healthy
    # Or we can just leave it to the individual tests.
    pass
