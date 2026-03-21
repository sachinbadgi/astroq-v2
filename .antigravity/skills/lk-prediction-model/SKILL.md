---
name: lk-prediction-model
description: Build the Lal Kitab Prediction Translation Model v2 from scratch using test-driven development. Uses autoresearch to study existing codebase patterns and superpowers for parallel test execution. Implements 7 modules (Config, StrengthEngine, GrammarAnalyser, ProbabilityEngine, RulesEngine, EventClassifier, PredictionTranslator) with 98+ tests.
---

# Lal Kitab Prediction Model — Build Skill

## Goal

Build the complete prediction engine from scratch under `backend/astroq/lk_prediction/` using
the model specification in [lk_prediction_model_v2.md](resources/lk_prediction_model_v2.md).

> **CRITICAL**: This is a FROM-SCRATCH build. You may READ existing code for reference,
> but all new code goes into `backend/astroq/lk_prediction/`. Do NOT modify existing modules.

> **STRICT BAN ON STUBS / HALF-BAKED FEATURES**: It is UNACCEPTABLE to leave stubbed implementations in the new codebase (e.g. returning empty lists, mock values, or dummy dictionaries for complex rules). 
> For every feature you build, you MUST:
> 1. Deeply analyze the old reference codebase (`D:\astroq-mar26`) to discover the *complete* mathematical/logical rules.
> 2. Document these exact complete rules into `lk_prediction_model_v2.md` first.
> 3. Write comprehensive TDD tests for the complete rules in the new codebase.
> 4. Implement the complete, true logic in the new codebase. Do not take shortcuts.

## Reference Codebase (READ-ONLY)

The legacy codebase lives at a separate location. Use it for autoresearch ONLY — never modify it.

```
REFERENCE_CODEBASE = D:\astroq-mar26
REFERENCE_BACKEND  = D:\astroq-mar26\backend\astroq
REFERENCE_DATA     = D:\astroq-mar26\backend\data
REFERENCE_DB       = D:\astroq-mar26\backend\astroq.db
REFERENCE_TESTS    = D:\astroq-mar26\backend\tests
REFERENCE_DOCS     = D:\astroq-mar26\docs
```

> When the skill says "study file X", always prefix with `D:\astroq-mar26\` if the file
> is not found in the current workspace. All NEW code goes into the current workspace.

## Pre-Requisites

Before starting, read the full model spec:
```
view_file resources/lk_prediction_model_v2.md
```

## ⚡ Memory System (MANDATORY)

This skill has persistent memory across sessions. You MUST follow this protocol:

### On Session Start (ALWAYS do this FIRST)

Read ALL three memory files before doing ANY work:

```bash
# 1. Know where you left off
view_file .antigravity/skills/lk-prediction-model/memory/progress.md

# 2. Absorb accumulated learnings
view_file .antigravity/skills/lk-prediction-model/memory/learnings.md

# 3. Review settled design decisions (don't re-debate these)
view_file .antigravity/skills/lk-prediction-model/memory/decisions.md
```

> **CRITICAL**: Do NOT skip this step. The memory files tell you:
> - Which phase to resume from (don't redo completed work)
> - Which files already exist (don't recreate them)
> - What patterns worked/failed (don't repeat mistakes)
> - Config values that were tuned (use the tuned values)

### On Session End (ALWAYS do this LAST)

Before ending your session, update ALL relevant memory files:

1. **Update `memory/progress.md`**: Mark completed phases, update test counts,
   check off created files, record benchmark scores
2. **Append to `memory/learnings.md`**: Add a dated entry with what you
   discovered — bugs found, patterns that worked, config insights,
   surprising behaviors, things the next session should know
3. **Append to `memory/decisions.md`**: Record any architectural decisions
   that were made (use the template format)

### Memory Files

| File | Purpose | Read At | Write At |
|------|---------|---------|----------|
| `memory/progress.md` | Phase completion, file checklists, benchmark scores | Session start | After each phase complete |
| `memory/learnings.md` | Accumulated knowledge, bugs, patterns, config insights | Session start | Session end |
| `memory/decisions.md` | Settled architectural decisions (don't re-debate) | Session start | When decisions are made |

## Autoresearch Phase

Before coding each module, autoresearch the **reference codebase** (`D:\astroq-mar26`) for patterns:

| Module | Study These Files (in D:\astroq-mar26) |
|--------|------------------------|
| Config | `backend\astroq\config.py`, `backend\astroq\lal_kitab\probability_model.py` (scattered weights) |
| StrengthEngine | `backend\astroq\global_birth_yearly_strength_setup.py`, `backend\astroq\lal_kitab\masnui.py` |
| GrammarAnalyser | `backend\astroq\global_birth_yearly_grammer_rules.py`, `backend\astroq\Mars_special_rules.py` |
| ProbabilityEngine | `backend\astroq\lal_kitab\probability_model.py`, `backend\astroq\lal_kitab\promise_analyser.py` |
| RulesEngine | `backend\astroq\lal_kitab\rule_worker.py`, DB: `backend\astroq.db` table `deterministic_rules` |
| EventClassifier | `backend\astroq\lal_kitab\event_classifier.py`, `docs\engine_architecture.md` |
| PredictionTranslator | `backend\astroq\lal_kitab\items_resolver.py`, `backend\astroq\life_analytics.py` |

> **Usage**: `view_file D:\astroq-mar26\backend\astroq\config.py` to read reference code.
> The reference DB can be queried with: `sqlite3 D:\astroq-mar26\backend\astroq.db`

## Superpowers TDD Build Sequence

Build in strict phase order. For EACH phase:
1. **Write tests FIRST** (Red)
2. **Implement just enough to pass** (Green)
3. **Run tests** to confirm all green
4. **Refactor** if needed

### Phase 1: Config Module
```bash
# 1. Create test file
# File: backend/tests/lk_prediction/test_config.py
# Tests: 8 unit tests (see model spec Section 4)

