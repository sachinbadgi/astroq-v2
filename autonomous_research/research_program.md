# AutoResearch Program: Bhav Parivartan Optimization

## Objective
Maximize the **Weighted Hit Rank (WHR)** score by adjusting House Exchange (Bhav Parivartan) weights.

## Baseline
- **Date**: 2026-04-19
- **Score**: 0.5667
- **Target Figure Sample**: First 10 public figures in `astroq_gt.db`.

## Instructions for Agent
1. Read `research_logic.py`.
2. Propose a modification to `PARIVARTAN_WEIGHTS`.
3. Run `python research_evaluator.py`.
4. If `FINAL_SCORE` increases, `git commit` the change to `research_logic.py`.
5. If score decreases, `git checkout research_logic.py`.
6. Repeat.

## Constraints
- `research.parivartan_boost` must be between 0.5 and 5.0.
- `research.exchange_diffusion_bonus` must be between 0.0 and 1.0.
