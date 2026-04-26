# Natal Fate View — Implementation Plan

> **For Antigravity:** REQUIRED SUB-SKILL: Load executing-plans to implement this plan task-by-task.

**Goal:** Given any natal chart, produce a structured "Fate View" that classifies every life domain and modern event domain as either **Graha Phal** (fixed fate — promised at birth) or **Rashi Phal** (conditional fate — depends on annual chart geometry).

**Architecture:** We add a new constant catalogue (`EVENT_DOMAIN_CATALOGUE`) to `lk_pattern_constants.py` that encodes every domain from `event-domain-list.md` as a list of deterministic evaluation rules (primary house occupied? key planet dignified? Pakka Ghar match?). A new stateless `NatalFateView` class in `lk_prediction/` reads this catalogue against the natal chart and emits a typed `DomainFateEntry` for each domain. The pipeline and a new audit script both call this class.

**Tech Stack:** Python 3.11+, existing `lk_constants.py` (PLANET_PAKKA_GHAR, PLANET_EXALTATION, PUCCA_GHARS_EXTENDED, FIXED_FATE_TYPES), existing `RulesEngine` (loads `fate_type` from `deterministic_rules`), `dataclasses`, `sqlite3`, `pytest`.

---

## Background Context

### How GP vs RP classification works today

The `deterministic_rules` SQLite table already has a `fate_type` column (`GRAHA_PHAL | RASHI_PHAL | HYBRID | CONTEXTUAL | NEUTRAL`).

When `RulesEngine.evaluate_chart(natal_chart)` is called it returns a list of `RuleHit` objects. Each `RuleHit` carries a `domain` field.  
The `final_predictive_audit.py` script already loads `fate_type` from the DB via a `fate_map` dict.

**Gap:** There is no way today to ask "for *this* natal chart, is the *career* domain a fixed promise or a conditional one?" without writing a custom loop each time. The `event-domain-list.md` adds ~50 modern domains (Crypto, EVs, Solar, LLM hosting, etc.) that are not yet in `deterministic_rules` at all — their fate classification must be derived purely from planetary dignity logic, not from DB rule rows.

### Fate Classification Logic

| Fate Type | Condition on Natal Chart |
|-----------|--------------------------|
| `GRAHA_PHAL` | Primary house is occupied AND the key planet is in its Pakka Ghar **OR** Exaltation house |
| `RASHI_PHAL` | Primary house is occupied BUT the key planet is NOT dignified (promise exists but conditional) |
| `NEITHER` | Primary house is empty AND no supporting-house planet matches — domain is structurally absent from this chart |
| `HYBRID` | Both a dignity signal AND a conditional guard exist (e.g. planet exalted but in an enemy axis) |

This is the same taxonomy as `RULE_FATE_TYPES` in `lk_constants.py`. We are adding a **chart-level view** rather than a rule-level view.

---

## Open Questions

> [!IMPORTANT]
> **Q1 — Domain granularity:** The `event-domain-list.md` has ~50 domains. Should every modern domain (e.g. "Cordyceps & Mushroom Cultivation") appear in the output, or only the **canonical 13** (career, health, marriage, etc.) plus a selectable subset of modern domains?  
> **Proposal:** Default output = 13 canonical + all modern domains grouped by category. A `filter_categories` parameter controls which groups appear.

> [!IMPORTANT]
> **Q2 — Modern domain fate sourcing:** Modern domains (Crypto, EVs, AI) have no rows in `deterministic_rules`. Their GP/RP classification must come 100% from the `EVENT_DOMAIN_CATALOGUE` constants (planetary dignity logic). Is this acceptable, or should we also add them to the DB?  
> **Proposal:** Constants-only for now. DB rows can be added in a future iteration if validation data exists.

> [!IMPORTANT]
> **Q3 — Output format:** Should `NatalFateView` return a plain Python dict (easy for scripts/API), a rich dataclass, or a pre-formatted markdown table?  
> **Proposal:** Return a list of `DomainFateEntry` dataclasses (serializable to dict/JSON). A separate `format_as_table()` helper renders the markdown/text table.

---

## Proposed Changes

