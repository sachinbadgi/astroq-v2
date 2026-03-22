---
name: lk-remedies-module
description: Build the Lal Kitab Remedies Module (RemedyEngine) from scratch using test-driven development. Uses autoresearch to study legacy remedy_engine.py and remedy_modeller.py. Implements planet shifting safety analysis, Goswami priority ranking, lifetime strength projection, life area aggregation, and integration with PredictionTranslator and ProbabilityEngine. Targets 22+ tests across 4 phases.
---

# Lal Kitab Remedies Module — Build Skill

## Goal

Build the complete `RemedyEngine` module under `backend/astroq/lk_prediction/` and integrate it
into `PredictionTranslator` and `ProbabilityEngine`, using the full specification in
[lk_remedies_module_spec.md](resources/lk_remedies_module_spec.md).

> **CRITICAL**: This is a FROM-SCRATCH build. You may READ existing code for reference,
> but all new code goes into `backend/astroq/lk_prediction/`. Do NOT modify existing modules
> unless explicitly called out as an integration step.

> **STRICT BAN ON STUBS / HALF-BAKED FEATURES**: It is UNACCEPTABLE to return empty
> lists, mock values, or placeholder implementations. For every feature:
> 1. Deep-read the legacy codebase (`D:\astroq-mar26`) for complete logic.
> 2. Document findings in `lk_remedies_module_spec.md` (resource file) first.
> 3. Write TDD tests for the complete logic.
> 4. Implement the full, true logic. No shortcuts.

---

## Reference Codebase (READ-ONLY)

The legacy codebase is a READ-ONLY reference. Never modify it.

```
REFERENCE_CODEBASE    = D:\astroq-mar26
REFERENCE_BACKEND     = D:\astroq-mar26\backend\astroq
REFERENCE_DB          = D:\astroq-mar26\backend\astroq.db
REFERENCE_TESTS       = D:\astroq-mar26\backend\tests
```

### Key Reference Files for Autoresearch

| Module / Topic         | Study File(s)                                                                         |
|------------------------|--------------------------------------------------------------------------------------|
| Planet Shifting Engine | `D:\astroq-mar26\backend\astroq\remedy_engine.py` (397 L)                             |
| LK-Aware Shifting      | `D:\astroq-mar26\backend\astroq\lal_kitab\remedy_modeller.py` (452 L)                |
| Chart Enrichment       | `D:\astroq-mar26\backend\astroq\lal_kitab\enricher.py` (1596 L) — shifting integration |
| RLM Context            | `D:\astroq-mar26\backend\astroq\lal_kitab\rlm_engine.py` (529 L)                     |
| Probability Integration| `D:\astroq-mar26\backend\astroq\lal_kitab\probability_model.py` (1053 L)             |
| Item Resolution        | `D:\astroq-mar26\backend\astroq\lal_kitab\items_resolver.py`                         |

> **Usage**: `view_file D:\astroq-mar26\backend\astroq\remedy_engine.py`
> The reference DB: `sqlite3 D:\astroq-mar26\backend\astroq.db`

---

## Pre-Requisites

Before starting, verify the prediction model base is in place:

```bash
# Confirm base modules exist
view_file backend/astroq/lk_prediction/config.py
view_file backend/astroq/lk_prediction/prediction_translator.py
view_file backend/astroq/lk_prediction/probability_engine.py
view_file backend/data/model_defaults.json
```

Then read the **full remedies spec**:
```bash
view_file .antigravity/skills/lk-remedies-module/resources/lk_remedies_module_spec.md
```

---

## ⚡ Memory System (MANDATORY)

This skill has persistent memory across sessions. You MUST follow this protocol exactly.

### On Session Start (ALWAYS do this FIRST)

Read ALL three memory files before doing ANY work:

```bash
# 1. Know where you left off
view_file .antigravity/skills/lk-remedies-module/memory/progress.md

# 2. Absorb accumulated learnings
view_file .antigravity/skills/lk-remedies-module/memory/learnings.md

# 3. Review settled design decisions (don't re-debate these)
view_file .antigravity/skills/lk-remedies-module/memory/decisions.md
```