# 2. Create implementation
# File: backend/astroq/lk_prediction/config.py
# Data: backend/data/model_defaults.json

# 3. Run tests
// turbo
pytest backend/tests/lk_prediction/test_config.py -v
```

### Phase 2: Strength Engine
```bash
# 1. Create test file
# File: backend/tests/lk_prediction/test_strength_engine.py
# Tests: 10 unit tests (see model spec Section 5)

# 2. Create implementation
# File: backend/astroq/lk_prediction/strength_engine.py

# 3. Run tests
// turbo
pytest backend/tests/lk_prediction/test_strength_engine.py -v
```

### Phase 3: Grammar Analyser
```bash
# 1. Create test file
# File: backend/tests/lk_prediction/test_grammar_analyser.py
# Tests: 23 unit tests (see model spec Section 6)

# 2. Create implementation
# File: backend/astroq/lk_prediction/grammar_analyser.py

# 3. Run tests
// turbo
pytest backend/tests/lk_prediction/test_grammar_analyser.py -v
```

### Phase 4: Rules Engine
```bash
# 1. Create test file
# File: backend/tests/lk_prediction/test_rules_engine.py
# Tests: 14 unit tests (see model spec Section 8)

# 2. Create implementation
# File: backend/astroq/lk_prediction/rules_engine.py

# 3. Run tests
// turbo
pytest backend/tests/lk_prediction/test_rules_engine.py -v
```

### Phase 5: Probability Engine
```bash
# 1. Create test file
# File: backend/tests/lk_prediction/test_probability_engine.py
# Tests: 18 unit tests (see model spec Section 7)

# 2. Create implementation
# File: backend/astroq/lk_prediction/probability_engine.py

# 3. Run tests
// turbo
pytest backend/tests/lk_prediction/test_probability_engine.py -v
```

### Phase 6: Event Classifier
```bash
# 1. Create test file
# File: backend/tests/lk_prediction/test_event_classifier.py
# Tests: 8 unit tests (see model spec Section 9)

# 2. Create implementation
# File: backend/astroq/lk_prediction/event_classifier.py

# 3. Run tests
// turbo
pytest backend/tests/lk_prediction/test_event_classifier.py -v
```

### Phase 7: Prediction Translator
```bash
# 1. Create test file
# File: backend/tests/lk_prediction/test_prediction_translator.py
# Tests: 11 unit tests (see model spec Section 10)

# 2. Create implementation
# File: backend/astroq/lk_prediction/prediction_translator.py

# 3. Run tests
// turbo
pytest backend/tests/lk_prediction/test_prediction_translator.py -v
```

### Phase 8: Pipeline Integration
```bash
# 1. Create test file
# File: backend/tests/lk_prediction/test_pipeline.py
# Tests: 6 integration tests (see model spec Section 11)

# 2. Create implementation
# File: backend/astroq/lk_prediction/pipeline.py

# 3. Run ALL tests
// turbo
pytest backend/tests/lk_prediction/ -v --tb=short
```

### Phase 9: Benchmark
```bash
# Run against ground truth public figures
// turbo
python .antigravity/skills/lk-prediction-model/scripts/run_benchmark.py --domain profession --limit 20
```

### Phase 10: Config Tuning
```bash
# Auto-tune config overrides per figure
python .antigravity/skills/lk-prediction-model/scripts/tune_config.py --iterations 10
```

## File Structure (Final)

```
backend/astroq/lk_prediction/
├── __init__.py
├── config.py                  # Module 1: Centralized config
├── strength_engine.py         # Module 2: Aspect + dignity + scapegoat
├── grammar_analyser.py        # Module 3: 15 LK grammar factors
├── probability_engine.py      # Module 4: Pn × Tvp × Ea × Dcorr
├── rules_engine.py            # Module 5: DB rules evaluator
├── event_classifier.py        # Module 6: Peak detection + sentiment
├── prediction_translator.py   # Module 7: NL prediction generation
├── pipeline.py                # Orchestrator
└── data_contracts.py          # Shared types (ChartData, EnrichedPlanet, LKPrediction)

backend/data/
└── model_defaults.json        # Default config values

backend/tests/lk_prediction/
├── conftest.py                # Shared fixtures
├── test_config.py
├── test_strength_engine.py
├── test_grammar_analyser.py
├── test_probability_engine.py
├── test_rules_engine.py
├── test_event_classifier.py
├── test_prediction_translator.py
├── test_pipeline.py
└── test_benchmark.py
```

## Metrics (Target)

| Metric | Target | Formula |
|--------|--------|---------|
| **Hit Rate** | > 80% | Events within ±2 years / total |
| **Offset** | < 2.0 | Mean absolute year error |
| **Natal Accuracy** | > 85% | Correct domain ID |
| **False Positive Rate** | < 15% | Spurious peaks / total peaks |
| **Test Coverage** | 98+ tests | All green before merge |
