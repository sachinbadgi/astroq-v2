# Design: Karpathy AutoResearch (Bhav Parivartan)

## Goal
Implement an autonomous **propose-train-evaluate-loop** for the Lal Kitab prediction engine to optimize House Exchange (Bhav Parivartan) weights using ground truth data.

## Architecture
We use the **Clean Wrapper Pattern** to decouple the research orchestration from the core physics engine.

### 1. File Contract
- **`autonomous_research/research_logic.py`**: A dedicated configuration target for the agent. It defines the scalars and weights for Bhav Parivartan.
- **`autonomous_research/research_evaluator.py`**: An immutable script that:
    1. Loads `PARIVARTAN_WEIGHTS` from `research_logic.py`.
    2. Runs the prediction pipeline for a fixed set of 50 figures from `astroq_gt.db`.
    3. Calculates a **Weighted Hit Rank (WHR)** score.
    4. Prints the score as the final output.
- **`autonomous_research/research_program.md`**: The directive describing the current optimization goal and constraints.

### 2. Core Engine Integration
The `PhysicsEngine` (in `backend/astroq/lk_prediction/rules_engine.py`) will be modified to support a `runtime_config` override. When provided, the engine will use these weights instead of its defaults.

### 3. Metric: Weighted Hit Rank (WHR)
$$WHR = \sum_{i=1}^{N} \left( \frac{1}{\text{Rank}(Event_i)} \times \text{Confidence}_i \right)$$
- If the correct life event is Ranked #1, it gets full points.
- If it's #3, it gets 0.33 points.
- Offsets outside of $\pm 1$ year are penalized.

## Success Criteria
- The loop can run 10 iterations autonomously in "Turbo" mode.
- Each iteration must correctly identify whether the score improved or declined.
- The `research_logic.py` is updated ONLY when the score improves.
- Git tracking logs every successful (improving) change.

## Security & Safety
- `research_evaluator.py` will have a 5-minute timeout per run to prevent runaway processes.
- The agent is restricted to modifying files within the `autonomous_research/` directory (except for the initial instrumentation of the core engine).
