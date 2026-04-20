# AutoResearch Progress Log

## Summary
Implementing and running the Karpathy-style "propose-train-evaluate" loop for the Lal Kitab prediction engine.

## Milestones

### 2026-04-19: Baseline & Tooling
- Implemented `research_logic.py`, `research_evaluator.py`, and `research_program.md`.
- Instrumented `PhysicsEngine` and `ModelConfig` for volatile weight overrides.
- Established baseline WHR on 10 figures: **0.5667**.

### 2026-04-19: Dataset Expansion & Iteration 5
- Expanded ground truth dataset from 10 to 25 figures including global leaders (Obama, Trump, Queen Elizabeth II) and Indian icons (Gandhi, Nehru, Lata Mangeshkar).
- Hardcoded coordinates for all 25 figures to bypass geocoding rate limits.
- **New 25-Figure Baseline**: 0.4883.
- **Iteration 5 (Result: SUCCESS)**:
    - Hypothesis: Sharper probability sigmoid (`base_k` = 5.5) + Slightly higher natal importance (`ea_weighting` = 0.12).
    - Result: **0.5300** (+4.17% improvement).
    - Status: Weights kept as the new local best.

## Current Best Weights
```python
RESEARCH_PARAMS = {
    "research.parivartan_boost": 1.25,        
    "research.exchange_diffusion_bonus": 0.15,
    "probability.base_k": 5.5,            
    "probability.ea_weighting": 0.12,     
    "probability.tvp_boost_factor": 1.2
}
```
