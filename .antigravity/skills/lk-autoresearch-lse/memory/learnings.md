# Skill Memory: Learnings Log

> Accumulated knowledge from AutoResearch 2.0 (LSE) implementation sessions.
> The agent MUST read this at the start of each session and append new entries at the end.

## How to Use This File

**At session start**: Read this entire file to absorb prior learnings.
**At session end**: Append a new entry at the bottom using the template below.

```
## YYYY-MM-DD — Phase N: [Module Name]
- **What worked**: ...
- **What didn't work (and the fix)**: ...
- **Hypothesis types that moved the needle**: ...
- **Config knobs that had high impact**: ...
- **Convergence behaviour observed**: ...
- **Next session must know**: ...
```

---

## Key Patterns from Spec (Read Before Starting)

- **The worked example** (Sun H1, Jupiter H9, Saturn H10) has a known 2.5-year
  Mars H8 delay. The implementation should reproduce this exactly in Phase 7.
- **Hypothesis ranking**: Delay constants should be tried before grammar
  overrides. Simple hypotheses (single-planet delay) before compound ones.
- **Convergence guard**: Always cap iterations at `max_iterations=20` to prevent
  infinite loops on charts with contradictory event data.
- **Sleeping house cancellation**: H12 travel is the most common override for
  H10 sleeping charts. Always include this hypothesis early.
- **`config.set_override(key, value, figure=id)`**: This is the ONLY way to
  store personalised constants. Never mutate `rules.db` directly.

---

*(Append session notes below this line)*

## 2026-03-26 — Phase 8: Batch Benchmark (astroq_gt.db)
- **What worked**: Integrated `astroq_gt.db` tables (`lk_birth_charts` and `benchmark_ground_truth`) into a new batch processing script `run_lse_benchmark_gt.py`.
- **Normalization**: Used regex-based name normalization to link figures between tables, handling minor spelling/format variations.
- **Batching**: Implemented `--batch-size` and `--start-index` for flexible execution and resumability.
- **Convergence**: Orchestrator correctly handles solve loops for each figure in the batch.
- **Next session must know**: The script saves `ChartDNA` directly back to `astroq_gt.db` for centralized data management.

