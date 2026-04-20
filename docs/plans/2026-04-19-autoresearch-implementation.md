# AutoResearch (Bhav Parivartan) Implementation Plan

> **For Antigravity:** REQUIRED SUB-SKILL: Load executing-plans to implement this plan task-by-task.

**Goal:** Implement an autonomous loop that optimizes Lal Kitab House Exchange (Bhav Parivartan) weights using ground truth data.

**Architecture:** We use a Clean Wrapper Pattern. A new `autonomous_research/` directory will house the loop orchestration, while the core `PhysicsEngine` is instrumented to accept runtime weight overrides.

**Tech Stack:** Python, NumPy, SQLite, Pytest

---

### Phase 1: Instrumentation (Core Engine)

#### Task 1: Add Runtime Overrides to ModelConfig
**Files:**
- Modify: `backend/astroq/lk_prediction/config.py`

**Step 1: Update `ModelConfig` to support ad-hoc overrides**
Enable the config to hold volatile research weights that don't persist to disk.

#### Task 2: Implement Bhav Parivartan Detection in PhysicsEngine
**Files:**
- Modify: `backend/astroq/lk_prediction/physics_engine.py`

**Step 1: Add `_tag_parivartan` pass**
Detect if Planet A is in House(B) and B is in House(A), using `PLANET_PAKKA_GHAR`.
**Step 2: Apply `parivartan_boost` to RuleHit magnitudes**
If a hit involves exchanged planets, multiply its magnitude by `weights.parivartan_boost`.

---

### Phase 2: Scaffolding (Research Loop)

#### Task 3: Create Research Directory and Logic Target
**Files:**
- Create: `autonomous_research/research_logic.py`
- Create: `autonomous_research/research_program.md`

**Step 1: Write `research_logic.py` with initial weights**
```python
# target_file: logic.py
PARIVARTAN_WEIGHTS = {
    "parivartan_boost": 1.25,
    "exchange_diffusion_bonus": 0.15,
    "kendra_bonus": 1.10
}
```

#### Task 4: Create Immutable Evaluator
**Files:**
- Create: `autonomous_research/research_evaluator.py`

**Step 1: Implement Batch Runner**
Load 50 figures from `backend/data/astroq_gt.db`.
Run `LKPredictionPipeline` with `research_logic.py` weights.
**Step 2: Implement WHR (Weighted Hit Rank) Metric**
Calculate score. Print `FINAL_SCORE: <float>` to stdout.

---

### Phase 3: Validation & Handoff

#### Task 5: Baseline Run
**Step 1: Run evaluator manually**
`python autonomous_research/research_evaluator.py`
**Step 2: Record baseline score in `research_program.md`**

#### Task 6: Enable "Turbo" Protocol
**Files:**
- Create: `.agents/rules/research_protocol.md`

**Step 1: Define the Loop Rule**
State that the agent is authorized to run experiments in a loop using `git commit` for successes and `git revert` for failures.

---

### Execution Choice
Two execution options:
1. **Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration. **REQUIRED:** Switch Antigravity to **Fast Mode**.
2. **Parallel Session (separate)** - Open new session with executing-plans.

**Which approach?**
