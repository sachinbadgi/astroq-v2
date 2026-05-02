---
name: lk-autoresearch-lse
description: AutoResearch 2.0 (LSE) — a dual-agent system that now uses Canonical Milestone Alignments (36, 42, 48) instead of arbitrary offsets. Integrates with Unified Grammar and Rule-Specific domain mapping.
---

# AutoResearch 2.0 (LSE) — Skill

## Goal

Implement the **LSE (Learn-Self-Evolve)** dual-agent feature on top of the
existing `lk_prediction` pipeline.

Given a user's birth chart + a list of known life events, the system:

1. **Researcher Agent** — extracts applicable rules and proposes hypotheses
   about grammar overrides and delay constants.
2. **Validator Agent** — runs `run_prediction_pipeline()` with each hypothesis
   and reports back the gap between prediction and reality.
3. The two agents iterate ≤ 20 times until back-test hit rate ≥ 95%.
4. The discovered personalised model is saved as `ModelConfig` figure overrides
   and used to generate future predictions with a confidence score.

> **Full LSE Specification**: See [autoresearch_lse_spec.md](resources/autoresearch_lse_spec.md).
> Read this FIRST. It contains the exact algorithm, data structures, step-by-step
> example, and success criteria.

---

## Pre-Requisites (MUST READ FIRST)

Before making any changes, read:

```bash
# 1. Full LSE algorithm + data structures + worked example
view_file .antigravity/skills/lk-autoresearch-lse/resources/autoresearch_lse_spec.md

# 2. Where you left off + files already created
view_file .antigravity/skills/lk-autoresearch-lse/memory/progress.md

# 3. Accumulated learnings from previous sessions
view_file .antigravity/skills/lk-autoresearch-lse/memory/learnings.md

# 4. Settled design decisions (don't re-debate)
view_file .antigravity/skills/lk-autoresearch-lse/memory/decisions.md

# 5. The existing prediction model (integration points)
view_file .antigravity/skills/lk-prediction-model/resources/lk_prediction_model_v2.md
```

---

## ⚡ Memory System (MANDATORY)

This skill maintains persistent memory across sessions.

### On Session Start (do this FIRST, ALWAYS)

```bash
view_file .antigravity/skills/lk-autoresearch-lse/memory/progress.md
view_file .antigravity/skills/lk-autoresearch-lse/memory/learnings.md
view_file .antigravity/skills/lk-autoresearch-lse/memory/decisions.md
```

> **CRITICAL**: DO NOT skip this. The memory tells you which phases are done,
> which files already exist, which hypothesis types worked, and which config
> knobs moved the needle.

### On Session End (do this LAST, ALWAYS)

Before ending the session, update:

1. **`memory/progress.md`** — mark completed phases, tick off created files,
   record latest back-test hit rates.
2. **`memory/learnings.md`** — append a dated entry: what you discovered,
   what hypothesis types worked, surprising chart behaviors, config insights.
3. **`memory/decisions.md`** — record architectural decisions made (use the
   template format in the file).

### Memory Files Reference

| File | Purpose | Read At | Write At |
|------|---------|---------|----------|
| `memory/progress.md` | Phase status, file checklist, hit rate scores | Session start | After each phase |
| `memory/learnings.md` | Hypothesis patterns, config insights, bugs | Session start | Session end |
| `memory/decisions.md` | Settled design choices (agent API, storage, etc.) | Session start | When decisions made |

---

## Reference Codebase (Autoresearch)

The **existing** prediction pipeline lives in the current workspace. Read these
files before implementing each module:

| Module to Build | Study These Files |
|-----------------|------------------|
| `ResearcherAgent` | `backend/astroq/lk_prediction/rules_engine.py`, `grammar_analyser.py` |
| `ValidatorAgent` | `backend/astroq/lk_prediction/pipeline.py`, `benchmark_runner.py` |
| `LSEOrchestrator` | `backend/astroq/lk_prediction/config.py` (`set_override`, figure overrides) |
| `ChartDNA` storage | `backend/data/model_defaults.json` (override structure) |
| `LSEPrediction` | `backend/astroq/lk_prediction/data_contracts.py` |