### Task 1 — Add `EVENT_DOMAIN_CATALOGUE` to `lk_pattern_constants.py`

#### [MODIFY] [lk_pattern_constants.py](file:///Users/sachinbadgi/Documents/lal_kitab/astroq-v2/backend/astroq/lk_prediction/lk_pattern_constants.py)

Append a new `PATTERN 11` block at end of file. Each entry in the catalogue is a dict:

```python
{
    "domain": str,                  # e.g. "career", "cryptocurrency"
    "label": str,                   # Human-readable label
    "category": str,                # "canonical" | "career_tech" | "finance" | "home_lifestyle"
                                    # | "health_wellness" | "tech_infra" | "modern_finance"
                                    # | "sustainable" | "social_psych"
    "primary_houses": list[int],    # Houses whose occupancy signals the domain is active
    "supporting_houses": list[int], # Secondary houses (lower weight check)
    "key_planets": list[str],       # Planets whose dignity determines GP vs RP
    "gp_condition": str,            # Description of what makes this GP
    "rp_condition": str,            # Description of what makes this RP
}
```

**Complete catalogue** (all 13 canonical + all modern from event-domain-list.md):

**Canonical (13):** career/profession, wealth/assets, marriage, progeny, education/wisdom, property/land, foreign_travel, litigation/enemies, courage/siblings, health/vitality, spirituality, family, real_estate

**Category: career_tech (6):** startups/entrepreneurship, software_coding, ai_big_data, public_reputation/social_media, corporate_politics, consulting/coaching

**Category: finance (5):** cryptocurrency, stock_market_trading, gold_bonds, inheritance_hidden_wealth, ecommerce_retail

**Category: home_lifestyle (5):** solar_energy, sustainable_farming, smart_homes, automobiles_travel, spirituality_mental_wellness

**Category: health_wellness (5):** anxiety_digital_fatigue, gym_biohacking, chronic_lifestyle_diseases, professional_networking, education_online_learning

**Category: tech_infra (6):** logic_coding, local_llm_hosting, cloud_computing, hardware_servers, cybersecurity, app_launch_branding

**Category: modern_finance (6):** sovereign_gold_bonds, mutual_funds_sip, digital_tokens, venture_capital, premature_asset_redemption, corporate_audits

**Category: sustainable (5):** rooftop_solar_agrivoltaics, hydroponics_farming, cordyceps_mushroom, electric_vehicles, government_subsidies

**Category: social_psych (5):** social_media_influencing, anxiety_info_overload, professional_networking_linkedin, remote_work, legal_agreements_smart_contracts

---

### Task 2 — Build `NatalFateView` Evaluator

#### [NEW] [natal_fate_view.py](file:///Users/sachinbadgi/Documents/lal_kitab/astroq-v2/backend/astroq/lk_prediction/natal_fate_view.py)

New file. Zero external dependencies beyond `lk_constants.py` and `lk_pattern_constants.py`.

```python
"""
NatalFateView
=============
Reads a natal chart and classifies every life domain / modern event
as GRAHA_PHAL (fixed fate), RASHI_PHAL (conditional), HYBRID, or NEITHER.

Usage:
    view = NatalFateView()
    entries = view.evaluate(natal_chart)
    print(view.format_as_table(entries))
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .lk_constants import PLANET_PAKKA_GHAR, PLANET_EXALTATION, PLANET_DEBILITATION, NATURAL_RELATIONSHIPS
from .lk_pattern_constants import EVENT_DOMAIN_CATALOGUE


@dataclass
class DomainFateEntry:
    domain: str
    label: str
    category: str
    fate_type: str              # "GRAHA_PHAL" | "RASHI_PHAL" | "HYBRID" | "NEITHER"
    evidence: list[str]         # Why this fate was assigned
    key_planets: list[str]      # Which planets are involved
    active_houses: list[int]    # Which houses are occupied for this domain
    dignity_details: dict       # {planet: "Pakka Ghar H7" | "Exalted H12" | "Neutral H3"}


class NatalFateView:
    def evaluate(
        self,
        natal_chart: dict,
        categories: Optional[list[str]] = None,
        include_neither: bool = True,
        db_fate_map: Optional[Dict[str, str]] = None,   # rule_id → fate_type from DB
        db_rule_hits: Optional[list] = None,            # RuleHit list from RulesEngine
    ) -> List[DomainFateEntry]: ...

    def format_as_table(self, entries: List[DomainFateEntry]) -> str: ...
```

