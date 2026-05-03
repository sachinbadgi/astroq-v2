# Issue: Implement Rule Extraction (AST Parsing)

Status: `complete` (Extracted 200+ rules from lk_pattern_constants.py)

## Description

Automate the discovery of astrological rules by parsing the source code. This allows the fuzzer to know exactly what planetary configurations it needs to generate to achieve "Semantic Coverage."

## Tasks

- [ ] Create `backend/tests/graphify_test/rule_extractor.py`.
- [ ] Implement AST parser to extract logic from `RulesEngine` or specific pattern modules.
- [ ] Map extracted rules to Graphify `node_id`s.
- [ ] Export rules to a standardized `coverage_map.json`.
- [ ] Verify extraction via unit tests.

## Comments
- We should focus on extracting constraints like `planet in house X` and `planet has aspect Y`.