> **Reference to legacy codebase** (READ-ONLY, for autoresearch):
> ```
> REFERENCE_CODEBASE = D:\astroq-mar26
> ```
> Useful for understanding the original grammar rules and delay patterns
> that were NOT ported to the new prediction engine.

---

## Superpowers TDD Build Sequence

Build in strict phase order. For EACH phase:
1. **Write tests FIRST** (Red)
2. **Implement just enough to pass** (Green)
3. **Run tests** to confirm all green
4. **Update memory files**

### Phase 1: Data Structures + Life Event Log

```bash
# 1. Extend data_contracts.py with LSE types
# File: backend/astroq/lk_prediction/data_contracts.py
# Add: LifeEvent, LifeEventLog, ChartDNA, LSEPrediction

# 2. Create test file
# File: backend/tests/lk_prediction/test_lse_data_contracts.py
# Tests: 6 unit tests (see spec Section 4)

// turbo
pytest backend/tests/lk_prediction/test_lse_data_contracts.py -v
```

### Phase 2: Validator Agent

```bash
# 1. Create test file
# File: backend/tests/lk_prediction/test_lse_validator.py
# Tests: 8 unit tests — gap computation, hit rate, offset, contradiction detection

# 2. Create implementation
# File: backend/astroq/lk_prediction/lse_validator.py
# Class: ValidatorAgent
#   compare_to_events(predictions, life_event_log) -> GapReport
#   compute_hit_rate(gap_report) -> float
#   compute_mean_offset(gap_report) -> float

// turbo
pytest backend/tests/lk_prediction/test_lse_validator.py -v
```

### Phase 3: Researcher Agent

```bash
# 1. Create test file
# File: backend/tests/lk_prediction/test_lse_researcher.py
# Tests: 10 unit tests — rule extraction, hypothesis generation, delay constant
#         proposals, grammar override proposals, hypothesis ranking

# 2. Create implementation
# File: backend/astroq/lk_prediction/lse_researcher.py
# Class: ResearcherAgent
#   extract_applicable_rules(birth_chart) -> list[Rule]
#   generate_hypotheses(gap_report, rules) -> list[Hypothesis]
#   rank_hypotheses(hypotheses, gap_report) -> list[Hypothesis]

// turbo
pytest backend/tests/lk_prediction/test_lse_researcher.py -v
```

### Phase 4: LSE Orchestrator (Core Loop)

```bash
# 1. Create test file
# File: backend/tests/lk_prediction/test_lse_orchestrator.py
# Tests: 12 unit + integration tests
#   - converges within 20 iterations on synthetic chart
#   - stops early when hit_rate >= 0.95
#   - saves ChartDNA correctly
#   - applies delay constants to future predictions
#   - handles zero life events gracefully

# 2. Create implementation
# File: backend/astroq/lk_prediction/lse_orchestrator.py
# Function: solve_chart(birth_chart, life_event_log, max_iterations=20) -> LSESolveResult

// turbo
pytest backend/tests/lk_prediction/test_lse_orchestrator.py -v
```

### Phase 5: ChartDNA Persistence

```bash
# 1. Create test file
# File: backend/tests/lk_prediction/test_lse_chart_dna.py
# Tests: 6 tests — save to DB, load by figure, override merge, confidence score

# 2. Add to SQLite DB schema:
#    Table: chart_dna
#    Columns: figure_id, delay_constants_json, grammar_overrides_json,
#             back_test_hit_rate, mean_offset, iterations, confidence_score,
#             created_at, updated_at

// turbo
pytest backend/tests/lk_prediction/test_lse_chart_dna.py -v
```

### Phase 6: API Endpoint

```bash
# 1. Create test file
# File: backend/tests/lk_prediction/test_lse_api.py
# Tests: 6 endpoint tests

# 2. Create implementation
# File: backend/astroq/lk_prediction/api/lse_routes.py
# POST /api/lk/lse/solve
#   Input: { birth_chart, life_events: LifeEvent[] }
#   Output: { chart_dna: ChartDNA, future_predictions: LSEPrediction[] }

// turbo
pytest backend/tests/lk_prediction/test_lse_api.py -v --tb=short
```

### Phase 7: Full Integration Test

