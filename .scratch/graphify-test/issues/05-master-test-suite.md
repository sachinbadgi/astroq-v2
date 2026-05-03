# Issue: Master Semantic Test Suite

Status: `ready-for-agent`

## Description

Create a comprehensive `pytest` suite that uses the Graphify tags to verify 100% semantic coverage of the `RulesEngine`. This test suite will ensure that any future refactoring of the engine logic is automatically validated against the canonical Lal Kitab rules.

## Tasks

- [ ] Create `backend/tests/graphify_test/test_semantic_coverage.py`.
- [ ] Parameterize tests using `coverage_map.json`.
- [ ] Implement "Correlation Assertion":
    *   Assert rule `desc` is in engine results.
    *   Assert `node_id` is in Graphify trace hits.
- [ ] Verify suite passes with 100% success rate.

## Comments
- This suite replaces manual smoke tests with a deterministic, data-driven validation layer.
