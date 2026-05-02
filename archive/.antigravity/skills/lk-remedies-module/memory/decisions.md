# Skill Memory: Design Decisions

> Records architectural decisions made during implementation and WHY.
> Prevents re-debating settled decisions in future sessions.

## Template

```
### [DECISION-NNN] Title
- **Date**: YYYY-MM-DD
- **Context**: What prompted this decision
- **Options Considered**: What alternatives were evaluated
- **Decision**: What was chosen
- **Rationale**: Why this option won
- **Consequences**: What this means for future work
```

---

## Decisions

### [DECISION-001] RemedyEngine as a Separate, Injectable Class

- **Date**: 2026-03-22
- **Context**: Where to put planet shifting logic — inside PredictionTranslator, or standalone?
- **Options Considered**:
  - A) Embed shifting logic directly in `PredictionTranslator.translate()`
  - B) Create a standalone `RemedyEngine` class, injectable via `__init__`
- **Decision**: Option B — standalone injectable class
- **Rationale**: Clean module boundary; independently testable (22 unit tests don't need
  a translator); allows the same engine to be used by `ProbabilityEngine` for Tvp boost;
  consistent with how other engines (StrengthEngine, GrammarAnalyser) are structured.
- **Consequences**: `PredictionTranslator.__init__` gains a `remedy_engine=None` optional
  parameter. `pipeline.py` must instantiate and inject `RemedyEngine`.

---

### [DECISION-002] Extended PUCCA_GHARS for Remedy Safety

- **Date**: 2026-03-22
- **Context**: The remedy engine needs to know which houses are "safe" for shifting.
  Legacy codebase uses TWO different PUCCA_GHARS: single Pakka Ghar (for strength scoring)
  and extended list (for remedy shifting).
- **Options Considered**:
  - A) Reuse the single `PLANET_PAKKA_GHAR` from StrengthEngine
  - B) Define a separate `PUCCA_GHARS` (extended) for remedy engine
- **Decision**: Option B — separate extended PUCCA_GHARS in remedy_engine.py
- **Rationale**: Different semantic purpose. Saturn's single Pakka Ghar is H10 (max dignity),
  but for shifting, Saturn is also safe in H7, H8, H11. The extended set reflects Lal Kitab
  moving prescriptions, not planet strength measurement.
- **Consequences**: `remedy_engine.py` owns its own `PUCCA_GHARS` constant, completely
  independent of the one in `strength_engine.py`. Both are correct for their own purposes.

---

### [DECISION-003] Backward-Compatible Translator Integration

- **Date**: 2026-03-22
- **Context**: PredictionTranslator already has existing tests and callers. Integrating
  RemedyEngine should not break them.
- **Options Considered**:
  - A) Required `remedy_engine` parameter — forces all callers to update
  - B) Optional `remedy_engine=None` — existing callers unchanged
- **Decision**: Option B — optional with None default
- **Rationale**: The remedies module is an enhancement, not a requirement. Existing tests
  should continue to pass, with new tests covering the remedy path. Zero risk of regression
  from Phase C changes to Phase B callers.
- **Consequences**: When `remedy_engine=None`, translator sets `remedy_applicable=False`
  and `remedy_hints=[]`. This matches the current behavior before this skill was built.

---

### [DECISION-004] Tvp Boost as Phase D (After Phase C Stable)

- **Date**: 2026-03-22
- **Context**: The Tvp boost (remedies affecting probability) is a significant change to
  ProbabilityEngine. It needs benchmarking to ensure it doesn't skew hit rates.
- **Options Considered**:
  - A) Implement Tvp boost simultaneously with PredictionTranslator integration
  - B) Implement Tvp boost as a separate phase (Phase D) after Phase C is proven stable
- **Decision**: Option B — Phase D after Phase C
- **Rationale**: Phase C (surface remedy hints in predictions) has no accuracy impact.
  Phase D (raise P(event) when remedy is applied) affects benchmark metrics. Separating
  them allows controlled benchmarking of each change independently.
- **Consequences**: Phase D is optional if benchmarks show Phase C already satisfies targets.
  Document benchmark impact in learnings.md when Phase D is attempted.

---

*(Future decisions will be appended below)*
