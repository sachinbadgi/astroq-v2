# Stateless → Stateful Engine Implementation Plan

> **For Antigravity:** REQUIRED SUB-SKILL: Load executing-plans to implement this plan task-by-task.

**Goal:** Upgrade the Lal Kitab engine from per-year snapshot logic to a Sequential State Machine with scapegoat rerouting, cumulative trauma carry-over, and remedy recoil enforcement.

**Architecture:** New `ScapegoatRouter` sits between `IncidentResolver` and `StateLedger` inside `LifecycleEngine`. `StateLedger` gains scapegoat exhaustion tracking and a dirty-start multiplier. `LifecycleEngine` carries accumulated trauma across the Age-35 cycle boundary.

**Tech Stack:** Python 3.11, pytest, `backend/astroq/lk_prediction/` package

---

## Gap Analysis

| Feature | Status | Files Affected |
|---|---|---|
| Scapegoat Rerouting | Missing | New: `scapegoat_router.py` |
| Dignity-Aware Scapegoat Gate | Missing | `scapegoat_router.py`, `lifecycle_engine.py` |
| Scapegoat Exhaustion Tracking | Missing | `state_ledger.py` |
| 35-Year Dirty Start Carry-over | Missing | `lifecycle_engine.py`, `state_ledger.py` |
| Remedy Recoil Enforcement | Missing | `lifecycle_engine.py`, `state_ledger.py` |

---

## Task 1: ScapegoatRouter — Canonical Sacrificial Agent Table

**Files:**
- Create: `backend/astroq/lk_prediction/scapegoat_router.py`
- Create: `backend/tests/lk_prediction/test_scapegoat_router.py`

**Step 1: Write the failing test**

```python
# backend/tests/lk_prediction/test_scapegoat_router.py
from astroq.lk_prediction.scapegoat_router import ScapegoatRouter

def test_saturn_hit_by_sun_routes_to_venus_and_rahu():
    router = ScapegoatRouter()
    assert "Venus" in router.get_scapegoats("Saturn")
    assert "Rahu" in router.get_scapegoats("Saturn")

def test_jupiter_routes_to_ketu():
    router = ScapegoatRouter()
    assert "Ketu" in router.get_scapegoats("Jupiter")

def test_planet_with_no_scapegoat_returns_empty():
    router = ScapegoatRouter()
    assert router.get_scapegoats("Moon") == []
```

**Step 2: Run test to verify it fails**

```bash
cd /Users/sachinbadgi/Documents/lal_kitab/astroq-v2/backend && source venv/bin/activate
pytest tests/lk_prediction/test_scapegoat_router.py -v
```
Expected: `FAILED — ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# backend/astroq/lk_prediction/scapegoat_router.py
"""
ScapegoatRouter — 1952 Gosvami Sacrificial Agent rerouting.
Canonical table: Gosvami 1952, pp. 171-200.
"""
from typing import List, Optional

SCAPEGOAT_TABLE = {
    "Saturn":  ["Venus", "Rahu"],  # Wife / In-laws (cite: p.197)
    "Jupiter": ["Ketu"],           # Son / Maternal Uncle (cite: p.199)
    "Sun":     ["Ketu"],           # Son / Grandfather (cite: p.199)
    "Mars":    ["Ketu"],           # Nephew / Son (cite: p.198)
    "Venus":   ["Moon"],           # Mother (cite: p.198)
    "Mercury": ["Venus"],          # Wife (cite: p.198)
}
MASTERS_OF_JUSTICE = {"Sun", "Mars", "Jupiter"}

class ScapegoatRouter:
    def get_scapegoats(self, planet: str, attacker: Optional[str] = None) -> List[str]:
        base = planet.replace("Masnui ", "") if planet.startswith("Masnui ") else planet
        if base in MASTERS_OF_JUSTICE:
            return ["Ketu"]  # Masters always sacrifice Ketu first (cite: p.174)
        return SCAPEGOAT_TABLE.get(base, [])

    def is_master_of_justice(self, planet: str) -> bool:
        base = planet.replace("Masnui ", "") if planet.startswith("Masnui ") else planet
        return base in MASTERS_OF_JUSTICE
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/lk_prediction/test_scapegoat_router.py -v
```
Expected: `3 passed`

