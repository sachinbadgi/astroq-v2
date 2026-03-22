# Planet Shifting & Remedies — Old Codebase Analysis + New Model

> **Source Files Analysed** (D:\astroq-mar26)
> - `astroq/remedy_engine.py` (397 L) — Legacy shifting engine
> - `astroq/lal_kitab/remedy_modeller.py` (452 L) — LK-aware shifting engine
> - `astroq/lal_kitab/enricher.py` (1596 L) — Chart enrichment + shifting integration
> - `astroq/lal_kitab/rlm_engine.py` (529 L) — RLM execution context (remedy helpers)
> - `astroq/lal_kitab/probability_model.py` (1053 L) — Probability engine (shifting boost pathway)

---

## 1. What Planet Shifting Is

In Lal Kitab, **Planet Shifting (Graha Parivartan)** is a *remedy* — physically moving articles associated with a planet to the room/direction corresponding to a "better" house. The astrologer identifies the **recommended target house** for each planet, then prescribes articles (e.g., "keep silver in bedroom = Moon shifted to H4").

The engine's job is to:
1. **Identify** which houses are recommended for each planet in both the birth and annual chart.
2. **Filter** out houses where the planet's enemies already sit ("blocked").
3. **Rank** the safe matches using a priority system (Goswami rules).
4. **Project** the strength/probability boost the remedy would provide over a lifetime.
5. **Surface** the ranked options in the prediction output as `remedy_hints`.

---

## 2. Old Codebase — Complete Logic Map

### 2.1 Reference Constants (shared across both engines)

```python
# Pucca Ghars — owned/foundational houses per planet
PUCCA_GHARS = {
    "Sun":     [1, 5],
    "Moon":    [2, 4],
    "Mars":    [3, 8, 10],
    "Mercury": [6, 7],
    "Jupiter": [2, 4, 5, 9, 11, 12],
    "Venus":   [2, 7, 12],
    "Saturn":  [7, 8, 10, 11],
    "Rahu":    [3, 6, 12],
    "Ketu":    [6, 9, 12],
}

# Exaltation houses per planet
EXALTATION_HOUSES = {
    "Sun":     [1],   "Moon":    [2],   "Mars":  [10],  "Mercury": [6],
    "Jupiter": [4],   "Venus":   [12],  "Saturn": [7],
    "Rahu":   [3, 6], "Ketu":   [9, 12],
}

# Enemies (blocking set)
ENEMIES = {
    "Sun":     ["Saturn", "Venus", "Rahu", "Ketu"],
    "Moon":    ["Rahu", "Ketu"],
    "Mars":    ["Mercury", "Ketu"],
    "Mercury": ["Moon"],
    "Jupiter": ["Mercury", "Venus"],
    "Venus":   ["Sun", "Moon", "Rahu"],
    "Saturn":  ["Sun", "Moon", "Mars"],
    "Rahu":    ["Sun", "Venus", "Mars", "Moon", "Ketu"],
    "Ketu":    ["Moon", "Mars", "Rahu"],
}

# Masnui (artificial) planets map to their base planet for enemy checks
MASNUI_TO_STANDARD = {
    "Artificial Jupiter": "Jupiter", "Artificial Sun": "Sun",
    "Artificial Moon": "Moon",       "Artificial Venus": "Venus",
    "Artificial Mars (Auspicious)": "Mars", "Artificial Mars (Malefic)": "Mars",
    "Artificial Mercury": "Mercury", "Artificial Saturn (Like Ketu)": "Saturn",
    "Artificial Saturn (Like Rahu)": "Saturn",
    "Artificial Rahu (Debilitated Rahu)": "Rahu",
    "Artificial Rahu (Exalted Rahu)": "Rahu",
    "Artificial Ketu (Exalted Ketu)": "Ketu",
    "Artificial Ketu (Debilitated Ketu)": "Ketu",
}
```

> **Key insight**: `PUCCA_GHARS` here uses the *extended* list (e.g., Saturn → [7,8,10,11]), NOT the single `PLANET_PAKKA_GHAR` used in the StrengthEngine (Saturn → 10). These are remedially safe houses, not just the single Pakka Ghar.

---

### 2.2 Step 1 — Identify Recommended Houses

```
Base Recs = PUCCA_GHARS[planet] ∪ EXALTATION_HOUSES[planet]   (sorted, deduplicated)
```

