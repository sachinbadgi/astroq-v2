# 75-Year Lifecycle Engine Implementation Plan

> **For Antigravity:** REQUIRED SUB-SKILL: Load executing-plans to implement this plan task-by-task.

**Goal:** Implement a stateful 75-year prediction engine that tracks cumulative planetary trauma and scarring.

**Architecture:** A sequential orchestrator using a `PlanetaryStateLedger` for memory and an `IncidentResolver` for geometric trigger detection.

**Tech Stack:** Python 3.11, Pytest.

---

### Task 1: The `PlanetaryStateLedger` (State Machine)

**Files:**
- Create: `backend/astroq/lk_prediction/state_ledger.py`
- Test: `backend/tests/lk_prediction/test_state_ledger.py`

**Step 1: Write the failing test for Ledger Initialization and Trauma Scaling**
```python
def test_ledger_initialization_and_multipliers():
    from astroq.lk_prediction.state_ledger import StateLedger
    ledger = StateLedger()
    sun = ledger.get_planet_state("Sun")
    assert sun.trauma_points == 0
    assert ledger.get_leakage_multiplier("Sun") == 1.0 # Pristine
    
    sun.trauma_points = 1
    # Scarring rule: 1.0 + (0.1 * trauma)
    assert abs(ledger.get_leakage_multiplier("Sun") - 1.1) < 0.01
```

**Step 2: Run test to verify it fails**
Run: `pytest backend/tests/lk_prediction/test_state_ledger.py`

**Step 3: Implement `PlanetaryState` and `StateLedger`**
```python
from dataclasses import dataclass

@dataclass
class PlanetaryState:
    base_state: str = "Dormant"
    modifier: str = "None" # None, Startled, Supported
    trauma_points: int = 0
    remedy_count: int = 0
    remedy_active_until: int = 0
    is_manda: bool = False

class StateLedger:
    def __init__(self):
        self.planets = {p: PlanetaryState() for p in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]}
    
    def get_planet_state(self, name: str):
        return self.planets[name]
        
    def get_leakage_multiplier(self, name: str) -> float:
        p = self.planets[name]
        if p.modifier == "Startled":
            return 1.5 + (0.2 * p.trauma_points)
        return 1.0 + (0.1 * p.trauma_points)
```

**Step 4: Run test to verify it passes**

**Step 5: Commit**
`git commit -m "feat: add StateLedger with trauma math"`

---

### Task 2: The `IncidentResolver` (Geometric Patterns)

**Files:**
- Create: `backend/astroq/lk_prediction/incident_resolver.py`
- Test: `backend/tests/lk_prediction/test_incident_resolver.py`

**Step 1: Write failing test for Takkar and Sanctuary detection**

**Step 2: Implement `detect_incidents` scanning chart geometric pairs**

**Step 3: Run tests and verify**

**Step 4: Commit**

---

### Task 3: The `LifecycleEngine` Orchestrator

**Files:**
- Create: `backend/astroq/lk_prediction/lifecycle_engine.py`
- Test: `backend/tests/lk_prediction/test_lifecycle_engine.py`

**Step 1: Write test for the 75-year sequential loop**
Verify that year `N` state affects year `N+1` output.

**Step 2: Implement Orchestrator calling `Pipeline` and `Resolver`**

---

### Task 4: Sachin Graph Data Schema

**Files:**
- Modify: `backend/astroq/lk_prediction/lifecycle_engine.py`

**Step 1: Implement `generate_75yr_report` returning Friction/Momentum series.**

**Step 2: Commit**