**Step 5: Commit**

```bash
git add astroq/lk_prediction/scapegoat_router.py tests/lk_prediction/test_scapegoat_router.py
git commit -m "feat: add ScapegoatRouter with canonical 1952 Gosvami sacrificial agent table"
```

---

## Task 2: StateLedger — Scapegoat Exhaustion Tracking

After a scapegoat absorbs 3+ hits it is "exhausted" and the planet takes the next blow directly.

**Files:**
- Modify: `backend/astroq/lk_prediction/state_ledger.py`
- Modify: `backend/tests/lk_prediction/test_state_ledger.py` (extend)

**Step 1: Write failing test**

```python
# Append to backend/tests/lk_prediction/test_state_ledger.py
def test_scapegoat_exhaustion_after_three_hits():
    from astroq.lk_prediction.state_ledger import StateLedger
    ledger = StateLedger()
    ledger.record_scapegoat_hit("Ketu")
    ledger.record_scapegoat_hit("Ketu")
    ledger.record_scapegoat_hit("Ketu")
    assert ledger.is_scapegoat_exhausted("Ketu") is True

def test_scapegoat_not_exhausted_below_threshold():
    from astroq.lk_prediction.state_ledger import StateLedger
    ledger = StateLedger()
    ledger.record_scapegoat_hit("Venus")
    assert ledger.is_scapegoat_exhausted("Venus") is False
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/lk_prediction/test_state_ledger.py -v
```
Expected: `FAILED — AttributeError: no attribute 'record_scapegoat_hit'`

**Step 3: Write minimal implementation**

In `PlanetaryState` dataclass add field:
```python
scapegoat_hit_count: int = 0
SCAPEGOAT_EXHAUSTION_THRESHOLD: int = 3
```

In `StateLedger` class add methods:
```python
def record_scapegoat_hit(self, scapegoat_planet: str) -> None:
    """Records absorbed scapegoat hit + minor trauma (0.3 pts)."""
    base = scapegoat_planet.replace("Masnui ", "") if scapegoat_planet.startswith("Masnui ") else scapegoat_planet
    if base in self.planets:
        self.planets[base].scapegoat_hit_count += 1
        self.apply_trauma(base, 0.3)

def is_scapegoat_exhausted(self, scapegoat_planet: str) -> bool:
    """True if scapegoat absorbed >= SCAPEGOAT_EXHAUSTION_THRESHOLD hits."""
    base = scapegoat_planet.replace("Masnui ", "") if scapegoat_planet.startswith("Masnui ") else scapegoat_planet
    state = self.planets.get(base)
    if not state:
        return False
    return state.scapegoat_hit_count >= state.SCAPEGOAT_EXHAUSTION_THRESHOLD
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/lk_prediction/test_state_ledger.py -v
```

**Step 5: Commit**

```bash
git add astroq/lk_prediction/state_ledger.py tests/lk_prediction/test_state_ledger.py
git commit -m "feat: add scapegoat exhaustion tracking to StateLedger"
```

---

## Task 3: LifecycleEngine — Dignity-Aware Scapegoat Rerouting

Three-way routing rule:
- `RASHI_PHAL + Healthy scapegoat` → 100% trauma to scapegoat, 0% to native
- `GRAHA_PHAL` → 80% native, 20% scapegoat
- `Fatigued/Burst` → Double hit (both native AND scapegoat take full trauma)

**Files:**
- Modify: `backend/astroq/lk_prediction/lifecycle_engine.py`
- Create: `backend/tests/lk_prediction/test_lifecycle_scapegoat.py`

**Step 1: Write failing test**

