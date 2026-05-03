# Issue: Implement Constraint-Aware Fuzzer

Status: `complete` (Fuzzer implemented with 60% smoke test hit rate)

## Description

Implement the fuzzer that takes the extracted `coverage_map.json` and generates birth/annual chart data to satisfy those constraints. This will allow us to "solve" for cold paths in the rules engine.

## Tasks

- [ ] Create `backend/tests/graphify_test/fuzzer.py`.
- [ ] Implement `ConstraintAwareFuzzer` that picks a rule and generates a `ChartData` payload satisfying its requirements.
- [ ] Implement "Hit Tracking" to correlate Graphify tracer hits with the specific rule that was being tested.
- [ ] Integrate with `GraphifyTestOrchestrator`.
- [ ] Verify fuzzer hits via a small test suite.

## Comments
- The fuzzer should support both `natal` and `annual` constraint satisfaction.
- We need a way to mock `VedicHoroscopeData` or bypass the heavy astronomical calculation when we just want to test engine logic with forced positions.
