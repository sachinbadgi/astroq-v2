---
name: lk-benchmark-tuning
description: Phase 9-10 of the LK Prediction Model v2. Benchmarks the prediction engine against 84 real public figure charts with known life events. Measures Hit Rate, Offset, Natal Accuracy, and False Positive Rate. Auto-tunes ModelConfig overrides via grid search. Uses increment-only testing (one figure at a time) to keep test runs fast.
---

# Lal Kitab Prediction Model — Benchmark & Tuning Skill

## Goal

Run Phases 9–10 of the prediction engine build:
- **Phase 9: Benchmark** — measure 4 metrics against ground truth across 84 public figures
- **Phase 10: Tune** — iteratively adjust `ModelConfig` overrides until metric targets are hit

## Metric Targets

| Metric | Target | Formula |
|--------|--------|---------|
| **Hit Rate** | > 80% | Events where `abs(predicted_peak_age - actual_age) ≤ 2` / total events |
| **Offset** | < 2.0yr | Mean absolute error: `mean(abs(predicted_age - actual_age))` across all hits+misses |
| **Natal Accuracy** | > 85% | Correct detection of event domain at natal chart level |
| **False Positive Rate** | < 15% | Predicted peaks with no matching ground truth event within ±3 years / total predicted peaks |

## Reference Resources

```
REFERENCE_CODEBASE   = D:\astroq-mar26
PUBLIC_FIGURES_DATA  = D:\astroq-mar26\backend\tests\data\public_figures\
GROUND_TRUTH_DB      = D:\astroq-mar26\backend\astroq.db  (table: benchmark_ground_truth)
FIGURE_LIST          = D:\astroq-mar26\backend\db_figures.txt  (84 figures)
OLD_BENCHMARK_RUNNER = D:\astroq-mar26\backend\astroq\benchmark_runner.py
OLD_DATASET          = D:\astroq-mar26\backend\astroq\benchmark_dataset.py
```

> **ALWAYS READ THESE FILES FIRST** when starting autoresearch on a data structure:
> `view_file D:\astroq-mar26\backend\astroq\benchmark_dataset.py`
> `view_file D:\astroq-mar26\backend\tests\advanced\run_accuracy_benchmark.py`

## ⚡ Memory System (MANDATORY)

### On Session Start (do this FIRST)

```bash
view_file .antigravity/skills/lk-benchmark-tuning/memory/progress.md
view_file .antigravity/skills/lk-benchmark-tuning/memory/learnings.md
view_file .antigravity/skills/lk-benchmark-tuning/memory/decisions.md
```

### On Session End (do this LAST)

Update all three memory files with what you found, what you changed, and what to do next.

## Autoresearch — Phase 9

Before running benchmarks, study these reference files to understand chart format and ground truth:

| Task | Study File |
|------|-----------|
| Chart JSON format | `D:\astroq-mar26\backend\tests\data\public_figures\sachin_tendulkar_enriched_chart.json` |
| Ground truth schema | Query: `sqlite3 D:\astroq-mar26\backend\astroq.db "SELECT * FROM benchmark_ground_truth LIMIT 10"` |
| AccuracyChecker logic | `D:\astroq-mar26\backend\astroq\lal_kitab\accuracy_checker.py` |
| Old run script | `D:\astroq-mar26\backend\tests\advanced\run_accuracy_benchmark.py` |

## Build Sequence

### Phase 9a: Port Public Figures Data

```bash
# Copy enriched chart JSONs for the 10 core figures
# from D:\astroq-mar26\backend\tests\data\public_figures\
# to  D:\astroq-v2\backend\tests\data\public_figures\
# Start with the 10 in benchmark_dataset.py (CELEBRITY_DATA)
```

### Phase 9b: Implement BenchmarkRunner

```bash
# File: backend/astroq/lk_prediction/benchmark_runner.py
# - Loads public figure chart JSON
# - Runs run_prediction_pipeline() for each domain
# - Computes 4 metrics
# - Saves results to JSON

// turbo
pytest backend/tests/lk_prediction/test_benchmark.py -v -k "single_figure" --tb=short
```

### Phase 9c: Incremental TDD Tests (One Figure at a Time)

