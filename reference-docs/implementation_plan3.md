# Fix Missing Lal Kitab Grammar Features in Grammar Analyser

## Background

After comparing the OLD reference codebase (`D:\astroq-mar26`) against the NEW `grammar_analyser.py`, **5 major grammar features are missing or partially implemented**. These need to be: (1) documented in `lk_prediction_model_v2.md`, then (2) test-driven into `grammar_analyser.py`.

---

## Gap Analysis Summary

| Gap | Old Reference | New Code | Status |
|-----|--------------|----------|--------|
| **Mangal Badh counter rules** | 17 rules (inc + dec) in `Mars_special_rules.py` | 4 simplified rules | ❌ Partial |
| **Disposition rules** | 16 rules in `global_birth_yearly_strength_additional_checks.py` | 4 hardcoded rules | ❌ Partial |
| **BilMukabil detection** | Natural friends + sig aspect + enemy in foundational house | Only 100% aspect + enemy | ❌ Wrong logic |
| **Mangal Badh strength formula** | `counter / 16.0` divisor | `counter / 5.0` divisor | ❌ Wrong value |
| **Sleeping Planet detection** | Uses `get_houses_aspected_by_planet()` aspect map | Uses `len(aspects) > 0` | ⚠️ Imprecise |

---

## Proposed Changes

---

### Section A: Model Specification Document

#### [MODIFY] [lk_prediction_model_v2.md](file:///d:/astroq-v2/.antigravity/skills/lk-prediction-model/resources/lk_prediction_model_v2.md)

Add a **Section 14: Complete Grammar Feature Reference** that documents:

1. **Mangal Badh — All 17 Rules** (from `Mars_special_rules.py`)
   - 13 increment conditions + 4 decrement conditions
   - Formula: `new_mars_strength = current * (1 + counter/16.0)` for reduction

2. **Disposition Rules — All 16 Rules** (from `global_birth_yearly_strength_additional_checks.py`)
   - Types: `planet_in_house` and `any_of_houses_for_planet`
   - Effect direction: Good (additive) vs Bad (subtractive)
   - The causer planet's absolute strength is the adjustment amount

3. **BilMukabil — 3-Step Detection** (from `global_birth_yearly_grammer_rules.py`)
   - Step 1: p1 and p2 must be **natural friends** (from `RELATIONSHIPS` table)
   - Step 2: Either planet must cast a **significant aspect** (100%, 50%, 25%) on the other
   - Step 3: An enemy of either must be in a **foundational house** of the other

4. **Sleeping Planet — Aspect-Map Logic** (from `check_sleeping_planet()`)
   - Use canonical `HOUSE_ASPECT_MAP` (H1→H7, H3→H9,H11, etc.)
   - Planet is sleeping if not in Pakka Ghar AND no planets exist in any house it aspects

5. **Mangal Badh Divisor Fix**
   - Old code: `counter / 16.0`
   - Must be applied post-disposition-rules (last step)

---

### Section B: Implementation — Grammar Analyser

#### [MODIFY] [grammar_analyser.py](file:///d:/astroq-v2/backend/astroq/lk_prediction/grammar_analyser.py)

**Change 1: `detect_mangal_badh()` — Add all 17 rules**

Replace the 4-rule simplified version with the complete set from `Mars_special_rules.py`:

```python
# INCREMENT rules (13):
# R1: Sun+Saturn conjunct
# R2: Sun does NOT aspect Mars
# R3: Moon does NOT aspect Mars  
# R4: Mercury in H6, Ketu in H6
# R5: Mars+Mercury conjunct OR Mars+Ketu conjunct
# R6: Ketu in H1
# R7: Ketu in H8
# R8: Mars in H3
# R9: Venus in H9
# R10: Sun in H6/H7/H10/H12
# R11: Mars in H6
# R12: Mercury in H1/H3/H8
# R13: Rahu in H5/H9
# + 4 more duplications for sun/moon not aspecting
# DECREMENT rules (4):
# D1: Sun+Mercury conjunct
# D2: Mars in H8 AND Mercury in H8
# D3: Sun in H3 AND Mercury in H3
# D4: Moon in H1/H2/H3/H4/H8/H9
```

**Change 2: `detect_dispositions()` — Add all 16 disposition rules**

