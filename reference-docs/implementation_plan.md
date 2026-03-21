# LK Prediction Model v2 — Implementation Plan

Build the complete Lal Kitab prediction engine from scratch under `backend/astroq/lk_prediction/` using test-driven development per the [model specification](file:///d:/astroq-v2/reference-docs/lk_prediction_model_v2.md) and [skill instructions](file:///d:/astroq-v2/.antigravity/skills/lk-prediction-model/SKILL.md).

> [!IMPORTANT]
> This is a **from-scratch** build. All new code goes into `backend/astroq/lk_prediction/`. Reference codebase at `D:\astroq-mar26` is READ-ONLY (autoresearch only). No external dependencies beyond Python stdlib + pytest.

## Proposed Changes

### Foundation Files

#### [NEW] [__init__.py](file:///d:/astroq-v2/backend/astroq/lk_prediction/__init__.py)
Empty package init.

#### [NEW] [data_contracts.py](file:///d:/astroq-v2/backend/astroq/lk_prediction/data_contracts.py)
Shared types: `ChartData` (TypedDict), `EnrichedPlanet` (TypedDict), `LKPrediction` (dataclass), `ClassifiedEvent` (dataclass), `RuleHit` (dataclass). All based on spec Section 3.

#### [NEW] [model_defaults.json](file:///d:/astroq-v2/backend/data/model_defaults.json)
Default config values for all 6 groups (strength, probability, rules, timing, remedy, translator). Values derived from autoresearch of `probability_model.py` and `global_birth_yearly_strength_setup.py`.

#### [NEW] [conftest.py](file:///d:/astroq-v2/backend/tests/lk_prediction/conftest.py)
Shared pytest fixtures: `SAMPLE_NATAL_CHART`, `SAMPLE_ANNUAL_CHART`, `make_config()`, `make_chart()` factory.

---

### Phase 1: Config Module (8 tests)

#### [NEW] [test_config.py](file:///d:/astroq-v2/backend/tests/lk_prediction/test_config.py)
8 unit tests covering defaults loading, fallback, global/figure overrides, hierarchical resolution.

#### [NEW] [config.py](file:///d:/astroq-v2/backend/astroq/lk_prediction/config.py)
`ModelConfig` class — loads `model_defaults.json`, supports DB overrides (SQLite), figure-specific overrides. Resolution: `figure_override → global_override → json_default → HARDCODED_FALLBACK`.

---

### Phase 2: Strength Engine (10 tests)

#### [NEW] [test_strength_engine.py](file:///d:/astroq-v2/backend/tests/lk_prediction/test_strength_engine.py)
10 tests: aspect calculation, dignity (exalted/debilitated/pakka ghar), scapegoat distribution, natal-annual additive merge, empty chart, breakdown summation.

#### [NEW] [strength_engine.py](file:///d:/astroq-v2/backend/astroq/lk_prediction/strength_engine.py)
`StrengthEngine` — 4-step pipeline: raw aspects → dignity scoring → scapegoat distribution → natal-annual merge. Uses lookup tables from reference `config.py` (ASPECT_STRENGTH_DATA, HOUSE_ASPECT_DATA, FRIENDS/ENEMIES, FIXED_HOUSES, etc).

---

### Phase 3: Grammar Analyser (23 tests)

#### [NEW] [test_grammar_analyser.py](file:///d:/astroq-v2/backend/tests/lk_prediction/test_grammar_analyser.py)
23 tests covering all 15 grammar elements: sleeping, kaayam, dharmi, sathi, bil mukabil, mangal badh, masnui, dhoka, achanak chot, rin, 35Y ruler, disposition, confrontation. Plus compound tests.

#### [NEW] [grammar_analyser.py](file:///d:/astroq-v2/backend/astroq/lk_prediction/grammar_analyser.py)
`GrammarAnalyser` — detects all 15 grammar flags AND feeds them back into `strength_total` via configurable weights. Processing order per spec Section 6.

---

### Phase 4: Rules Engine (14 tests)

#### [NEW] [test_rules_engine.py](file:///d:/astroq-v2/backend/tests/lk_prediction/test_rules_engine.py)
14 tests for condition evaluation (placement, conjunction, confrontation, AND/OR/NOT operators, nested conditions, specificity scoring).

#### [NEW] [rules_engine.py](file:///d:/astroq-v2/backend/astroq/lk_prediction/rules_engine.py)
`RulesEngine` — loads rules from SQLite `deterministic_rules` table, evaluates condition trees against chart data, returns `RuleHit` list sorted by specificity.

---

### Phase 5: Probability Engine (18 tests)

#### [NEW] [test_probability_engine.py](file:///d:/astroq-v2/backend/tests/lk_prediction/test_probability_engine.py)
18 tests: sigmoid behavior, adaptive k, natal propensity modifiers, Tvp delivery rules, Ea boost/penalty/cap, Dcorr, probability clamping, 75-year model.

#### [NEW] [probability_engine.py](file:///d:/astroq-v2/backend/astroq/lk_prediction/probability_engine.py)
`ProbabilityEngine` — implements `P(event|age,domain) = σ(Pn) × Tvp^α × Ea × Dcorr`. All magic numbers from config.

---

### Phase 6: Event Classifier (8 tests)

#### [NEW] [test_event_classifier.py](file:///d:/astroq-v2/backend/tests/lk_prediction/test_event_classifier.py)
8 tests: peak detection (absolute + momentum), sentiment classification, domain tagging from house rules.

#### [NEW] [event_classifier.py](file:///d:/astroq-v2/backend/astroq/lk_prediction/event_classifier.py)
`EventClassifier` — hybrid peak detection, sentiment classification (BENEFIC/MALEFIC/VOLATILE/MIXED), domain mapping from `DOMAIN_WEIGHTS`.

---

### Phase 7: Prediction Translator (11 tests)

#### [NEW] [test_prediction_translator.py](file:///d:/astroq-v2/backend/tests/lk_prediction/test_prediction_translator.py)
11 tests: confidence mapping, agent resolution, item resolution, text generation, full translation pipeline.

#### [NEW] [prediction_translator.py](file:///d:/astroq-v2/backend/astroq/lk_prediction/prediction_translator.py)
`PredictionTranslator` — translates classified events into natural language `LKPrediction` objects with confidence levels, affected items/people, remedy hints.

---

### Phase 8: Pipeline Integration (6 tests)

#### [NEW] [test_pipeline.py](file:///d:/astroq-v2/backend/tests/lk_prediction/test_pipeline.py)
6 integration tests: end-to-end pipeline, known chart peak age, domain filtering, empty chart.

#### [NEW] [pipeline.py](file:///d:/astroq-v2/backend/astroq/lk_prediction/pipeline.py)
`run_prediction_pipeline()` — orchestrates all 7 modules in sequence per spec Section 11.

---

## Verification Plan

### Automated Tests

Each phase is verified by running its test suite. Due to session limits, we'll implement **Phases 1-3** in this session.

```bash
# Phase 1: Config (8 tests)
pytest backend/tests/lk_prediction/test_config.py -v

# Phase 2: Strength Engine (10 tests)
pytest backend/tests/lk_prediction/test_strength_engine.py -v

# Phase 3: Grammar Analyser (23 tests)
pytest backend/tests/lk_prediction/test_grammar_analyser.py -v

# All phases combined
pytest backend/tests/lk_prediction/ -v --tb=short
```

### Success Criteria
- All tests **GREEN** before moving to next phase
- Each module follows the data contracts defined in `data_contracts.py`
- Config values match reference codebase defaults (autoresearched)
- `strength_breakdown` sums to `strength_total` for every enriched planet
