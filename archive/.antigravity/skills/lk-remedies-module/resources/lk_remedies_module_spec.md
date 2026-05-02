# Lal Kitab Remedies Module — Complete Specification

> Build from scratch using autoresearch + superpowers TDD approach.
> This document is the single source of truth for the RemedyEngine.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Reference Constants](#2-reference-constants)
3. [Config Keys](#3-config-keys)
4. [Data Contracts](#4-data-contracts)
5. [RemedyEngine API](#5-remedyengine-api)
6. [Algorithm Specifications](#6-algorithm-specifications)
7. [Integration Points](#7-integration-points)
8. [Test Plan (Superpowers TDD)](#8-test-plan-superpowers-tdd)
9. [Implementation Order](#9-implementation-order)
10. [Key Design Decisions](#10-key-design-decisions)

---

## 1. System Overview

### What Planet Shifting Is

In Lal Kitab, **Planet Shifting (Graha Parivartan)** is a remedy — physically moving articles
associated with a planet to the room/direction corresponding to a "better" house. The engine's job:

1. **Identify** recommended target houses per planet (Pucca Ghars + Exaltation)
2. **Filter** out houses where the planet's enemies already sit ("blocked")
3. **Rank** safe matches using Goswami priority rules
4. **Project** the strength/probability boost the remedy would provide over a lifetime
5. **Surface** ranked options in `LKPrediction.remedy_hints`

### Design Principles

- **Config-Driven**: Every scaling constant in `model_defaults.json`
- **Test-First**: Tests written BEFORE implementation
- **Integration-Complete**: Hooks into both `PredictionTranslator` and `ProbabilityEngine`
- **No Stubs**: All logic fully implemented — no empty returns

### Position in Pipeline

```
PredictionTranslator.translate()
    └─→ RemedyEngine.get_year_shifting_options()
        └─→ RemedyEngine.rank_safe_houses()
            └─→ RemedyEngine.generate_remedy_hints()
                └─→ LKPrediction.remedy_hints

ProbabilityEngine.calculate_varshaphal_trigger()
    └─→ if applied_remedies[planet][age].is_safe:
            Tvp_base *= (1 + remedy.tvp_boost_per_unit)
```

---

## 2. Reference Constants

These constants are derived from the legacy `remedy_engine.py` and `remedy_modeller.py`.
They are config-driven in the new model (see Section 3).

### 2.1 Extended Pucca Ghars (Remedially Safe Houses)

> **IMPORTANT**: This is the EXTENDED set used for remedy shifting, NOT the single
> `PLANET_PAKKA_GHAR` used in `StrengthEngine`. They serve different purposes.

```python
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
```

### 2.2 Exaltation Houses

```python
EXALTATION_HOUSES = {
    "Sun":     [1],
    "Moon":    [2],
    "Mars":    [10],
    "Mercury": [6],
    "Jupiter": [4],
    "Venus":   [12],
    "Saturn":  [7],
    "Rahu":    [3, 6],
    "Ketu":    [9, 12],
}
```

### 2.3 Enemies (Blocking Set)

```python
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
```

### 2.4 Masnui to Standard Planet Mapping

```python
MASNUI_TO_STANDARD = {
    "Artificial Jupiter": "Jupiter",
    "Artificial Sun": "Sun",
    "Artificial Moon": "Moon",
    "Artificial Venus": "Venus",
    "Artificial Mars (Auspicious)": "Mars",
    "Artificial Mars (Malefic)": "Mars",
    "Artificial Mercury": "Mercury",
    "Artificial Saturn (Like Ketu)": "Saturn",
    "Artificial Saturn (Like Rahu)": "Saturn",
    "Artificial Rahu (Debilitated Rahu)": "Rahu",
    "Artificial Rahu (Exalted Rahu)": "Rahu",
    "Artificial Ketu (Exalted Ketu)": "Ketu",
    "Artificial Ketu (Debilitated Ketu)": "Ketu",
}
```

### 2.5 Goswami Pair Targets

```python
GOSWAMI_PAIR_TARGETS = {
    ("Moon", "Jupiter"): [2, 4, 10],   # [P263]
    ("Sun", "Moon"):     [1, 2, 4],
    ("Mars", "Saturn"):  [8, 10],
}
```

### 2.6 Life Area Groups

```python
LIFE_AREA_GROUPS = {
    "Wealth & Prosperity": ["Jupiter", "Venus", "Mercury"],
    "Health & Vitality":   ["Sun", "Mars", "Saturn"],
    "Career & Status":     ["Sun", "Mars", "Jupiter"],
    "Relationships & Joy": ["Venus", "Moon", "Jupiter"],
}
```

---

## 3. Config Keys

All the following keys must be added to `backend/data/model_defaults.json`
under their existing root structure (no nesting required — flat keys).

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

## 4. Data Contracts

### 4.1 ShiftingOption

```python
@dataclass
class ShiftingOption:
    house: int
    score: int           # Goswami composite score
    rank: str            # "CRITICAL" | "High" | "Medium" | "Low"
    rationale: str       # Human-readable reason for this ranking
    articles: list[str]  # Physical articles from items_resolver (planet+house)
```

### 4.2 PlanetShiftingResult

```python
@dataclass
class PlanetShiftingResult:
    planet: str
    birth_house: int
    annual_house: int
    safe_matches: list[ShiftingOption]   # Sorted by score desc
    other_options: list[int]             # Houses safe in birth only (informational)
    conflicts: dict[int, str]            # house → "Birth: Blocked by Saturn" etc.
    llm_hint: str                        # One-line natural language summary
```

### 4.3 LifetimeStrengthProjection

```python
@dataclass
class LifetimeStrengthProjection:
    ages: list[int]
    planets: dict[str, dict]
    # planet → {
    #   "baseline": list[float],      # strength_total without remedy
    #   "remedy": list[float],        # strength_total with remedy applied
    #   "cum_baseline": list[float],  # cumulative baseline
    #   "cum_remedy": list[float],    # cumulative with remedies
    # }
```

### 4.4 LifeAreaSummary

```python
@dataclass
class LifeAreaSummary:
    area: str
    fixed_fate: float               # Sum of baseline strengths from current_age to 75
    current_remediation: float      # Sum(remedy) - sum(baseline) for applied remedies
    untapped_potential: float       # Sum(max_all_safe_remedy) - sum(applied_remedy)
    max_remediable: float           # Max achievable cumulative remedy strength
    remediation_efficiency: float   # (applied - baseline) / (max - baseline + 0.1) × 100
```

### 4.5 Applied Remedy Input Format

When passed to `simulate_lifetime_strength()` or `calculate_varshaphal_trigger()`:

```python
applied_remedies = [
    {
        "planet": "Jupiter",
        "age": 28,
        "target_house": 4,
        "is_safe": True,   # False = unsafe match (half boost)
    },
    ...
]
```

---

## 5. RemedyEngine API

### File: `backend/astroq/lk_prediction/remedy_engine.py`

```python
class RemedyEngine:
    def __init__(self, config: ModelConfig, items_resolver) -> None:
        """
        Args:
            config: ModelConfig instance (reads remedy.* keys)
            items_resolver: LKItemsResolver for planet+house article lookup
        """

    # ── Core per-age shifting ──────────────────────────────────────────────

    def get_safe_houses(
        self,
        planet: str,
        enriched_chart: dict,
    ) -> tuple[list[int], dict[int, str]]:
        """
        Returns (safe_house_list, conflict_map) for a single chart.

        Logic:
          base_recs = sorted(set(PUCCA_GHARS[planet] + EXALTATION_HOUSES[planet]))
          For each h in base_recs:
            blockers = standard enemies in h + masnui enemies in h
            if blockers: conflicts[h] = "Blocked by ..."
            else: safe.append(h)

        The enriched_chart must have either:
          - chart["planets_in_houses"][planet_name]["house"] = int
          OR
          - chart["planet_analysis"][planet_name]["house"] = int
        And optionally:
          - chart["masnui_grahas_formed"] = list of {name, house} dicts
        """

    def get_year_shifting_options(
        self,
        birth_chart: dict,
        annual_chart: dict,
        age: int,
    ) -> dict[str, PlanetShiftingResult]:
        """
        Returns per-planet {planet: PlanetShiftingResult} for a single age.

        Logic:
          For each standard planet:
            birth_safe, b_conflicts = get_safe_houses(planet, birth_chart)
            annual_safe, a_conflicts = get_safe_houses(planet, annual_chart)
            safe_matches = birth_safe ∩ annual_safe
            other_options = (birth_safe ∪ annual_safe) - safe_matches
            conflict_map = merge b_conflicts (prefix "Birth: ") + a_conflicts (prefix "Annual: ")
            ranked = rank_safe_houses(planet, safe_matches, annual_chart)
            birth_house = birth_chart.planets[planet].house
            annual_house = annual_chart.planets[planet].house
        """

    def rank_safe_houses(
        self,
        planet: str,
        safe_houses: list[int],
        annual_chart: dict,
        annual_planets: dict,
    ) -> list[ShiftingOption]:
        """
        Score and rank each safe house using Goswami rules.

        Scoring (additive, base = 10):
          + cfg.goswami_h9_weight (30) if house == 9
          + cfg.goswami_h2_weight (20) if house == 2
          + cfg.goswami_h4_weight (10) if house == 4
          + cfg.goswami_unblock_weight (50) if annual_planet.house == 8 AND h in [2, 4]
          + cfg.goswami_pair_weight (40) if planet in GOSWAMI_PAIR_TARGETS pair
                                          AND companion in same annual_house
                                          AND h in pair_targets
          + cfg.goswami_doubtful_weight (20) if "Doubtful" in annual_planet.states

        Rank thresholds:
          score >= cfg.critical_threshold (60) → "CRITICAL"
          score >= cfg.high_threshold (40)      → "High"
          score >= cfg.medium_threshold (20)    → "Medium"
          else                                  → "Low"

        Sort descending by score.
        Attach articles from items_resolver.get_planet_items(planet, house).
        """

    # ── Lifetime simulation ────────────────────────────────────────────────

    def simulate_lifetime_strength(
        self,
        birth_chart: dict,
        annual_charts: dict[int, dict],
        applied_remedies: list[dict] | None = None,
    ) -> LifetimeStrengthProjection:
        """
        Projects strength[planet][age] baseline vs remedied.

        Algorithm:
          For each planet in STANDARD_PLANETS:
            residual = 0.0
            For each age in sorted(annual_charts.keys()):
              base = annual_charts[age].planets[planet].strength_total
              boost = 0.0
              For each rem in applied_remedies where rem.planet==planet and rem.age==age:
                multiplier = cfg.safe_multiplier (1.0) if rem.is_safe else cfg.unsafe_multiplier (0.5)
                boost = cfg.shifting_boost * multiplier
                residual += boost * cfg.residual_impact_factor
              total = base + boost + residual
              record(planet, age, baseline=base, remedy=total)
        """

    def analyze_life_area_potential(
        self,
        birth_chart: dict,
        annual_charts: dict[int, dict],
        applied_remedies: list[dict] | None = None,
        current_age: int = 1,
    ) -> dict[str, LifeAreaSummary]:
        """
        Returns life area summaries from current_age to 75.

        For each life area in LIFE_AREA_GROUPS:
          fixed_fate = sum(baseline[age] for planet in area for age in range(current_age, 76))
          applied_sum = sum(remedy[age] for planet in area for age in range(current_age, 76))
          current_remediation = applied_sum - fixed_fate
          max_achievable = maximum possible if all safe options applied
          untapped_potential = max_achievable - applied_sum
          remediation_efficiency = (applied_sum - fixed_fate) / (max_achievable - fixed_fate + 0.1) * 100
        """

    # ── Output helpers ─────────────────────────────────────────────────────

    def generate_remedy_hints(
        self,
        year_options: dict[str, PlanetShiftingResult],
    ) -> list[str]:
        """
        Returns top-3 CRITICAL/High priority hints as list[str] for LKPrediction.

        Algorithm:
          options = [(planet, option) for planet in year_options
                                      for option in planet_result.safe_matches
                                      if option.rank in ("CRITICAL", "High")]
          sorted by score descending → take top 3
          hint_str = f"Shift {planet} to House {h}: {rationale}. Articles: {', '.join(articles)}"
        """

    def get_llm_remedy_summary(
        self,
        birth_chart: dict,
        annual_chart: dict,
        age: int,
    ) -> str:
        """
        Returns formatted markdown remedy roadmap (used by RLM context / LLM).

        Format:
          ## Remedy Options for Age {age}
          ### {planet}
          - **[CRITICAL]** House {h} — {rationale}
            Articles: {articles}
          ...
        """
```

---

## 6. Algorithm Specifications

### 6.1 get_safe_houses — Detailed Pseudocode

```python
def get_safe_houses(self, planet: str, chart: dict) -> tuple[list[int], dict[int, str]]:
    base_recs = sorted(
        set(PUCCA_GHARS.get(planet, []) + EXALTATION_HOUSES.get(planet, []))
    )
    # Support both chart formats
    pih = (chart.get("planet_analysis")
           or chart.get("planets_in_houses")
           or {})
    masnui_list = chart.get("masnui_grahas_formed", [])

    enemies = ENEMIES.get(planet, [])
    safe, conflicts = [], {}

    for h in base_recs:
        # Check standard planets
        blockers = [p for p, data in pih.items()
                    if data.get("house") == h and p in enemies]
        # Check masnui planets → resolve to base planet
        blockers += [m.get("name", "") for m in masnui_list
                     if m.get("house") == h
                     and MASNUI_TO_STANDARD.get(m.get("name", "")) in enemies]
        if blockers:
            conflicts[h] = f"Blocked by {', '.join(str(b) for b in blockers)}"
        else:
            safe.append(h)

    return safe, conflicts
```

### 6.2 simulate_lifetime_strength — Detailed Pseudocode

```python
def simulate_lifetime_strength(self, birth_chart, annual_charts, applied_remedies=None):
    applied_remedies = applied_remedies or []
    STANDARD_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter",
                        "Venus", "Saturn", "Rahu", "Ketu"]
    result = {}

    for planet in STANDARD_PLANETS:
        residual = 0.0
        baseline_list, remedy_list = [], []
        cum_baseline, cum_remedy = 0.0, 0.0
        cum_b_list, cum_r_list = [], []

        for age in sorted(annual_charts.keys()):
            pih = (annual_charts[age].get("planet_analysis")
                   or annual_charts[age].get("planets_in_houses")
                   or {})
            base = pih.get(planet, {}).get("strength_total", 0.0)

            boost = 0.0
            for rem in applied_remedies:
                if rem.get("planet") == planet and rem.get("age") == age:
                    mult = (self.cfg.get("remedy.safe_multiplier")
                            if rem.get("is_safe") else
                            self.cfg.get("remedy.unsafe_multiplier"))
                    boost = self.cfg.get("remedy.shifting_boost") * mult
                    residual += boost * self.cfg.get("remedy.residual_impact_factor")

            total = base + boost + residual
            baseline_list.append(base)
            remedy_list.append(total)
            cum_baseline += base
            cum_remedy += total
            cum_b_list.append(cum_baseline)
            cum_r_list.append(cum_remedy)

        result[planet] = {
            "baseline": baseline_list,
            "remedy": remedy_list,
            "cum_baseline": cum_b_list,
            "cum_remedy": cum_r_list,
        }

    return LifetimeStrengthProjection(
        ages=sorted(annual_charts.keys()),
        planets=result,
    )
```

### 6.3 generate_remedy_hints — Detailed Pseudocode

```python
def generate_remedy_hints(self, year_options: dict) -> list[str]:
    all_opts = []
    for planet, result in year_options.items():
        for opt in result.safe_matches:
            if opt.rank in ("CRITICAL", "High"):
                all_opts.append((planet, opt))

    # Sort by score descending
    all_opts.sort(key=lambda x: x[1].score, reverse=True)
    top3 = all_opts[:3]

    hints = []
    for planet, opt in top3:
        articles_str = ", ".join(opt.articles) if opt.articles else "keep articles nearby"
        hint = (f"Shift {planet} to House {opt.house} [{opt.rank}]: "
                f"{opt.rationale}. Articles: {articles_str}")
        hints.append(hint)

    return hints
```

---

## 7. Integration Points

### 7.1 PredictionTranslator Integration

In `prediction_translator.py` → `translate()` method, after building `ClassifiedEvent`:

```python
# Inject remedy_engine in __init__:
def __init__(self, config: ModelConfig, items_resolver, remedy_engine=None):
    ...
    self.remedy_engine = remedy_engine

# In translate():
if self.remedy_engine and enriched_natal and enriched_annual:
    year_options = self.remedy_engine.get_year_shifting_options(
        birth_chart=enriched_natal,
        annual_chart=enriched_annual,
        age=event.peak_age,
    )
    remedy_applicable = any(r.safe_matches for r in year_options.values())
    remedy_hints = self.remedy_engine.generate_remedy_hints(year_options)
else:
    remedy_applicable = False
    remedy_hints = []

return LKPrediction(
    ...,
    remedy_applicable=remedy_applicable,
    remedy_hints=remedy_hints,
)
```

> **Backward compatibility**: `remedy_engine` defaults to `None`. If not provided,
> `remedy_applicable=False` and `remedy_hints=[]`. No breaking change.

### 7.2 ProbabilityEngine Integration

In `probability_engine.py` → `calculate_varshaphal_trigger()`:

```python
# Accept optional applied_remedies
def calculate_varshaphal_trigger(
    self, planet, natal, annual, age, domain, applied_remedies=None
):
    ...
    # After computing Tvp_base, apply remedy boost if applicable
    if applied_remedies:
        for rem in applied_remedies:
            if (rem.get("planet") == planet
                    and rem.get("age") == age
                    and rem.get("is_safe", False)):
                tvp_boost = self.config.get("remedy.tvp_boost_per_unit", 0.1)
                Tvp_base *= (1.0 + tvp_boost)
                break
    ...
```

> **Default**: `applied_remedies=None` → no behavioral change for existing callers.

---

## 8. Test Plan (Superpowers TDD)

### Test File Structure

```
backend/tests/lk_prediction/
├── test_remedy_engine.py          # 22 unit tests (Phase B)
├── test_remedy_integration.py     # 5 integration tests (Phase C + E)
└── test_remedy_tvp_integration.py # 4 integration tests (Phase D)
```

### Phase B Tests — test_remedy_engine.py

#### Group 1: get_safe_houses (4 tests)

```python
def test_get_safe_houses_no_enemies_returns_all_base_recs():
    """Sun in H1, no enemies in any base rec houses → all base recs safe."""

def test_get_safe_houses_enemy_in_target_returns_blocked():
    """Saturn in H5 (Sun enemy) → H5 blocked in Sun's safe houses."""

def test_get_safe_houses_masnui_enemy_in_target_returns_blocked():
    """Artificial Saturn in H5 → resolves to Saturn → blocks Sun in H5."""

def test_get_safe_houses_empty_chart_returns_all_recs():
    """Empty planets_in_houses → no blockers → all base recs safe."""
```

#### Group 2: get_year_shifting_options (3 tests)

```python
def test_get_year_shifting_options_intersection_of_birth_and_annual():
    """House safe in both birth AND annual appears in safe_matches."""

def test_get_year_shifting_options_no_overlap_returns_empty_safe_matches():
    """Birth blocks H4, annual blocks H9 → safe_matches = []."""

def test_get_year_shifting_options_conflict_map_merges_both_charts():
    """Birth conflict shows 'Birth: Blocked by ...', annual shows 'Annual: ...'."""
```

#### Group 3: rank_safe_houses (5 tests)

```python
def test_rank_safe_houses_h9_scores_higher_than_h4():
    """H9: base 10 + 30 = 40 (High); H4: base 10 + 10 = 20 (Medium)."""

def test_rank_safe_houses_unblock_rule_gives_critical():
    """Jupiter in H8, target H4 → +50 bonus → score ≥ 60 → CRITICAL."""

def test_rank_safe_houses_pair_companion_boosts_score():
    """Moon+Jupiter pair, target H2 → +40 bonus → score ≥ 40 → High."""

def test_rank_safe_houses_doubtful_planet_boosts_rank():
    """Planet has Doubtful state → +20 added to score."""

def test_rank_safe_houses_sorted_descending_by_score():
    """Multiple safe houses → returned sorted highest score first."""
```

#### Group 4: simulate_lifetime_strength (4 tests)

```python
def test_simulate_lifetime_strength_baseline_matches_chart_strengths():
    """No remedies applied → remedy == baseline for all ages."""

def test_simulate_lifetime_strength_boost_applied_correct_year():
    """Remedy applied at age 28 → boost active only at age 28."""

def test_simulate_lifetime_strength_residual_carries_forward():
    """After remedy at age 28, age 29 and beyond have residual > 0."""

def test_simulate_lifetime_strength_unsafe_remedy_half_boost():
    """Unsafe remedy (is_safe=False) → boost = SHIFTING_BOOST * 0.5."""
```

#### Group 5: analyze_life_area_potential (2 tests)

```python
def test_analyze_life_area_potential_max_exceeds_applied():
    """max_remediable >= current_remediation always (can't over-remedy)."""

def test_analyze_life_area_potential_efficiency_correct_percentage():
    """Efficiency = (applied - baseline) / (max - baseline + 0.1) * 100."""
```

#### Group 6: generate_remedy_hints (3 tests)

```python
def test_generate_remedy_hints_returns_top_3_critical_high():
    """5 CRITICAL+High options → returns exactly 3."""

def test_generate_remedy_hints_includes_planet_and_house():
    """Hint string contains planet name and house number."""

def test_generate_remedy_hints_empty_when_no_safe_matches():
    """No safe matches → returns []."""
```

#### Group 7: config integration (2 tests)

```python
def test_remedy_engine_config_shifting_boost_used():
    """Engine reads remedy.shifting_boost from config (not hardcoded 2.5)."""

def test_remedy_engine_config_residual_factor_used():
    """Engine reads remedy.residual_impact_factor from config (not hardcoded 0.05)."""
```

### Phase C Tests — test_remedy_integration.py

```python
def test_translator_populates_remedy_hints_when_safe_matches_exist():
    """PredictionTranslator with RemedyEngine → LKPrediction.remedy_hints populated."""

def test_translator_sets_remedy_applicable_false_when_no_safe_matches():
    """No safe houses → remedy_applicable=False."""

def test_translator_remedy_includes_planet_and_house():
    """remedy_hints strings reference planet and house number."""

def test_translator_remedy_hints_max_3_items():
    """Even with many options, remedy_hints has at most 3 items."""

def test_translator_without_remedy_engine_defaults_empty():
    """PredictionTranslator(remedy_engine=None) → remedy_hints=[], remedy_applicable=False."""
```

### Phase D Tests — test_remedy_tvp_integration.py

```python
def test_tvp_boost_increases_when_remedy_applied_safely():
    """Safe remedy applied → Tvp_base * (1 + tvp_boost_per_unit)."""

def test_tvp_unchanged_when_no_remedy_applied():
    """No remedies → Tvp unchanged."""

def test_tvp_boost_uses_config_tvp_boost_per_unit():
    """Engine reads remedy.tvp_boost_per_unit from config."""

def test_tvp_boost_unsafe_remedy_no_extra_boost():
    """Unsafe remedy (is_safe=False) → no Tvp boost."""
```

---

## 9. Implementation Order

```
Phase A (Config Extension):
  1. Add 13 remedy.* keys to backend/data/model_defaults.json
  2. Confirm config.get("remedy.shifting_boost") returns 2.5
  3. Run: pytest backend/tests/lk_prediction/test_config.py -v -k "remedy"

Phase B (Core Module — Test First):
  4. Create backend/tests/lk_prediction/test_remedy_engine.py (22 tests, all RED)
  5. Create backend/astroq/lk_prediction/remedy_engine.py
  6. Implement group by group, running tests after each group
  7. Confirm all 22 tests GREEN

Phase C (PredictionTranslator Integration):
  8. Modify prediction_translator.py (add remedy_engine param + call generate_remedy_hints)
  9. Create backend/tests/lk_prediction/test_remedy_integration.py (5 tests)
  10. Confirm all 5 tests GREEN

Phase D (ProbabilityEngine Integration — Optional):
  11. Modify probability_engine.py (add applied_remedies param to calculate_varshaphal_trigger)
  12. Create backend/tests/lk_prediction/test_remedy_tvp_integration.py (4 tests)
  13. Confirm all 4 tests GREEN

Phase E (End-to-End Verification):
  14. Run full test suite: pytest backend/tests/lk_prediction/ -v --tb=short
  15. Run pipeline on Sachin chart → verify remedy_hints populated
  16. Confirm 0 regressions
```

---

## 10. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Separate `RemedyEngine` class** | Clean module boundary; injectable into translator and prob engine |
| **Extended PUCCA_GHARS** | Remedy shifting uses wider set of safe houses vs single Pakka Ghar in StrengthEngine |
| **Both standard AND masnui planets checked** | Legacy code does this; a masnui enemy in target house blocks shifting |
| **Intersection of birth × annual** | Birth = lifelong potential; annual = current-year safety |
| **Goswami scores are additive** | Multiple conditions can compound; CRITICAL naturally dominates output |
| **top-3 only in generate_remedy_hints** | Avoid overwhelming LKPrediction.remedy_hints with low-priority options |
| **remedy_engine=None default** | Backward-compatible injection; translator works without remedies |
| **Tvp boost is Phase D (after Phase C stable)** | Separates functional from probabilistic integration; benchmark first |
| **Config-driven scoring thresholds** | CRITICAL/High/Medium thresholds tunable without code changes |