> **CRITICAL**: Do NOT skip this step. The memory files tell you:
> - Which phase to resume from (don't redo completed work)
> - Which files already exist (don't recreate them)
> - What patterns worked/failed (don't repeat mistakes)
> - Integration notes from prior sessions

### On Session End (ALWAYS do this LAST)

Before ending your session, update ALL relevant memory files:

1. **Update `memory/progress.md`**: Mark completed phases, test counts, file checklists
2. **Append to `memory/learnings.md`**: Add a dated entry with discoveries, bugs, patterns
3. **Append to `memory/decisions.md`**: Record any new architectural decisions made

### Memory Files

| File                | Purpose                                          | Read At       | Write At                  |
|---------------------|--------------------------------------------------|---------------|---------------------------|
| `memory/progress.md` | Phase completion, file checklists, test counts  | Session start | After each phase complete |
| `memory/learnings.md`| Accumulated knowledge, bugs, config insights    | Session start | Session end               |
| `memory/decisions.md`| Settled architectural decisions                 | Session start | When decisions are made   |

---

## Autoresearch Phase

Before coding each module, autoresearch the **reference codebase** for patterns.
Study these files in order:

### Step 1 — Understand Constants & Data Structures

```bash
# PUCCA_GHARS (extended), ENEMIES, EXALTATION_HOUSES, MASNUI_TO_STANDARD
view_file D:\astroq-mar26\backend\astroq\remedy_engine.py
```

Look for:
- `PUCCA_GHARS` dict — note it uses an **extended** list (e.g., Saturn→[7,8,10,11])
  vs the single Pakka Ghar used in StrengthEngine. Document both.
- `ENEMIES` dict — planet-level enemy set used for blocking
- `MASNUI_TO_STANDARD` — mapping from artificial planet names to base planet
- `SHIFTING_BOOST` and `RESIDUAL_IMPACT_FACTOR` constants

### Step 2 — Study shift safety logic

```bash
# get_safe_houses(), get_year_shifting_options() in the legacy engine
view_file D:\astroq-mar26\backend\astroq\lal_kitab\remedy_modeller.py
```

Look for:
- Birth × Annual intersection logic
- `conflict_map` merging (prefix "Birth:" vs "Annual:")
- How Masnui planets are checked for conflicts

### Step 3 — Study Goswami ranking

```bash
# rank_safe_houses(), GOSWAMI_PAIR_TARGETS
view_file D:\astroq-mar26\backend\astroq\lal_kitab\remedy_modeller.py
```

Look for:
- Score base (10) + additive rules
- `HOUSE_PREFERENCE_WEIGHTS = {9:30, 2:20, 4:10}`
- Unblock rule (H8 → H2/H4 = +50)
- Pair companion rule (`GOSWAMI_PAIR_TARGETS`, +40)
- Doubtful state rule (+20)
- Tier thresholds: CRITICAL≥60, High≥40, Medium≥20, Low<20

### Step 4 — Study lifetime projection

```bash
# simulate_lifetime_strength() / analyze_life_area_potential()
view_file D:\astroq-mar26\backend\astroq\remedy_engine.py
```

Look for:
- `LIFE_AREA_GROUPS` dict
- Cumulative residual algorithm
- How `fixed_fate`, `current_remediation`, `untapped_potential`, `remediation_efficiency` are computed

### Step 5 — Study probability integration gap

```bash
# calculate_varshaphal_trigger() — does it use shifting boost?
view_file D:\astroq-mar26\backend\astroq\lal_kitab\probability_model.py
```

Look for: how (or whether) remedy application affects strength_total fed into Pn / Tvp.
Document the gap vs what should happen.

### Step 6 — Study item resolution

```bash
# get_planet_items(planet, house) used in articles list
view_file D:\astroq-mar26\backend\astroq\lal_kitab\items_resolver.py
```

Look for: which Sheet/method maps planet+house → articles (physical objects for shifting).

---

## Superpowers TDD Build Sequence

Build in strict phase order. For EACH phase:
1. **Write tests FIRST** (Red — tests fail because code doesn't exist yet)
2. **Implement just enough to pass** (Green)
3. **Run tests** to confirm all green
4. **Refactor** if needed, keeping tests green

---

### Phase A: Config Extension

Extend `model_defaults.json` with all `remedy.*` config keys and update `ModelConfig`
to recognise the new group.

```bash
# 1. Add remedy.* keys to backend/data/model_defaults.json
# 2. Verify config loads new keys correctly

// turbo
pytest backend/tests/lk_prediction/test_config.py -v -k "remedy"
```

Config keys to add (see spec Section 3):
```json
{
  "remedy.shifting_boost": 2.5,
  "remedy.residual_impact_factor": 0.05,
  "remedy.safe_multiplier": 1.0,
  "remedy.unsafe_multiplier": 0.5,
  "remedy.tvp_boost_per_unit": 0.1,
  "remedy.goswami_h9_weight": 30,
  "remedy.goswami_h2_weight": 20,
  "remedy.goswami_h4_weight": 10,
  "remedy.goswami_unblock_weight": 50,
  "remedy.goswami_pair_weight": 40,
  "remedy.goswami_doubtful_weight": 20,
  "remedy.critical_score_threshold": 60,
  "remedy.high_score_threshold": 40,
  "remedy.medium_score_threshold": 20
}
```

---

### Phase B: RemedyEngine — Core Module

```bash
# 1. Create test file (WRITE TESTS FIRST)
# File: backend/tests/lk_prediction/test_remedy_engine.py
# Tests: 22 unit tests (see spec Section 5)

# 2. Create implementation
# File: backend/astroq/lk_prediction/remedy_engine.py

# 3. Run tests
// turbo
pytest backend/tests/lk_prediction/test_remedy_engine.py -v --tb=short
```

#### Tests for Phase B (write these first, in this order):

**Group 1 — get_safe_houses (4 tests)**
```
test_get_safe_houses_no_enemies_returns_all_base_recs
test_get_safe_houses_enemy_in_target_returns_blocked
test_get_safe_houses_masnui_enemy_in_target_returns_blocked
test_get_safe_houses_empty_chart_returns_all_recs
```

**Group 2 — get_year_shifting_options (3 tests)**
```
test_get_year_shifting_options_intersection_of_birth_and_annual
test_get_year_shifting_options_no_overlap_returns_empty_safe_matches
test_get_year_shifting_options_conflict_map_merges_both_charts
```

**Group 3 — rank_safe_houses (5 tests)**
```
test_rank_safe_houses_h9_scores_higher_than_h4
test_rank_safe_houses_unblock_rule_gives_critical
test_rank_safe_houses_pair_companion_boosts_score
test_rank_safe_houses_doubtful_planet_boosts_rank
test_rank_safe_houses_sorted_descending_by_score
```

**Group 4 — simulate_lifetime_strength (4 tests)**
```
test_simulate_lifetime_strength_baseline_matches_chart_strengths
test_simulate_lifetime_strength_boost_applied_correct_year
test_simulate_lifetime_strength_residual_carries_forward
test_simulate_lifetime_strength_unsafe_remedy_half_boost
```

**Group 5 — analyze_life_area_potential (2 tests)**
```
test_analyze_life_area_potential_max_exceeds_applied
test_analyze_life_area_potential_efficiency_correct_percentage
```

**Group 6 — generate_remedy_hints (3 tests)**
```
test_generate_remedy_hints_returns_top_3_critical_high
test_generate_remedy_hints_includes_planet_and_house
test_generate_remedy_hints_empty_when_no_safe_matches
```

**Group 7 — config integration (2 tests)**
```
test_remedy_engine_config_shifting_boost_used
test_remedy_engine_config_residual_factor_used
```

---

### Phase C: Integration — PredictionTranslator

Wire `RemedyEngine` into `PredictionTranslator.translate()` so that
`LKPrediction.remedy_applicable` and `LKPrediction.remedy_hints` are populated.

```bash
# 1. Modify backend/astroq/lk_prediction/prediction_translator.py
#    - Add remedy_engine: RemedyEngine param to __init__
#    - Call get_year_shifting_options() and generate_remedy_hints() in translate()

# 2. Add integration tests
# File: backend/tests/lk_prediction/test_remedy_integration.py

# 3. Run integration tests
// turbo
pytest backend/tests/lk_prediction/test_remedy_integration.py -v --tb=short
```

Integration tests:
```
test_translator_populates_remedy_hints_when_safe_matches_exist
test_translator_sets_remedy_applicable_false_when_no_safe_matches
test_translator_remedy_includes_planet_and_house
test_translator_remedy_hints_max_3_items
```

---

### Phase D: Integration — ProbabilityEngine (Tvp Boost)

Wire the shifting boost into `ProbabilityEngine.calculate_varshaphal_trigger()`.
This closes the gap from the old codebase (remedies never increased P(event)).

```bash
# 1. Modify backend/astroq/lk_prediction/probability_engine.py
#    - Accept applied_remedies dict in calculate_varshaphal_trigger()
#    - If remedy applied to this planet+age and is_safe=True: Tvp_base *= (1 + tvp_boost/10)

# 2. Add tests
# File: backend/tests/lk_prediction/test_remedy_tvp_integration.py

# 3. Run tests
// turbo
pytest backend/tests/lk_prediction/test_remedy_tvp_integration.py -v --tb=short
```

Integration tests:
```
test_tvp_boost_increases_when_remedy_applied_safely
test_tvp_unchanged_when_no_remedy_applied
test_tvp_boost_uses_config_tvp_boost_per_unit
test_tvp_boost_unsafe_remedy_no_extra_boost
```

---

### Phase E: End-to-End Verification

Run the full prediction pipeline on a known chart and verify remedy hints appear.

```bash
# 1. Use the Sachin Tendulkar chart (or equivalent)
# 2. Run pipeline and assert remedy_hints is populated for career domain

// turbo
pytest backend/tests/lk_prediction/test_remedy_integration.py -v -k "e2e" --tb=short
```

Also run the full test suite to confirm no regressions:
```bash
// turbo
pytest backend/tests/lk_prediction/ -v --tb=short
```

---

## File Structure (Final)

```
backend/astroq/lk_prediction/
├── remedy_engine.py           # NEW: RemedyEngine class

backend/data/
└── model_defaults.json        # MODIFY: add remedy.* keys

backend/tests/lk_prediction/
├── test_remedy_engine.py      # NEW: 22 unit tests (Phase B)
├── test_remedy_integration.py # NEW: 4+1 integration tests (Phase C + E)
└── test_remedy_tvp_integration.py  # NEW: 4 integration tests (Phase D)

.antigravity/skills/lk-remedies-module/
├── SKILL.md                   # This file
├── resources/
│   └── lk_remedies_module_spec.md  # Complete technical spec
└── memory/
    ├── progress.md
    ├── learnings.md
    └── decisions.md
```

---

## Key Design Decisions (Settled — Do Not Re-Debate)

| Decision | Rationale |
|----------|-----------|
| **Separate `RemedyEngine` class** | Clean module boundary; injectable into translator and probability engine |
| **All constants are config-driven** | SHIFTING_BOOST, RESIDUAL etc. tunable without code changes |
| **`get_safe_houses()` checks both standard AND masnui planets** | Legacy engine did this; masnui enemy in target house blocks shifting |
| **Intersection of birth × annual** | Birth = lifelong potential; annual = current-year safety |
| **Goswami scores are additive** | Multiple conditions compound; CRITICAL naturally dominates output |
| **`generate_remedy_hints()` returns top-3 only** | Avoid overwhelming the prediction with low-priority options |
| **Tvp boost is Phase D (after Phase C is stable)** | Separates functional integration from probabilistic; benchmark impact first |
| **Extended PUCCA_GHARS** | Remedy uses wider safe house set vs single Pakka Ghar in StrengthEngine |

---

## Metrics (Target)

| Metric | Target | Description |
|--------|--------|-------------|
| **Test Coverage** | 30+ tests green | All unit + integration green before merge |
| **Remedy Hint Presence** | >90% valid peaks | Peaks with safe_matches should have hints |
| **No Regression** | 0 test failures | All prior lk_prediction tests still green |
| **Config Coverage** | 13 remedy.* keys | All config keys tunable without code change |