For each base-rec house:
- Check all standard planets in the chart (`planets_in_houses`)
- Check all Masnui planets in the chart (`masnui_grahas_formed`) — map to base type
- If any enemy of `planet` is in that house → mark as **BLOCKED** with reason
- Otherwise → mark as **SAFE**

```python
def get_safe_houses(planet, planets_in_houses, masnui_list) -> (safe_houses, conflicts):
    base_recs = sorted(set(PUCCA_GHARS.get(planet,[]) + EXALTATION_HOUSES.get(planet,[])))
    enemies = ENEMIES.get(planet, [])
    safe, conflicts = [], {}
    for h in base_recs:
        blockers = [p for p,d in planets_in_houses.items() if d["house"]==h and p in enemies]
        blockers += [m["name"] for m in masnui_list
                     if m["house"]==h and MASNUI_TO_STANDARD.get(m["name"]) in enemies]
        if blockers: conflicts[h] = f"Blocked by {', '.join(blockers)}"
        else: safe.append(h)
    return safe, conflicts
```

---

### 2.3 Step 2 — Intersect Birth & Annual Chart Results

For each age (year of life):
```
birth_safe    = get_safe_houses(planet, birth_chart)
annual_safe   = get_safe_houses(planet, annual_chart)
safe_matches  = birth_safe ∩ annual_safe          # only houses safe in BOTH
other_options = PUCCA_GHARS∪EXALTATION - safe_matches  # context info only
```

Annual chart conflicts are merged with birth chart conflicts into a single `conflict_map`.

---

### 2.4 Step 3 — Goswami Priority Ranking

Each safe house gets a **score** (base = 10), adjusted by:

| Rule | Condition | Score Adjustment |
|------|-----------|-----------------|
| House Preference H9 | Target house == 9 | +30 |
| House Preference H2 | Target house == 2 | +20 |
| House Preference H4 | Target house == 4 | +10 |
| Unblocking H2 [P148] | Planet is in annual H8 AND target is H2 or H4 | +50 |
| Pair Companion [P263] | Companion planet is in same house AND target is a known pair target | +40 |
| Doubtful (Maski) | Planet has "Doubtful" state in annual chart | +20 |

**Rank tiers**:
- ≥ 60 → `CRITICAL`
- ≥ 40 → `High`
- ≥ 20 → `Medium`
- < 20  → `Low`

```python
GOSWAMI_PAIR_TARGETS = {
    ("Moon", "Jupiter"): [2, 4, 10],   # [P263]
    ("Sun", "Moon"):     [1, 2, 4],
    ("Mars", "Saturn"):  [8, 10],
}
HOUSE_PREFERENCE_WEIGHTS = {9: 30, 2: 20, 4: 10}
```

---

### 2.5 Step 4 — Lifetime Strength Projection

Constants:
```python
SHIFTING_BOOST        = 2.5   # strength_total increase when remedy applied in a year
RESIDUAL_IMPACT_FACTOR = 0.05  # 5% of boost carries forward permanently each year
```

Algorithm (per planet, per age):
```
base_strength[age]     = chart[age].planets[planet].strength_total
current_year_boost     = SHIFTING_BOOST if remedy applied this year (safe=True)
                       = SHIFTING_BOOST * 0.5 if remedy applied (safe=False)
cumulative_residual   += boost * RESIDUAL_IMPACT_FACTOR (when remedy applied)
total_strength[age]    = base_strength + current_year_boost + cumulative_residual
```

Outputs per planet: `baseline[]`, `remedy[]`, `cumulative_baseline[]`, `cumulative_remedy[]`

---

### 2.6 Step 5 — Life Area Aggregation

```python
LIFE_AREA_GROUPS = {
    "Wealth & Prosperity": ["Jupiter", "Venus", "Mercury"],
    "Health & Vitality":   ["Sun", "Mars", "Saturn"],
    "Career & Status":     ["Sun", "Mars", "Jupiter"],
    "Relationships & Joy": ["Venus", "Moon", "Jupiter"],
}
```

For each area, summing from `current_age` to 75:
- `fixed_fate`              = sum of baseline strengths
- `current_remediation`     = sum(remedy) - sum(baseline) for applied remedies
- `untapped_potential`      = sum(max_all_safe_remedy) - sum(applied_remedy)
- `remediation_efficiency`  = (applied - baseline) / (max - baseline + 0.1) × 100%

