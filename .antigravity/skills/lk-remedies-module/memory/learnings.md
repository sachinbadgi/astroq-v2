# Skill Memory: Learnings Log

> Accumulated knowledge from implementation sessions.
> The agent MUST read this at the start of each session and append new entries at the end.

## How to Use This File

**At session start**: Read this entire file to absorb prior learnings.
**At session end**: Append a new entry at the bottom with:
- Date
- Phase/module worked on
- What was discovered (bugs, patterns, reference code surprises)
- What worked well
- What didn't work (and the fix)
- Config values that were tuned and why
- Integration gotchas

---

## Learnings

### [2026-03-22] — Skill Created

**Phase**: Skill design / specification

**Key findings from reference codebase analysis (`planet_shifting_remedies_analysis.md`)**:

1. **Extended PUCCA_GHARS vs single Pakka Ghar**: The remedy engine uses a wider set of
   "safe houses" (e.g., Saturn → [7,8,10,11]) while the StrengthEngine uses only the single
   canonical Pakka Ghar (Saturn → 10). These serve different purposes — don't conflate them.

2. **Masnui check is mandatory**: Both standard AND masnui planets must be checked for
   enemy occupancy in target houses. Missing this caused silent bugs in legacy code.

3. **Birth × Annual intersection**: A house must be safe in BOTH the birth chart AND the
   specific annual chart. Birth gives the "lifelong potential", annual gives "current safety".

4. **Goswami scores are additive**: Multiple rules can stack. The CRITICAL tier (≥60) is
   naturally reached only by genuinely critical combinations (e.g., H8 unblock = +50 alone
   plus any preference = ≥60).

5. **Old integration gap identified**: In the legacy code, `remedy_engine.py` computed
   strength projections but `probability_model.py` read ONLY raw chart strength — remedies
   never actually increased P(event). The new model fixes this via the Tvp boost path (Phase D).

6. **items_resolver integration**: `generate_remedy_hints()` needs `items_resolver.get_planet_items(planet, house)`
   to return the physical article list. Verify the method signature matches before calling.

7. **Backward compatibility design**: `remedy_engine=None` default in `PredictionTranslator.__init__()`
   means zero breaking changes to existing callers. Phase C is purely additive.

**Config insight**:
- All 13 `remedy.*` constants should be in `model_defaults.json` flat (no nesting)
- Use `config.get("remedy.shifting_boost")` — same pattern as other config keys

**What to do in first session**:
1. Read this learnings file ✓
2. Read progress.md ✓  
3. Read decisions.md ✓
4. Then start Phase A: add config keys → run test_config.py -k "remedy"

*(Future entries will be appended below)*

### [2026-03-22] — Implementation Completed
**Phases**: A, B, C, D, E
**What was discovered**:
1. Residual factor applies to the *current* year's total strength as well, not just carry-forward. Formula: `total = base + boost + residual`.
2. Probability capping constraint: When testing integration for TVP boosts, if the base probability calculation natively hits the `cap_upper` limit (0.95) due to high `annual_magnitude`, the `Tvp_base` boost appears to have no effect. Base magnitudes must be kept low enough (<0.95) to observe the multiplier correctly working in integration tests.

**Integration gotchas**:
- `PredictionTranslator._generate_remedies` uses `remedy_engine` to parse `get_year_shifting_options`, but must filter the options strictly to the specific `ClassifiedEvent.planet` to prevent generating confusing or irrelevant generic hints about other planets during translation.
