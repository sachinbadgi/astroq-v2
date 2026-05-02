# Rule: Autonomous Research Protocol (Turbo Mode)

## Context
When the agent is tasked with "Optimizing Parivartan Weights" or working within the `autonomous_research/` directory, these rules apply.

## Authorization
1. The agent is authorized to modify `autonomous_research/research_logic.py`.
2. The agent is authorized to execute `autonomous_research/research_evaluator.py` repeatedly.
3. The agent is authorized to use `git commit` to save progressive improvements.

## Protocol Loop
- **Step 1: Hypothesis**: Based on previous runs, decide which parameter in `research_logic.py` to change.
- **Step 2: Edit**: Apply the change.
- **Step 3: Evaluate**: Run the evaluator.
- **Step 4: Decision**:
    - If `FINAL_SCORE` > Current Best: `git commit -m "research: WHR improvement to <score>"`
    - If `FINAL_SCORE` <= Current Best: `git restore autonomous_research/research_logic.py`

## Safety
- Never modify files outside `autonomous_research/` during a research iteration.
- Maintain a log of results in a scratch file.