---

### 2.7 Step 6 — Integration with Probability Engine

Old `probability_model.py` uses shifting boost **indirectly** via `strength_total` — if remedies have been applied, the enriched annual chart's `strength_total` is higher, which feeds into:
- `calculate_natal_propensity()` — higher strength → higher sigmoid → higher Pn
- `calculate_varshaphal_trigger()` — higher annual strength → higher Tvp

The `LKExecutionContext.get_remedy_options()` surfaces the safe houses for each year to the LLM/RLM context. The LLM then generates the `remedy_hints` text from these options.

---

### 2.8 Step 7 — Remedy Output in Predictions

In `remedy_modeller.get_llm_remedy_summary()`:
- Options are sorted CRITICAL → High → Medium → Low
- Each safe match includes the **planet articles** from `items_resolver.get_planet_items(planet, house)`
- Output is a markdown string with rationale and action items

In the new model, these should map to `LKPrediction.remedy_hints` (list[str]).

---

## 3. What Was Missing / Not Integrated

| Gap | Location | Impact |
|-----|----------|--------|
| Shifting boost not reflected back into probability | `remedy_engine.py` computes projections but `probability_model.py` reads raw chart strength | Applied remedies don't increase P(event) |
| No config keys for SHIFTING_BOOST / RESIDUAL_IMPACT_FACTOR | Hardcoded constants | Can't tune |
| Remedy output not connected to `LKPrediction.remedy_hints` | `prediction_translator.py` does not call remedy_modeller | remedy_hints always empty |
| Goswami pair targets & house preference not tunable | Hardcoded | Can't tune |
| No lifetime projection summary in prediction output | Only exposed via rlm_engine Python helpers | User can't see it without asking |

---

## 4. New Model — Efficient Implementation

### 4.1 New Module: `remedy_engine.py`

**File**: `backend/astroq/lk_prediction/remedy_engine.py`

#### Constants (all config-driven)

Config keys to add to `model_defaults.json`:

```json
{
  "remedy.shifting_boost":         2.5,
  "remedy.residual_impact_factor": 0.05,
  "remedy.safe_shifting_multiplier": 1.0,
  "remedy.unsafe_shifting_multiplier": 0.5,
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

#### Core Data Structures

```python
@dataclass
class ShiftingOption:
    house: int
    score: int           # Goswami score
    rank: str            # "CRITICAL" | "High" | "Medium" | "Low"
    rationale: str
    articles: list[str]  # from items_resolver

@dataclass
class PlanetShiftingResult:
    planet: str
    birth_house: int
    annual_house: int
    safe_matches: list[ShiftingOption]   # sorted by score desc
    other_options: list[int]
    conflicts: dict[int, str]
    llm_hint: str                        # one-line natural language

@dataclass
class LifetimeStrengthProjection:
    ages: list[int]
    planets: dict[str, dict]             # planet → {baseline, remedy, cum_baseline, cum_remedy}

@dataclass
class LifeAreaSummary:
    area: str
    fixed_fate: float
    current_remediation: float
    untapped_potential: float
    max_remediable: float
    remediation_efficiency: float        # percentage
```

#### API

```python
class RemedyEngine:
    def __init__(self, config: ModelConfig, items_resolver): ...

    # ── Core per-age shifting ──────────────────────────────────────
    def get_safe_houses(
        self, planet: str, enriched_chart: dict
    ) -> tuple[list[int], dict[int, str]]:
        """Returns (safe_house_list, conflict_map)."""

    def get_year_shifting_options(
        self, birth_chart: dict, annual_chart: dict, age: int
    ) -> dict[str, PlanetShiftingResult]:
        """Per-planet shifting options for a single age."""

    def rank_safe_houses(
        self, planet: str, safe_houses: list[int],
        annual_chart: dict, annual_planets: dict
    ) -> list[ShiftingOption]:
        """Score + rank each safe house via Goswami rules."""

    # ── Lifetime simulation ───────────────────────────────────────
    def simulate_lifetime_strength(
        self,
        birth_chart: dict,
        annual_charts: dict[int, dict],
        applied_remedies: list[dict] = None,
    ) -> LifetimeStrengthProjection:
        """Projects strength[planet][age] baseline vs remedied."""

    def analyze_life_area_potential(
        self,
        birth_chart: dict,
        annual_charts: dict[int, dict],
        applied_remedies: list[dict] = None,
        current_age: int = 1,
    ) -> dict[str, LifeAreaSummary]:
        """Returns life area summaries from current_age to 75."""

    # ── Output helpers ────────────────────────────────────────────
    def generate_remedy_hints(
        self, year_options: dict[str, PlanetShiftingResult]
    ) -> list[str]:
        """Top 3 CRITICAL/High priority hints → list[str] for LKPrediction."""

    def get_llm_remedy_summary(
        self, birth_chart: dict, annual_chart: dict, age: int
    ) -> str:
        """Formatted markdown roadmap (for RLM context)."""