```bash
# Run the worked example from the spec (Sun H1, Jupiter H9, Saturn H10)
# Verify: converges within 15 iterations, hit_rate >= 0.95, delay = 2.5yr

// turbo
pytest backend/tests/lk_prediction/test_lse_orchestrator.py -v -k "worked_example"

# Run all LSE tests together
// turbo
pytest backend/tests/lk_prediction/ -v -k "lse" --tb=short
```

---

## 🚀 Benchmark Execution (astroq_gt.db)

To run the LSE back-testing loop against the ground truth dataset in `astroq_gt.db`, use the provided benchmark script. This script processes public figures in batches of 10.

```bash
# Run benchmark for the first 10 figures
python backend/scripts/run_lse_benchmark_gt.py --batch-size 10 --limit 10

# Resume from index 10
python backend/scripts/run_lse_benchmark_gt.py --batch-size 10 --start-index 10 --limit 10
```

### Data Source
- **Birth Charts**: `lk_birth_charts` table in `backend/data/astroq_gt.db`.
- **Life Events**: `benchmark_ground_truth` table in `backend/data/astroq_gt.db`.

### Output
- Discovered `ChartDNA` (personalised models) are saved back to the `chart_dna` table in `astroq_gt.db`.
- Check progress in the terminal logs.


---

## Hypothesis Types (Researcher Must Generate These)

The Researcher Agent generates hypotheses from this fixed taxonomy.
Autoresearch `grammar_analyser.py` and the LSE spec for the complete rules.

| Hypothesis Type | Config Key | Example Value |
|-----------------|-----------|---------------|
| **Delay Constant** | `delay.{planet}_h{house}` | `delay.mars_h8 = 2.5` |
| **Early Trigger** | `delay.{planet}_h{house}` | `delay.sun_h1 = -1.0` |
| **Sleeping House Cancel** | `grammar.h{N}_sleep_cancelled` | `True` |
| **Travel Override** | `grammar.h12_travel_cancels_h{N}_sleep` | `True` |
| **Masnui Boost** | `grammar.masnui_feedback_amplify` | `1.5` |
| **Rin Delay** | `grammar.rin_delay_years` | `3.0` |
| **Dharmi Acceleration** | `grammar.dharmi_accelerate_factor` | `0.8` |

---

## File Structure (Final)

```
backend/astroq/lk_prediction/
├── lse_validator.py            # ValidatorAgent: gap computation + metrics
├── lse_researcher.py           # ResearcherAgent: rule extraction + hypotheses
├── lse_orchestrator.py         # Core solve_chart() iteration loop
└── api/
    └── lse_routes.py           # POST /api/lk/lse/solve

backend/tests/lk_prediction/
├── test_lse_data_contracts.py  # Phase 1: LifeEvent, ChartDNA, LSEPrediction
├── test_lse_validator.py       # Phase 2: GapReport, hit rate, offset
├── test_lse_researcher.py      # Phase 3: Rule extraction, hypotheses
├── test_lse_orchestrator.py    # Phase 4: Core loop, convergence
├── test_lse_chart_dna.py       # Phase 5: DB persistence
└── test_lse_api.py             # Phase 6: API endpoint

.antigravity/skills/lk-autoresearch-lse/
├── SKILL.md                    # This file
├── resources/
│   └── autoresearch_lse_spec.md  # Full LSE specification + worked example
└── memory/
    ├── progress.md
    ├── learnings.md
    └── decisions.md
```

---

## Success Criteria

The skill is complete when:

- [ ] All 7 phases implemented with tests GREEN
- [ ] `solve_chart()` converges on the spec's worked example (Sun H1, Jupiter H9, Saturn H10) within 15 iterations
- [ ] Back-test hit rate ≥ 95% on the worked example chart
- [ ] Discovered delay constant = 2.5 years (Mars H8)
- [ ] `ChartDNA` saved to DB with correct config overrides
- [ ] API endpoint returns `LSEPrediction[]` with `personalised: True`
- [ ] `confidence_score` ≥ 0.90 for the worked example
- [ ] Memory files updated with all findings

---

## Metrics

| Metric | Target |
|--------|--------|
| **Back-Test Hit Rate** | ≥ 95% (events within ±1 yr) |
| **Mean Offset** | ≤ 1.0 yr |
| **Confidence Score** | ≥ 0.90 |
| **Iterations to Convergence** | ≤ 15 (average) |
| **Test Coverage** | 48+ tests, all GREEN |