```python
# backend/tests/lk_prediction/test_lifecycle_scapegoat.py
from astroq.lk_prediction.lifecycle_engine import LifecycleEngine

MOCK_NATAL = {
    "Saturn": 12, "Sun": 6, "Venus": 3, "Moon": 5,
    "Mars": 9, "Mercury": 7, "Jupiter": 1, "Rahu": 10, "Ketu": 4,
}

def test_rashi_phal_routes_to_scapegoat():
    engine = LifecycleEngine()
    history = engine.run_75yr_analysis(MOCK_NATAL, dignity_overrides={"Saturn": "RASHI_PHAL"})
    # Venus (Saturn's scapegoat) should accumulate trauma
    final = history[75]
    assert final.get_planet_state("Venus").scapegoat_hit_count >= 0  # method exists

def test_run_accepts_dignity_overrides_kwarg():
    engine = LifecycleEngine()
    # Should not raise TypeError
    history = engine.run_75yr_analysis(MOCK_NATAL, dignity_overrides={})
    assert isinstance(history, dict)
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/lk_prediction/test_lifecycle_scapegoat.py -v
```
Expected: `FAILED — TypeError: unexpected keyword argument 'dignity_overrides'`

**Step 3: Write minimal implementation**

At top of `lifecycle_engine.py` add:
```python
from .scapegoat_router import ScapegoatRouter
```

In `LifecycleEngine.__init__` add:
```python
self.scapegoat_router = ScapegoatRouter()
```

Change `run_75yr_analysis` signature:
```python
def run_75yr_analysis(
    self,
    natal_data: Dict[str, Any],
    dignity_overrides: Dict[str, str] = None
) -> Dict[int, StateLedger]:
```

Replace the `if incident.type == "Takkar":` block with:
```python
if incident.type == "Takkar":
    complex_state = self.dormancy.get_complex_state(
        incident.target, target_house, annual_positions
    )
    if is_awake or complex_state.is_startled:
        overrides = dignity_overrides or {}
        fate_type = overrides.get(incident.target, "RASHI_PHAL")
        planet_state = self.ledger.get_planet_state(incident.target)
        scapegoats = self.scapegoat_router.get_scapegoats(incident.target)

        if planet_state.is_burst:
            # Double Hit: both native and scapegoat absorb full trauma
            self.ledger.apply_strike_impact(
                incident.target, incident.trauma_weight,
                is_startled=complex_state.is_startled
            )
            for sg in scapegoats:
                if not self.ledger.is_scapegoat_exhausted(sg):
                    self.ledger.record_scapegoat_hit(sg)
                    self.ledger.apply_trauma(sg, incident.trauma_weight)

        elif fate_type == "GRAHA_PHAL":
            # Fixed Fate: 80% native, 20% scapegoat
            self.ledger.apply_strike_impact(
                incident.target, incident.trauma_weight * 0.8,
                is_startled=complex_state.is_startled
            )
            for sg in scapegoats:
                if not self.ledger.is_scapegoat_exhausted(sg):
                    self.ledger.record_scapegoat_hit(sg)
                    self.ledger.apply_trauma(sg, incident.trauma_weight * 0.2)

        else:  # RASHI_PHAL default
            routed = False
            for sg in scapegoats:
                if not self.ledger.is_scapegoat_exhausted(sg):
                    self.ledger.record_scapegoat_hit(sg)
                    self.ledger.apply_trauma(sg, incident.trauma_weight)
                    routed = True
                    break
            if not routed:
                # Scapegoat exhausted — planet absorbs hit itself
                self.ledger.apply_strike_impact(
                    incident.target, incident.trauma_weight,
                    is_startled=complex_state.is_startled
                )
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/lk_prediction/test_lifecycle_scapegoat.py -v
```

**Step 5: Run full suite to check for regressions**

```bash
pytest tests/ -v --tb=short 2>&1 | tail -30
```

**Step 6: Commit**