**Evaluation algorithm per entry:**

1. Extract `positions = {planet: house}` from `natal_chart["planets_in_houses"]`.
2. Check `primary_houses`: any planet present → domain is structurally active.
3. For each `key_planet` in catalogue entry:
   - If planet is in ANY primary or supporting house:
     - Pakka Ghar match → `gp_signals.append(f"{planet} in Pakka Ghar H{h}")`
     - Exaltation match → `gp_signals.append(f"{planet} Exalted H{h}")`
     - Debilitation match → `rp_penalties.append(f"{planet} Debilitated H{h}")`
     - None of the above → `neutral.append(f"{planet} Neutral H{h}")`
4. Classify:
   - `gp_signals AND NOT rp_penalties` → `GRAHA_PHAL`
   - `gp_signals AND rp_penalties` → `HYBRID`
   - Primary house occupied AND zero gp_signals → `RASHI_PHAL`
   - All primary + supporting houses empty → `NEITHER`
5. **DB override (optional):** if `db_rule_hits` supplied, scan hits for the same domain:
   - Any hit with `fate_type == "GRAHA_PHAL"` → promotes to `GRAHA_PHAL`
   - Only `RASHI_PHAL` hits → confirms/demotes to `RASHI_PHAL`

---

### Task 3 — Unit Tests

#### [NEW] [test_natal_fate_view.py](file:///Users/sachinbadgi/Documents/lal_kitab/astroq-v2/backend/tests/test_natal_fate_view.py)

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from astroq.lk_prediction.natal_fate_view import NatalFateView, DomainFateEntry

def _chart(planets: dict) -> dict:
    """Build minimal chart dict from {planet: house} map."""
    return {"planets_in_houses": {p: {"house": h} for p, h in planets.items()}}

def get_entry(entries, domain):
    return next((e for e in entries if e.domain == domain), None)

class TestNatalFateView:
    def setup_method(self):
        self.view = NatalFateView()

    def test_career_graha_phal_saturn_pakka_ghar(self):
        """Saturn in H10 (its Pakka Ghar) → career = GRAHA_PHAL."""
        chart = _chart({"Saturn": 10, "Sun": 1})
        entries = self.view.evaluate(chart, categories=["canonical"])
        entry = get_entry(entries, "career")
        assert entry is not None
        assert entry.fate_type == "GRAHA_PHAL"

    def test_marriage_rashi_phal_venus_not_dignified(self):
        """Venus in H6 (debilitation) → marriage = RASHI_PHAL."""
        chart = _chart({"Venus": 6, "Mercury": 7})
        entries = self.view.evaluate(chart, categories=["canonical"])
        entry = get_entry(entries, "marriage")
        assert entry is not None
        assert entry.fate_type in ("RASHI_PHAL", "HYBRID")

    def test_marriage_neither_when_h7_empty(self):
        """H7 empty, Venus in H3 (no dignity) → marriage = RASHI_PHAL (not NEITHER because Venus exists)."""
        chart = _chart({"Venus": 3, "Saturn": 10})
        entries = self.view.evaluate(chart)
        entry = get_entry(entries, "marriage")
        assert entry is not None
        # Venus is in chart but not dignified and H7 empty → RASHI_PHAL
        assert entry.fate_type == "RASHI_PHAL"

    def test_cryptocurrency_graha_phal_rahu_pakka_ghar(self):
        """Rahu in H12 (Pakka Ghar) → cryptocurrency = GRAHA_PHAL."""
        chart = _chart({"Rahu": 12})
        entries = self.view.evaluate(chart, categories=["finance", "modern_finance"])
        entry = get_entry(entries, "cryptocurrency")
        assert entry is not None
        assert entry.fate_type == "GRAHA_PHAL"

    def test_filter_categories(self):
        """Only canonical entries returned when categories=["canonical"]."""
        chart = _chart({"Saturn": 10})
        entries = self.view.evaluate(chart, categories=["canonical"])
        assert all(e.category == "canonical" for e in entries)

    def test_include_neither_false(self):
        """NEITHER entries excluded when include_neither=False."""
        chart = _chart({"Saturn": 10})  # Most houses empty
        entries = self.view.evaluate(chart, include_neither=False)
        assert all(e.fate_type != "NEITHER" for e in entries)

    def test_format_as_table_returns_string(self):
        chart = _chart({"Saturn": 10, "Jupiter": 2, "Venus": 7})
        entries = self.view.evaluate(chart, categories=["canonical"])
        table = self.view.format_as_table(entries)
        assert isinstance(table, str)
        assert "GRAHA_PHAL" in table or "RASHI_PHAL" in table
