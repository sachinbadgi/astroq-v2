# Skill Memory: Design Decisions

> Settled architectural decisions for the AutoResearch 2.0 (LSE) skill.
> The agent MUST read this at session start to avoid re-debating closed questions.

## How to Use This File

**At session start**: Read all decisions. Do NOT re-open closed decisions.
**When making a new decision**: Append using the template at the bottom.

---

## DEC-001: Agent Interaction Model

**Date**: 2026-03-24  
**Decision**: The Researcher and Validator are **Python classes**, NOT external
LLM calls. They are deterministic algorithms.  
**Reasoning**: Keeps the system deterministic, testable, and fast. LLM-based
hypothesis generation is a future enhancement (see Open Items in spec).  
**Status**: ✅ Closed

---

## DEC-002: Hypothesis as Plain Dict

**Date**: 2026-03-24  
**Decision**: A `Hypothesis` is a plain `dict` with keys `type`, `key`, `value`,
`rationale`. Not a dataclass.  
**Reasoning**: Simplifies serialisation and comparison during iteration. The
closed set of hypothesis types (see SKILL.md) makes a rich class unnecessary.  
**Status**: ✅ Closed

---

## DEC-003: ChartDNA Storage

**Date**: 2026-03-24  
**Decision**: ChartDNA is saved to the **existing `rules.db` SQLite database**
in a new `chart_dna` table (NOT a separate file).  
**Reasoning**: Consistent with how `ModelConfig` overrides are stored. Single
database = simpler backup and migration.  
**Status**: ✅ Closed

---

## DEC-004: Hit Rate Tolerance Window

**Date**: 2026-03-24  
**Decision**: An event is a "hit" if `abs(predicted_peak_age - actual_age) ≤ 1.0`
year.  
**Reasoning**: The spec says ≤ 1 year for back-testing (stricter than the
benchmark runner's ≤ 2 year window — we are personalising, so tolerance is tighter).  
**Status**: ✅ Closed

---

## DEC-005: Zero Life Events Handling

**Date**: 2026-03-24  
**Decision**: If `life_event_log` is empty, `solve_chart()` skips Phase 3 (no
back-testing possible) and returns generic `run_prediction_pipeline()` results
with `confidence_source = "generic"`.  
**Status**: ✅ Closed

---

## DEC-006: Benchmark Database (astroq_gt.db)

**Date**: 2026-03-26  
**Decision**: The AutoResearch 2.0 (LSE) benchmark now uses `astroq_gt.db` for ground truth validation. This includes `lk_birth_charts` for natal data and `benchmark_ground_truth` for life events.  
**Reasoning**: Centralizes benchmark data and ensures consistency across the researcher agents. The `run_lse_benchmark_gt.py` script also persists `ChartDNA` back to this database.  
**Status**: ✅ Closed

---

## Template for New Decisions


```
## DEC-NNN: [Short Title]

**Date**: YYYY-MM-DD
**Decision**: [What was decided]
**Reasoning**: [Why]
**Status**: ✅ Closed | 🔄 Under review
```
