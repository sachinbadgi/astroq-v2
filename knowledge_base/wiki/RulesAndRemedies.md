# Domain Logic (Rules & Remedies)

This page explicitly defines the rule-execution algorithms and karmic remediation models (Planet Shifting) implemented in the engine. It contains the exact logic required for a 1:1 rewrite.

## 1. Deterministic Rules Engine (`rules_engine.py`)

The Rules Engine operates as a recursive Boolean AST parser. Instead of hardcoded `if/else` statements, it evaluates a database of canonical Lal Kitab rules (`deterministic_rules` SQLite table) using a structured JSON condition tree.

### 1.1 AST Evaluator Nodes
The mathematical AST evaluator resolves the following specific node types:
- **`AND`** / **`OR`** / **`NOT`**: Standard logical combinators.
- **`current_age`**: Strict equality check mapping directly to the annual `chart_period`.
- **`house_status`**: Resolves if a target house (1-12) matches an "occupied" or "empty" state dynamically.
- **`placement`**: Checks if a target Planet (or its Masnui equivalent) is seated in a specified array of houses dynamically.
- **`confrontation`**: Checks bidirectional "100 Percent" Aspect rules. E.g., if Planet A aspects Planet B's house, or Planet B aspects Planet A's house.

### 1.2 Scaling & Override Logic
For every successful `RuleHit`, the raw scoring magnitude is computed mathematically:
1. **Overrides**: If the orchestration researcher agent injects `weight.{rule_id}`, it overwrites the rule. $Weight \le 0.01$ mathematically deletes the rule as a "False Positive".
2. **Qualitative Multiplier Mapping**:
   If hardcoded magnitude is missing, the verbal string is mapped:
   - "minor" -> `1.0` * base
   - "moderate" -> `2.0` * base
   - "major" -> `3.0` * base
   - "extreme" / "deterministic" -> `4.0` * base
   *(Base depends on `boost_scaling = 0.04` and `penalty_scaling = 0.15`)*

3. **Annual Dignity Modifier (Yearly Charts Only)**:
   For annual charts, a mathematical multiplier is applied based on where the planet rotates from its natal house via `VARSHPHAL_YEAR_MATRIX`:
   - Planet rotates to **Pakka Ghar**: `x 1.25`
   - Planet rotates to **Exaltation**: `x 1.15`
   - Planet rotates to **Debilitation**: `x 0.75`
   - Planet rotates to Enemy's Pakka Ghar: `x 0.85`
   - Otherwise neutral: `x 1.0`
   Multiple triggering planets average their dignity modifiers.

4. **35-Year Cycle Ruler Modifier**:
   Stacks multiplicatively with the Dignity Modifier by resolving the `CYCLE_35_YEAR_RANGES` ruler for the native's current age.
   - If the Period Ruler is one of the rule's triggering planets: `x 1.20` (Ruler amplification)
   - If the Period Ruler is an enemy of a triggering planet: `x 0.85` (Ruler friction)
   - (*Note: 9 out of 9 planets perfectly align their Lal Kitab effective maturity ages exactly into their own ruling periods under this system.*)

*RuleHits are finally sorted strictly by Specificity (depth/width of passing AST) to bubble the most accurate rules directly to the LLM agent.*

---

## 2. Karmic Remedy Engine (`remedy_engine.py`)

The Remedy Engine explicitly governs "Graha Parivartan" (Planet Shifting) using Goswami's mathematical priority rules.

### 2.0 Living vs. Non-Living Transference Law (Grammar of Suffering)
A fundamental mathematical bias exists in the core predictive engine rules: negative planatary alignments afflict **Living Entities** (relatives, animals) >70% of the time, while positive alignments bestow **Non-Living Assets** perfectly balanced ~50% of the time. 
To counteract this malefic damage vector without literalizing the pessimistic outcomes to the user, the predictive platform uses a karmic Transference Law: 
If a rule mathematically hits a **Living Entity** (e.g., Wife via Venus), the remedy engine will specifically isolate and recommend sacrificing/donating a **Non-Living Entity/Item** tracked via `PLANET_HOUSE_ITEMS` of the same afflicted planet (e.g., Silk, Curd) to discharge the energy.

### 2.1 The "Safe House" Contract
A house $H$ is only considered a "safe" shifting target for Planet $P$ if:
1. It is a Pucca Ghar or Exaltation house for $P$.
2. It does not contain any of $P$'s enemies (including Artificial Masnui analogs translated back to base enemies).
3. **Crucial Rule**: It must pass these tests in **both** the Birth Chart AND the current Annual Chart.

### 2.2 Goswami Priority Scoring Algorithm
Safe houses are dynamically ranked using an additive algorithm starting from a base score of `10`:
- **House Preference**: House 9 adds `+30`, House 2 adds `+20`, House 4 adds `+10`.
- **Unblock Rule (P148)**: If planet is trapped mathematically in Annual House 8, shifting to House 2 or 4 adds `+50`.
- **Goswami Pair Rule**: If $P$ is sitting in the same house as a pair companion (e.g. Moon & Jupiter) and $H$ is a preferred pair target, add `+40`.
- **Doubtful Boost**: If the planet's state implies doubt, add `+20`.

**Rank Tiers:** `CRITICAL` ($\ge 60$), `High` ($\ge 40$), `Medium` ($\ge 20$), `Low`.

If tie-breakers are needed for the LLM Agent hints, **Kendra Priority** is legally enforced: House 1 beats 10, which beats 7, which beats 4.

### 2.3 Lifetime Projection & Aggregation
The engine mathematically projects lifetime improvements via:
$Total_{age} = BaseStrength_{age} + Boost_{current} + CumulativeResiduals$
- A `shifting_boost` (default `2.5`) is scaled by `safe_multiplier=1.0` or `0.5`.
- A fraction (`residual_impact_factor = 0.05`) of the boost rolls over permanently to the cumulative baseline.

Based on this math, the system outputs distinct numeric metrics for the LLM Agent outlining "Fixed Fate" versus "Max Remediable" efficiency percentages to give objective metrics.
