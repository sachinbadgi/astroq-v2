# Database Architecture & Schema

The Lal Kitab prediction engine utilizes a multi-layered SQLite database architecture distributed across the workspace. The primary data models are stored in `backend/data/`.

## 1. Core Engine Data (`backend/data/`)

These databases drive the deterministic and probabilistic logic of the application.

*   **`rules.db`**: The core predictive physics engine. Contains over 1,145 structured Lal Kitab AST rules.
*   **`astroq_gt.db`**: The benchmark/truth database storing ground-truth life events and birth charts for evaluating model fidelity.
*   **`charts.db`**: Evaluated chart calculation cache.
*   **`api_config.db`**: Live API-level configuration and overrides.
*   **`test_config.db`**: Used strictly by the `pytest` suite and interactive fallback mechanisms.

---

## 2. Research & Learning Artifacts (`backend/`)

While operating in autonomous mode or conducting research loops, the system generates localized databases to store learned weights and tuned parameters:

*   **`mock_<public_figure_name>.db`**: (e.g., `mock_bill_gates.db`). Stores specific agent-tuned parameter configurations (~1,100 rows per figure).
*   **`mock.db`**: Contains globally merged tuning parameters.
*   **`temp_tuner.db`**: Temporary state memory used during active hyperparameter tuning sessions.

---

## 3. Key Schemas

### `deterministic_rules` Table Schema (`rules.db`)

The primary table evaluated by the predictive pipeline:

```sql
CREATE TABLE deterministic_rules (
    id TEXT PRIMARY KEY,             -- Unique string ID (e.g., "LK_GOSW_P101_MOON_VEN_BLIND")
    domain TEXT NOT NULL,            -- Life Area category (e.g., "health", "career", "wealth")
    description TEXT NOT NULL,       -- Human-readable rule ("If Moon and Venus are in confrontation...")
    condition TEXT NOT NULL,         -- The deep JSON AST string evaluated by the engine
    verdict TEXT NOT NULL,           -- Prediction payload returned to the LLM
    scale TEXT NOT NULL,             -- String multiplier ("minor", "moderate", "major", "extreme")
    scoring_type TEXT NOT NULL,      -- "boost" (adds probability) or "penalty" (subtracts probability)
    source_page TEXT,                -- Book page reference (e.g., "Goswami p.101")
    success_weight REAL DEFAULT 1.0  -- Unused/research tracking
);
```

#### JSON AST `condition` Examples

**Description**: "If Moon and Venus are in confrontation, mother may become blind."
**JSON Payload**:
```json
{
  "type": "AND",
  "conditions": [
    {
      "type": "confrontation",
      "planet_a": "Moon",
      "planet_b": "Venus"
    }
  ]
}
```

### `model_config_overrides` Table Schema (Shared)

This schema exists uniformly across several databases (`mock_*.db`, `api_config.db`, `temp_tuner.db`) to enable hot-patching of weights and dynamic configurations:

```sql
CREATE TABLE model_config_overrides (
    key    TEXT NOT NULL,
    figure TEXT NOT NULL DEFAULT '__global__',
    value  TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'manual',
    PRIMARY KEY (key, figure)
);
```

> [!WARNING]  
> Because `model_config_overrides` exists in multiple databases, ensure scripts securely lock file paths (e.g., explicitly querying `backend/mock_amitabh.db` vs `backend/data/api_config.db`) to prevent tuning weights bleeding into default config spaces.

---

## 4. Architecture Pipeline Integration

When the predictive pipeline boots:
1. `rules_engine.py` calls a `SELECT * FROM deterministic_rules` from `backend/data/rules.db` and loads rows into RAM.
2. It validates the configuration state from `api_config.db` to load any active agent tunings.
3. It loops through active rules natively evaluating the `JSON AST condition` payloads.
4. Active hits instantiate a `RuleHit` object, scoring against the active weights.
