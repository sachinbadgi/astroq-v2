# Quantum Chart Generator Implementation Plan

> **For Antigravity:** REQUIRED SUB-SKILL: Load executing-plans to implement this plan task-by-task.

**Goal:** Implement the quantum-based chart generator module (`backend/astroq/quantum_engine`) to generate natal and annual charts using matrices and tertiary states (-1, 0, 1) for the auto-research framework.

**Architecture:** Use pure Python lists and mathematical transformation to implement the 120-year Varshphal matrix as a unitary operator. Entanglements (Masnui Grah) will be logic gates. All constants are loaded from a JSON configuration to support optimization loops. `numpy` can be used if available, but pure Python matrices are preferred for minimum dependency overhead unless performance requires it. (We'll use `numpy` since we're simulating quantum matrices and the project uses ML pipelines, but we'll ensure fallback or standard usage). Actually, we'll use pure Python 2D arrays (lists of lists) to prevent adding heavy new dependencies unless already in `requirements.txt`.

**Tech Stack:** Python, `pytest`.

## User Review Required
Please review this implementation plan. I will execute it task-by-task using TDD once approved.

## Proposed Changes

### Task 1: Setup Configuration Interface
**Files:**
- Create: `backend/tests/quantum_engine/test_config.py`
- Create: `backend/astroq/quantum_engine/quantum_weights.json`
- Create: `backend/astroq/quantum_engine/config.py`
- Create: `backend/astroq/quantum_engine/__init__.py`
- Create: `backend/tests/quantum_engine/__init__.py`

**Step 1.1: Write the failing test**
```python
# backend/tests/quantum_engine/test_config.py
from astroq.quantum_engine.config import load_quantum_weights, QuantumConfig

def test_load_default_weights():
    config = load_quantum_weights()
    assert isinstance(config, QuantumConfig)
    assert config.exaltation_amplitude == 1
    assert config.debilitation_amplitude == -1
```

**Step 1.2: Run test to verify it fails**
Run: `pytest backend/tests/quantum_engine/test_config.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'astroq.quantum_engine.config'"

**Step 1.3: Write minimal implementation**
```json
// backend/astroq/quantum_engine/quantum_weights.json
{
  "amplitudes": {
    "exaltation": 1,
    "debilitation": -1,
    "superposed": 0
  }
}
```
```python
# backend/astroq/quantum_engine/config.py
import json
import os
from dataclasses import dataclass

@dataclass
class QuantumConfig:
    exaltation_amplitude: int
    debilitation_amplitude: int
    superposed_amplitude: int

def load_quantum_weights(filepath=None) -> QuantumConfig:
    if not filepath:
        filepath = os.path.join(os.path.dirname(__file__), 'quantum_weights.json')
    with open(filepath, 'r') as f:
        data = json.load(f)
    amps = data.get("amplitudes", {})
    return QuantumConfig(
        exaltation_amplitude=amps.get("exaltation", 1),
        debilitation_amplitude=amps.get("debilitation", -1),
        superposed_amplitude=amps.get("superposed", 0)
    )
```

**Step 1.4: Run test to verify it passes**
Run: `pytest backend/tests/quantum_engine/test_config.py -v`
Expected: PASS

**Step 1.5: Commit**
```bash
git add backend/tests/quantum_engine backend/astroq/quantum_engine
git commit -m "feat(quantum): add configuration loader for quantum weights"
```

---

### Task 2: State Vectors and Transformation Matrices
**Files:**
- Create: `backend/tests/quantum_engine/test_matrix_models.py`
- Create: `backend/astroq/quantum_engine/matrix_models.py`

**Step 2.1: Write the failing test**
```python
# backend/tests/quantum_engine/test_matrix_models.py
from astroq.quantum_engine.matrix_models import StateVector, VarshphalMatrix

def test_state_vector_initialization():
    sv = StateVector()
    assert len(sv.vector) == 9 # 9 planets
    assert all(len(house_dist) == 12 for house_dist in sv.vector.values())

def test_unitary_evolution():
    sv = StateVector()
    # Put Sun in House 1
    sv.set_planet_house("Sun", 1, 1)
    
    # Apply Age 2 transformation (from 1952 Goswami matrix mapping: House 1 -> House 4)
    matrix = VarshphalMatrix()
    new_sv = matrix.apply_transformation(sv, age=2)
    
    # Sun should now be in House 4
    assert new_sv.get_planet_house("Sun") == 4
```

**Step 2.2: Run test to verify it fails**
Run: `pytest backend/tests/quantum_engine/test_matrix_models.py -v`
Expected: FAIL (missing module/classes)

**Step 2.3: Write minimal implementation**
We will implement `StateVector` containing the tertiary distribution, and `VarshphalMatrix` which holds the mapping rules (similar to `ChartGenerator.YEAR_MATRIX` but functioning as a mathematical permutation).

**Step 2.4: Run test to verify it passes**
Run: `pytest backend/tests/quantum_engine/test_matrix_models.py -v`
Expected: PASS

**Step 2.5: Commit**
```bash
git add backend/tests/quantum_engine/test_matrix_models.py backend/astroq/quantum_engine/matrix_models.py
git commit -m "feat(quantum): add state vectors and varshphal unitary operators"
```

---

### Task 3: Entanglement Logic Gates (Masnui Grah)
**Files:**
- Create: `backend/tests/quantum_engine/test_entanglement.py`
- Create: `backend/astroq/quantum_engine/entanglement.py`

**Step 3.1: Write failing test**
We test a CNOT equivalent: Sun + Venus -> Artificial Mercury.

**Step 3.2: Run test**
Run: `pytest backend/tests/quantum_engine/test_entanglement.py -v`

**Step 3.3: Implementation**
Implement `apply_masnui_gates(state_vector: StateVector, config: QuantumConfig)` that collapses interacting state amplitudes into new entangled composite matrices.

**Step 3.4: Run test**
Run: `pytest backend/tests/quantum_engine/test_entanglement.py -v`

**Step 3.5: Commit**
```bash
git add backend/tests/quantum_engine/test_entanglement.py backend/astroq/quantum_engine/entanglement.py
git commit -m "feat(quantum): add entanglement logic gates for masnui grah"
```

---

### Task 4: Quantum Chart Generator Wrapper
**Files:**
- Create: `backend/tests/quantum_engine/test_chart_generator.py`
- Create: `backend/astroq/quantum_engine/chart_generator.py`

**Step 4.1: Write failing test**
```python
# backend/tests/quantum_engine/test_chart_generator.py
from astroq.quantum_engine.chart_generator import QuantumChartGenerator

def test_generate_120_year_matrix():
    qcg = QuantumChartGenerator()
    natal_data = {"planets_in_houses": {"Sun": {"house": 1}}} # Mocked base
    
    result = qcg.generate_quantum_timeline(natal_data, max_years=5)
    assert "chart_0" in result # Natal
    assert "chart_5" in result # Age 5
```

**Step 4.2: Run test**
Run: `pytest backend/tests/quantum_engine/test_chart_generator.py -v`

**Step 4.3: Implementation**
Wrapper that takes the base `ChartData` and converts it into a `StateVector`, calculates 120 years of `StateVector`s by calling `VarshphalMatrix`, and returning them either as raw tensors or parsed dictionaries.

**Step 4.4: Run test**
Run: `pytest backend/tests/quantum_engine/test_chart_generator.py -v`

**Step 4.5: Commit**
```bash
git add backend/tests/quantum_engine/test_chart_generator.py backend/astroq/quantum_engine/chart_generator.py
git commit -m "feat(quantum): add master quantum chart generator pipeline"
```

## Verification Plan
1. Run the entire test suite `pytest backend/tests/quantum_engine/ -v`.
2. Ensure the resulting vectors map perfectly to the 1952 Goswami progression matrix.
