# Agent Orchestrator Workflows (`lse_orchestrator.py`)

The Lal Kitab Software Engineer (LSE) module utilizes an "**AutoResearch 2.0**" back-testing loop to personally tailor predictive accuracy to individual public figures. 

## The Iterative Tuning Loop

When solving a chart, the `LSEOrchestrator` attempts a feedback-driven optimization loop up to a configurable *max_iterations* limit.

1. **Pipeline Generation**: 
   The agent runs the pure mathematical pipeline across all annual charts simultaneously. To save processing time, pipeline predictions are cached unless a *Grammar Override* has been triggered by the Researcher.
2. **Surgical Alignment**:
   Before validating, the Orchestrator applies any cached numerical overrides to the predictions mathematically:
   - `delay.*`: Linearly shifts the `peak_age` by the float value given.
   - `align.*`: Snaps the delivery `peak_age` straight to the exact known milestone/canonical age.
3. **Validation & Hit-Rate**:
   The `ValidatorAgent` checks these modified predictions against the actual Ground-Truth `LifeEventLog` data for the public figure. It computes a mathematically rigorous `hit_rate` objective function.
4. **DNA Extraction**:
   If the hit-rate improves over the previous iteration, it updates the figure's `ChartDNA` (which holds optimal grammars, delay offsets, and milestone alignments).
5. **Convergence**:
   If the hit-rate meets or exceeds `95%` (`0.95`), the orchestrator triggers early convergence break.
6. **Hypothesis Generation**:
   If not converged, the `ResearcherAgent` scans the generated `Gap Report` (false positives, unpredicted events) and formulates new hypotheses (new `align.X`, `delay.X`, or `grammar.X` parameters). These are ranked, and the top untested hypothesis is fed into the next iteration.

## Outputs
At conclusion, all override data is wiped from the global config and written exclusively to the optimal `ChartDNA`. 
The orchestrator packages these finalized, tailor-fitted predictions into `LSEPrediction` contracts.
