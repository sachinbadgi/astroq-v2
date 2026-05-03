# PRD: Graphify-Test Framework

Status: `needs-triage`

## Problem Statement

The AstroQ-v2 backend calculates complex, recursive, and stateful astrological predictions over a 75-year lifecycle. Currently, the testing infrastructure is fragmented and lacks "semantic coverage"—meaning we can verify if the code runs, but not necessarily if all critical Lal Kitab rules (e.g., Mangal Badh, Doubtful Fate, 1-8 Takkar) are being exercised. Furthermore, testing a full 75-year lifecycle is computationally expensive and difficult to debug when regressions occur in later years (e.g., Year 60). Developers lack a way to see how changes in core logic engines ripple through the system's structural graph.

## Solution

Implement the **Graphify-Test Framework**, an automated testing and validation suite that bridges the gap between structural code analysis and astrological domain logic. 

Key pillars of the solution:
1.  **Structural Intelligence**: Leverage Graphify output to identify "God Nodes" (hubs) and "Impact Ripples" for targeted testing.
2.  **Semantic Coverage via Fuzzing**: Use a constraint-aware Monte Carlo fuzzer to generate astronomically valid birth charts that specifically trigger rules extracted from the codebase via AST parsing.
3.  **Segmented Lifecycle Testing**: Introduce "State-Snapshot Milestones" to allow parallelized and isolated testing of specific decades in a 75-year lifecycle.
4.  **Invariant-Based Integration**: Replace brittle JSON diffs with property-based assertions and execution trace verification in the API layer.

## User Stories

1.  As a developer, I want to automatically extract all astrological rules from the `rules_engine.py`, so that I know exactly which conditions need test coverage.
2.  As a developer, I want to see which nodes in the Graphify graph are "Cold" (never hit by tests), so that I can identify blind spots in the engine.
3.  As a developer, I want to generate 10,000 random but astronomically valid birth charts, so that I can stress-test the engine's stability.
4.  As a developer, I want the fuzzer to focus on "Hot Eras" (specific years/months) that satisfy rare rules, so that I don't waste CPU cycles on redundant data.
5.  As a developer, I want to run a test for Year 65 without re-calculating Years 1-64, so that I can debug late-life state regressions quickly.
6.  As a developer, I want to verify that a change in `AspectEngine` only triggers tests for the "Aspect Community" in the graph, so that CI remains fast.
7.  As a developer, I want to see a `X-Test-Trace` header in API responses that lists the Graphify nodes touched, so that I can verify the execution path.
8.  As a maintainer, I want a "Gold Standard" state ledger for Year 10, 20, 30... that validates the integrity of the recursive logic over time.
9.  As a maintainer, I want the CI to fail if a "Fixed Fate" classification (e.g., Graha Phal) changes its semantic tag, even if the narrative text is updated.
10. As a developer, I want to use Pydantic contracts to ensure that fuzzed data doesn't break the expected API response structure.

## Implementation Decisions

### Deep Modules to be Built/Modified

1.  **RuleExtractor (New)**:
    - **Interface**: `extract_rules(file_path: str) -> List[AstrologicalRule]`
    - **Logic**: Uses Python `ast` to parse pattern matching logic and extract house/planet constraints.
2.  **ConstraintAwareFuzzer (New)**:
    - **Interface**: `generate_matching_chart(rule: AstrologicalRule) -> ChartData`
    - **Logic**: Monte Carlo sampling of real-world dates, filtered by "Hot Eras" and astronomical sanity checks (e.g., Sun-Mercury elongation).
3.  **StateCheckpointManager (New)**:
    - **Interface**: `save_milestone(year: int, state: StateLedger)`, `load_milestone(year: int) -> StateLedger`
    - **Logic**: Serializes/Deserializes the `StateLedger` at decadal markers. Includes an integrity check to verify snapshot validity against current code.
4.  **GraphifyTraceDecorator (Modify `pipeline.py` / `engine_runner.py`)**:
    - **Logic**: A lightweight instrumentation layer that records node IDs from `graph.json` as they are executed.
5.  **APIInvariantValidator (Modify `tests/integration/`)**:
    - **Logic**: A test suite that asserts on Pydantic models, semantic tags, and trace IDs instead of raw string/JSON comparisons.

### Architectural Decisions
- **Interface-Level Hashing**: Use the public signatures of "God Nodes" (e.g., `LKPredictionPipeline`) to determine the scope of the impact ripple in CI.
- **Snapshot Integrity Loop**: Every CI run performs a "Full Sweep" on one canonical identity to ensure that the decadal milestones haven't drifted from the latest logic.

## Testing Decisions

### What makes a good test?
- **Behavioral Invariance**: Only test that the core astrological classification (e.g., "Mashkooq") and state values are correct. Do not test the specific wording of narrative strings.
- **Path Verification**: A successful test must not only return the right data but must also prove it traversed the correct logic gates in the graph.

### Prior Art
- Existing unit tests in `backend/tests/` provide basic coverage but lack the 75-year stateful depth.
- Graphify `graph.json` serves as the static blueprint for the dynamic execution tracing.

## Out of Scope
- Real-time visualization of the Graphify Heatmap (this will be a CLI-first tool).
- Testing of the Frontend UI via Playwright (focus is strictly on Backend Engine integrity).
- Correcting the astrological logic itself (this framework is for *verifying* the current logic).

## Further Notes
- The fuzzer will prioritize "Historical Reality" (1900-2100) to ensure the engine is tested against the dates most relevant to users.
- `graph.json` must be regenerated whenever the structural code changes to ensure the `node_id` mappings in the trace remain valid.