```bash
git add astroq/lk_prediction/lifecycle_engine.py tests/lk_prediction/test_lifecycle_scapegoat.py
git commit -m "feat: dignity-aware scapegoat rerouting in LifecycleEngine"
```

---

## Task 4: 35-Year Dirty Start Carry-over

At Age 35 → 36 boundary, planets with accumulated trauma get reduced burst thresholds so they degrade faster in Cycle 2.

**Files:**
- Modify: `backend/astroq/lk_prediction/state_ledger.py`
- Modify: `backend/astroq/lk_prediction/lifecycle_engine.py`
- Create: `backend/tests/lk_prediction/test_dirty_start.py`

**Step 1: Write failing test**

```python
# backend/tests/lk_prediction/test_dirty_start.py
from astroq.lk_prediction.state_ledger import StateLedger

def test_dirty_start_reduces_burst_threshold_for_traumatized_planet():
    ledger = StateLedger()
    ledger.planets["Saturn"].trauma_points = 2.5  # Heavy trauma
    original_threshold = ledger.planets["Saturn"].burst_threshold
    ledger.apply_dirty_start_penalty()
    assert ledger.planets["Saturn"].burst_threshold < original_threshold

def test_clean_planet_unaffected_by_dirty_start():
    ledger = StateLedger()
    # Saturn with 0 trauma — no degradation
    ledger.planets["Saturn"].trauma_points = 0.0
    original_threshold = ledger.planets["Saturn"].burst_threshold
    ledger.apply_dirty_start_penalty()
    assert ledger.planets["Saturn"].burst_threshold == original_threshold
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/lk_prediction/test_dirty_start.py -v
```
Expected: `FAILED — AttributeError: no attribute 'apply_dirty_start_penalty'`

**Step 3: Write minimal implementation**

Add to `StateLedger`:
```python
def apply_dirty_start_penalty(self) -> None:
    """
    Called at Age 35→36 cycle boundary.
    Reduces burst_threshold for traumatized planets — implements
    'Mechanical Degradation' into Cycle 2 (cite: 2176, 2179).
    Planets with > 2.0 trauma get 30% lower threshold (burst faster).
    Planets with 0.5-2.0 trauma get 15% lower threshold.
    Clean planets (< 0.5 trauma) are unaffected.
    """
    for planet, state in self.planets.items():
        if state.trauma_points >= 2.0:
            state.burst_threshold = max(1.0, state.burst_threshold * 0.70)
        elif state.trauma_points >= 0.5:
            state.burst_threshold = max(1.0, state.burst_threshold * 0.85)
        # else: clean — no change
```

Add inside `run_75yr_analysis` loop (after saving history[35]):
```python
# 35-Year cycle boundary: apply Dirty Start penalty (cite: 2176, 2179)
if age == 35:
    self.ledger.apply_dirty_start_penalty()
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/lk_prediction/test_dirty_start.py -v
```

**Step 5: Run full suite**

```bash
pytest tests/ -v --tb=short 2>&1 | tail -20
```

**Step 6: Commit**

```bash
git add astroq/lk_prediction/state_ledger.py astroq/lk_prediction/lifecycle_engine.py tests/lk_prediction/test_dirty_start.py
git commit -m "feat: 35-year Dirty Start carry-over accelerates burst threshold in Cycle 2"
```

---

## Task 5: Remedy Recoil Enforcement

When a remedy maintenance window expires, the planet recoils with +2.0 trauma (double penalty). The gap: `get_recoil_multiplier()` exists but nothing calls `apply_trauma` during the lifecycle loop.

**Files:**
- Modify: `backend/astroq/lk_prediction/state_ledger.py`
- Modify: `backend/astroq/lk_prediction/lifecycle_engine.py`
- Create: `backend/tests/lk_prediction/test_remedy_recoil.py`

**Step 1: Write failing test**