Add the full set from `lal_kitab_planet_disposition_rules` with correct condition types:

```python
# planet_in_house type rules:
# Jupiter H7 → spoils Venus
# Rahu H11 → spoils Jupiter
# Rahu H12 → spoils Jupiter
# Sun H6 → spoils Saturn
# Sun H10 → spoils Mars + Ketu
# Sun H11 → spoils Mars
# Moon H6 → spoils Mars, helps Venus
# Venus H9 → spoils Mars

# any_of_houses type rules:
# Moon H1/H3/H8 → helps Mars
# Venus H2/H5/H12 → spoils Jupiter
# Mercury H3/H6/H8/H12 → spoils Moon
# Mercury H2/H5/H9 → spoils Jupiter
# Saturn H4/H6/H10 → spoils Moon
# Rahu H2/H5/H6/H9 → spoils Jupiter
# Ketu H11/H12 → spoils Jupiter
# Ketu H11/H12 → spoils Mars, helps Venus
```

**Change 3: `detect_bilmukabil()` — Fix 3-point logic**

Replace the current 2-way enemy-aspect check with the proper 3-step check:
1. Must be natural friends (using `NATURAL_RELATIONSHIPS` dict)
2. Must have at least one significant aspect (100%, 50%, 25%) mutual
3. Must have an enemy of either in the foundational houses of the other

**Change 4: `detect_sleeping()` — Use canonical aspect map**

Replace `len(aspects) > 0` check with the canonical house-aspect map lookup to find if a planet actually casts to occupied houses:

```python
HOUSE_ASPECT_MAP = {
    1: [7], 2: [6], 3: [9, 11], 4: [10], 5: [9],
    6: [12], 7: [1], 8: [], 9: [3, 5], 10: [4],
    11: [3, 5], 12: [6]
}
```

**Change 5: `_apply_adjustments()` — Fix Mangal Badh divisor**

Change the Mangal Badh reduction formula from using config `mangal_badh_divisor` (5.0) to the correct formula from the reference:
```python
# Old (wrong):
delta = -(abs(total) - (abs(total) / self.w_mangal))  # 5.0

# New (correct):
mangal_counter = chart.get("mangal_badh_count", 0)
reduction = abs(total) * (1 + mangal_counter / 16.0)
delta = -reduction
```

The `_apply_adjustments` needs the chart's `mangal_badh_count` passed in addition to the boolean flag.

---

### Section C: Tests

#### [MODIFY] [test_grammar_analyser.py](file:///d:/astroq-v2/backend/tests/lk_prediction/test_grammar_analyser.py)

Add new tests:

```
test_mangal_badh_all_13_increment_rules          # All 13 conditions checked
test_mangal_badh_decrement_sun_mercury_together  # D1: Sun+Mercury reduces counter  
test_mangal_badh_decrement_moon_in_good_house    # D4: Moon in 1/2/3/4/8/9 reduces
test_mangal_badh_formula_uses_divisor_16         # strength reduced by counter/16.0
test_disposition_jupiter_h7_spoils_venus         # Venus strength reduced
test_disposition_rahu_h11_spoils_jupiter         # Jupiter strength reduced
test_disposition_moon_h1_h3_h8_helps_mars        # Mars strength boosted (any-of-houses)
test_disposition_mercury_h3_h6_h8_h12_spoils_moon# Moon strength reduced
test_disposition_ketu_h11_spoils_mars            # Mars reduced, Venus boosted
test_bilmukabil_requires_natural_friends         # p1+p2 must be friends
test_bilmukabil_requires_foundational_enemy      # enemy must be in foundational house
test_bilmukabil_not_triggered_wrong_relationship # non-friends never BilMukabil
test_sleeping_uses_aspect_map_not_just_list      # planet with H in [2] aspects H6, if H6 occupied → awake
```

---

## Verification Plan

### Automated Tests

All tests are in `backend/tests/lk_prediction/`:

```bash
# From d:\astroq-v2\backend
cd d:\astroq-v2\backend

# Run only the grammar tests (fast)
pytest tests/lk_prediction/test_grammar_analyser.py -v

# Run all lk_prediction tests to check no regressions
pytest tests/lk_prediction/ -v --tb=short
```

**Expected:** All existing 16 tests remain green. All ~13 new tests pass (total ≥ 29 tests).