```

---

### 4.2 Processing Logic (Compact Pseudocode)

#### `get_safe_houses(planet, chart)`
```
base_recs = sorted(set(PUCCA_GHARS[planet] + EXALTATION[planet]))
pih = chart.planet_analysis OR chart.planets_in_houses
masnui = chart.masnui_grahas.masnui OR []
enemies = ENEMIES[planet]

for h in base_recs:
    blockers  = [p for p in pih if pih[p].house==h and p in enemies]
    blockers += [m.name for m in masnui if m.house==h 
                  and MASNUI_MAP.get(m.name) in enemies]
    if blockers: conflicts[h] = f"Blocked by {blockers}"
    else: safe.append(h)

return safe, conflicts
```

#### `get_year_shifting_options(birth, annual, age)`
```
birth_safe, b_conflicts = get_safe_houses(planet, birth)
annual_safe, a_conflicts = get_safe_houses(planet, annual)
safe_matches = birth_safe ∩ annual_safe
conflict_map = merge(b_conflicts, a_conflicts, prefix "Birth:" / "Annual:")
ranked = rank_safe_houses(planet, safe_matches, annual, annual_pih)
return PlanetShiftingResult(planet, birth_house, annual_house, ranked, ...)
```

#### `rank_safe_houses(planet, safe_houses, annual_chart, annual_pih)`
```
for h in safe_houses:
    score = 10
    if h in {9:30, 2:20, 4:10}: score += weight
    if annual_pih[planet].house == 8 and h in [2,4]: score += 50  # unblock
    for pair, targets in GOSWAMI_PAIRS:
        if planet in pair:
            other = pair - {planet}
            if annual_pih[other].house == annual_house and h in targets:
                score += 40
    if "Doubtful" in annual_pih[planet].states: score += 20
    rank = "CRITICAL" if score>=60 else "High" if score>=40 else "Medium" if score>=20 else "Low"
    articles = items_resolver.get_planet_items(planet, h)
    options.append(ShiftingOption(h, score, rank, rationale, articles))
return sorted(options, key=score, reverse=True)
```

#### `simulate_lifetime_strength(birth, annual_charts, applied_remedies)`
```
for planet in STANDARD_PLANETS:
    residual = 0.0
    for age in sorted(annual_charts.keys()):
        base = annual_charts[age].planets[planet].strength_total
        boost = 0.0
        for rem in applied_remedies:
            if rem.planet==planet and rem.age==age:
                boost = SHIFTING_BOOST * (1.0 if rem.is_safe else 0.5)
                residual += boost * RESIDUAL_IMPACT_FACTOR
        total = base + boost + residual
        record(planet, age, base, total)
```

#### `generate_remedy_hints(year_options) → list[str]`
```
all_options = flatten year_options into [(planet, ShiftingOption)]
filtered    = options where rank in [CRITICAL, High]
sorted_by_score = sort descending
take top 3
return [f"Shift {planet} to House {h}: {rationale}. Articles: {articles}" ...]
```

---

### 4.3 Integration into PredictionTranslator

In `prediction_translator.py` → `translate()`:

```python
# After building ClassifiedEvent, add remedy hints
year_options = self.remedy_engine.get_year_shifting_options(
    birth_chart=enriched_natal,
    annual_chart=enriched_annual,
    age=event.peak_age
)
remedy_applicable = any(r.safe_matches for r in year_options.values())
remedy_hints = self.remedy_engine.generate_remedy_hints(year_options)