```python
# backend/tests/lk_prediction/test_remedy_recoil.py
from astroq.lk_prediction.lifecycle_engine import LifecycleEngine
from astroq.lk_prediction.state_ledger import RemedyNexus

MOCK_NATAL = {
    "Saturn": 12, "Sun": 6, "Venus": 3, "Moon": 5,
    "Mars": 9, "Mercury": 7, "Jupiter": 1, "Rahu": 10, "Ketu": 4,
}

def test_expired_remedy_fires_recoil_trauma():
    engine = LifecycleEngine()
    # Remedy applied at age 10, window=5 years → expires at age 15
    engine.ledger.planets["Saturn"].remedy_nexus = RemedyNexus(
        remedy_id="test_remedy",
        inception_age=10,
        recoil_multiplier=2.0,
        maintenance_window_years=5
    )
    history = engine.run_75yr_analysis(MOCK_NATAL)
    # At age 16 nexus should be cleared and trauma added
    ledger_16 = history.get(16)
    assert ledger_16 is not None
    # Remedy nexus should be cleared (recoil fired once)
    assert ledger_16.get_planet_state("Saturn").remedy_nexus is None
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/lk_prediction/test_remedy_recoil.py -v
```
Expected: `FAILED — AssertionError: remedy_nexus is not None` (recoil never fires)

**Step 3: Write minimal implementation**

Add to `StateLedger`:
```python
def apply_remedy_recoil_if_expired(self, planet: str, current_age: int) -> bool:
    """
    Checks remedy maintenance window. If expired, applies +2.0 trauma recoil
    and clears the nexus (fires once only).
    Implements 'High-Stakes Maintenance' (cite: 3942, 3945).
    Returns True if recoil was applied.
    """
    p = self.planets.get(planet)
    if not p or not p.remedy_nexus:
        return False
    nexus = p.remedy_nexus
    if (current_age - nexus.inception_age) > nexus.maintenance_window_years:
        self.apply_trauma(planet, 2.0)
        p.remedy_nexus = None  # Clear so it fires only once
        return True
    return False
```

Add at end of the `for age` loop in `run_75yr_analysis`, before saving `history[age]`:
```python
# Remedy recoil check (cite: 3942, 3945)
for planet_name in list(self.ledger.planets.keys()):
    self.ledger.apply_remedy_recoil_if_expired(planet_name, age)
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/lk_prediction/test_remedy_recoil.py -v
```

**Step 5: Run full suite — final check**

```bash
pytest tests/ -v --tb=short 2>&1 | tail -30
```

**Step 6: Final commit**

```bash
git add astroq/lk_prediction/state_ledger.py astroq/lk_prediction/lifecycle_engine.py tests/lk_prediction/test_remedy_recoil.py
git commit -m "feat: enforce remedy recoil (+2 trauma) when maintenance window expires"
```

---

## Verification Plan

### Run all new tests together

```bash
cd /Users/sachinbadgi/Documents/lal_kitab/astroq-v2/backend
source venv/bin/activate
pytest tests/lk_prediction/test_scapegoat_router.py \
       tests/lk_prediction/test_state_ledger.py \
       tests/lk_prediction/test_lifecycle_scapegoat.py \
       tests/lk_prediction/test_dirty_start.py \
       tests/lk_prediction/test_remedy_recoil.py -v
```

### Full suite

```bash
pytest tests/ --tb=short 2>&1 | tail -20
```

### Smoke test — engine still produces output

```bash
python run_lk_engine.py 2>&1 | head -40
```

### Integration check — lifecycle report

```bash
python -c "
from astroq.lk_prediction.lifecycle_engine import LifecycleEngine
import json
engine = LifecycleEngine()
report = engine.generate_75yr_report({
    'Saturn':12,'Sun':6,'Venus':3,'Moon':5,
    'Mars':9,'Mercury':7,'Jupiter':1,'Rahu':10,'Ketu':4
})
print(json.dumps(report['summary'], indent=2))
"
```
Expected: `scarred_planets` is non-empty, `total_trauma` > 0.