```bash
# Each test class covers ONE public figure
# Run individually: pytest -k "TestSachinTendulkar"
# Run all:         pytest -k "benchmark" --tb=short

// turbo
pytest backend/tests/lk_prediction/test_benchmark.py -v -k "TestSachin" --tb=short
```

### Phase 9d: Full Benchmark Run

```bash
# Run against all available figures, produce metrics report
// turbo
python backend/astroq/lk_prediction/benchmark_runner.py --mode full --output benchmark_results/
```

### Phase 10: Config Tuning

```bash
# Grid search over config knobs to maximize Hit Rate + minimize Offset
// turbo
python backend/astroq/lk_prediction/config_tuner.py --iterations 20 --figures core_10
```

## CRITICAL: Incremental Test Design

Tests MUST be designed so ONE figure can be tested at a time:

```python
# ✅ CORRECT — one-figure-at-a-time
@pytest.mark.benchmark
class TestSachinTendulkar:
    def test_career_debut_hit(self): ...
    def test_world_cup_hit(self): ...

@pytest.mark.benchmark  
class TestAmitabhBachchan:
    def test_stardom_career_hit(self): ...

# ❌ WRONG — all figures in one slow test
def test_all_public_figures(): ...
```

To run a single figure:
```bash
pytest tests/lk_prediction/test_benchmark.py -k "TestSachin" -v
```

To run all benchmark tests (slow, ~5min):
```bash
pytest tests/lk_prediction/test_benchmark.py -m benchmark --tb=short
```

## File Structure

```
backend/astroq/lk_prediction/
├── benchmark_runner.py       # Metric computation engine
└── config_tuner.py           # Grid search tuner

backend/tests/lk_prediction/
├── test_benchmark.py         # Per-figure TDD test classes
└── conftest_benchmark.py     # Shared benchmark fixtures

backend/tests/data/public_figures/
├── sachin_tendulkar_enriched_chart.json
├── amitabh_bachchan_enriched_chart.json
├── narendra_modi_enriched_chart.json
└── ... (84 figures ported from reference)

backend/data/
└── public_figures_ground_truth.json   # Ported from DB

.antigravity/skills/lk-benchmark-tuning/
├── SKILL.md                           # This file
├── resources/
│   └── benchmark_spec.md              # Metric formulas + tuning algorithm
└── memory/
    ├── progress.md
    ├── learnings.md
    └── decisions.md
```

## Config Knobs for Tuning (Phase 10)

Start with these high-impact knobs (search in config.py):

| Key | Default | Range | Impact |
|-----|---------|-------|--------|
| `probability.sigmoid_k` | 0.3 | 0.1–0.7 | Shapes the probability curve |
| `probability.delivery_pucca_ghar` | 1.8 | 1.2–2.5 | Pucca ghar transit boost |
| `probability.delivery_intensification` | 2.0 | 1.5–3.0 | Same-house intensification |
| `probability.delivery_maturation` | 1.8 | 1.2–2.5 | Maturation age spike |
| `timing.maturation_ages.*` | varies | ±5yr | Planet maturation timing |
| `rules.boost_scaling` | 0.04 | 0.02–0.08 | Rule boost impact |
| `rules.penalty_cap` | 0.8 | 0.5–0.95 | Max penalty dampening |
| `event_classifier.threshold_absolute` | 0.70 | 0.55–0.85 | Peak detection cutoff |
| `event_classifier.threshold_delta` | 0.25 | 0.10–0.40 | Momentum requirement |

## Tuning Algorithm (Phase 10)

```
FOR iteration in 1..N:
  FOR knob in tunable_knobs:
    FOR value in knob.range:
      1. Set config override: config.set_override(knob.key, value)
      2. Run benchmark on core_10 figures
      3. Record (hit_rate, offset, natal_acc, fpr) 
      4. If better_than_best: update best_config
  
  Report: best config, metrics delta, recommended overrides
  Save: benchmark_results/iter_{N}_config.json
```

## Success Criteria

The skill is complete when:
- [ ] 10 core figures tested (TDD, per-figure test classes)
- [ ] All 4 metrics computed correctly
- [ ] Hit Rate > 80% (or documented gap with diagnosis)
- [ ] Offset < 2.0yr (or documented)
- [ ] Config tuner ran ≥ 1 full iteration
- [ ] Best config overrides saved to `backend/data/model_defaults_tuned.json`
- [ ] Memory files updated with findings
