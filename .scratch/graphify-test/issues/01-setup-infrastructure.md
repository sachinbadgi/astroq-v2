# Issue: Setup Graphify-Test Infrastructure

Status: `complete` (Verified via integration tests)

## Description

Initial setup for the Graphify-Test framework, including the directory structure, base orchestrator, and integration with the existing Graphify output.

## Tasks

- [ ] Create `backend/tests/graphify_test/` directory.
- [ ] Implement `GraphifyTestOrchestrator` base class.
- [ ] Create utility to load and index `graph.json` for fast node lookup.
- [ ] Implement basic "Execution Tracer" context manager to capture node hits.

## Comments
- This is the foundation for all subsequent weeks (Rule Extraction, Fuzzing, Snapshots).