```

Run: `pytest backend/tests/test_natal_fate_view.py -v`  
Expected: All 7 tests pass.

---

### Task 4 — CLI Audit Script

#### [NEW] [natal_fate_audit.py](file:///Users/sachinbadgi/Documents/lal_kitab/astroq-v2/backend/scripts/natal_fate_audit.py)

```python
"""
natal_fate_audit.py
===================
Prints a Natal Fate View table for any public figure or custom birth data.

Usage:
    python backend/scripts/natal_fate_audit.py --figure "Walter Matthau"
    python backend/scripts/natal_fate_audit.py --dob "1920-10-01" --tob "11:00" --place "New York, US"
    python backend/scripts/natal_fate_audit.py --figure "Steve Jobs" --categories canonical finance
"""
```

Steps:
1. Parse CLI args (`argparse`): `--figure`, `--dob`, `--tob`, `--place`, `--categories`, `--include-neither/--no-neither`.
2. If `--figure` given: look up in `backend/data/public_figures_ground_truth.json`, extract DOB/TOB/place.
3. Call `ChartGenerator.build_full_chart_payload(...)` to generate natal chart.
4. Instantiate `NatalFateView`. Call `.evaluate(natal_chart, categories=...)`.
5. Print `format_as_table(entries)`.

Sample output:
```
=== NATAL FATE VIEW — Walter Matthau ===

CANONICAL DOMAINS
────────────────────────────────────────────────────────────────────
Domain                 Fate Type    Key Planets         Evidence
────────────────────────────────────────────────────────────────────
Career & Profession    GRAHA_PHAL   Saturn (H10 PG)     Saturn in Pakka Ghar H10
Marriage               RASHI_PHAL   Venus (H3)          Venus present, not dignified
...

MODERN — Finance & Assets
────────────────────────────────────────────────────────────────────
Cryptocurrency         RASHI_PHAL   Rahu (H6)           Rahu not in Pakka Ghar (H12)
Stock Market           GRAHA_PHAL   Mercury (H7 PG)     Mercury in Pakka Ghar H7
...
```

---

## Verification Plan

### Automated Tests

```bash
cd /Users/sachinbadgi/Documents/lal_kitab/astroq-v2
python -m pytest backend/tests/test_natal_fate_view.py -v
```
Expected: 7 tests, all PASS.

### Regression Check

```bash
python -m pytest backend/tests/ -v
```
Expected: All pre-existing tests still pass. `test_varshphal_timing.py` unaffected.

### Manual Spot-Check

```bash
python backend/scripts/natal_fate_audit.py --figure "Steve Jobs"
python backend/scripts/natal_fate_audit.py --figure "Walter Matthau"
```
Expected: Table printed, no import errors, career + finance domains classified.

---

## File Change Summary

| Action | File | Notes |
|--------|------|-------|
| MODIFY | `backend/astroq/lk_prediction/lk_pattern_constants.py` | Append `EVENT_DOMAIN_CATALOGUE` (Pattern 11, ~60 entries) |
| NEW    | `backend/astroq/lk_prediction/natal_fate_view.py` | `NatalFateView` + `DomainFateEntry` |
| NEW    | `backend/tests/test_natal_fate_view.py` | 7 unit tests |
| NEW    | `backend/scripts/natal_fate_audit.py` | CLI audit script |