prediction = LKPrediction(
    ...,
    remedy_applicable=remedy_applicable,
    remedy_hints=remedy_hints,
)
```

---

### 4.4 Integration into ProbabilityEngine (Shifting Boost Path)

The **correct** integration (fixing the old codebase gap):

In `ProbabilityEngine.calculate_varshaphal_trigger()`, after computing `Tvp_base`:

```python
# If a remedy has been applied to this planet in this year, boost Tvp
if applied_remedies.get(planet, {}).get(age, {}).get("is_safe"):
    Tvp_base *= (1.0 + cfg.get("remedy.shifting_boost") / 10.0)
    # i.e., +2.5/10 = +25% to Tvp when remedy is active
```

This means applied remedies directly increase event probability, closing the old integration gap.

---

### 4.5 New Config Keys in `model_defaults.json`

```json
"remedy.shifting_boost":             2.5,
"remedy.residual_impact_factor":     0.05,
"remedy.safe_multiplier":            1.0,
"remedy.unsafe_multiplier":          0.5,
"remedy.tvp_boost_per_unit":         0.1,
"remedy.goswami_h9_weight":          30,
"remedy.goswami_h2_weight":          20,
"remedy.goswami_h4_weight":          10,
"remedy.goswami_unblock_weight":     50,
"remedy.goswami_pair_weight":        40,
"remedy.goswami_doubtful_weight":    20,
"remedy.critical_score_threshold":   60,
"remedy.high_score_threshold":       40,
"remedy.medium_score_threshold":     20
```

---

## 5. TDD Tests

### File: `backend/tests/lk_prediction/test_remedy_engine.py`

```
test_get_safe_houses_no_enemies_returns_all_base_recs
test_get_safe_houses_enemy_in_target_returns_blocked
test_get_safe_houses_masnui_enemy_in_target_returns_blocked
test_get_safe_houses_empty_chart_returns_all_recs

test_get_year_shifting_options_intersection_of_birth_and_annual
test_get_year_shifting_options_no_overlap_returns_empty_safe_matches
test_get_year_shifting_options_conflict_map_merges_both_charts

test_rank_safe_houses_h9_scores_higher_than_h4
test_rank_safe_houses_unblock_rule_gives_critical
test_rank_safe_houses_pair_companion_boosts_score
test_rank_safe_houses_doubtful_planet_boosts_rank
test_rank_safe_houses_sorted_descending_by_score

test_simulate_lifetime_strength_baseline_matches_chart_strengths
test_simulate_lifetime_strength_boost_applied_correct_year
test_simulate_lifetime_strength_residual_carries_forward
test_simulate_lifetime_strength_unsafe_remedy_half_boost

test_analyze_life_area_potential_max_exceeds_applied
test_analyze_life_area_potential_efficiency_correct_percentage

test_generate_remedy_hints_returns_top_3_critical_high
test_generate_remedy_hints_includes_planet_and_house
test_generate_remedy_hints_empty_when_no_safe_matches

test_remedy_engine_config_shifting_boost_used
test_remedy_engine_config_residual_factor_used
```

---

## 6. Implementation Order

```
Phase A (Module Only):
  1. Add config keys to model_defaults.json
  2. Write tests (test_remedy_engine.py)
  3. Implement remedy_engine.py
  4. Green all 22 tests

Phase B (Integration):
  5. Inject remedy_engine into PredictionTranslator.__init__
  6. Call generate_remedy_hints() in translate() method
  7. Optional: add Tvp boost path in ProbabilityEngine

Phase C (Verification):
  8. Run pipeline on Sachin chart → verify remedy_hints populated
  9. Benchmark — confirm hit rate unaffected (remedies are additive only)
```

---

## 7. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Separate `RemedyEngine` class** | Clean module boundary; injectable into translator |
| **Config-driven constants** | SHIFTING_BOOST, RESIDUAL etc. tunable without code changes |
| **`get_safe_houses()` checks both standard AND masnui planets** | Old code did this; masnui in a target house can block shifting |
| **Intersection of birth & annual** | Birth determines lifelong potential; annual determines current safety |
| **Goswami scores are additive** | Multiple conditions can compound; allows CRITICAL to dominate output |
| **`generate_remedy_hints()` returns top-3 only** | Avoid overwhelming the prediction with low-priority options |
| **Tvp boost is optional (Phase B)** | Separates functional from probabilistic integration; benchmark first |
| **Extended PUCCA_GHARS** | Remedy shifting uses a wider set of safe houses than the single Pakka Ghar used in strength scoring |
