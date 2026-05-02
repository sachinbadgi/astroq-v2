# Benchmark & Tuning Skill — Progress

## Status: 🔴 NOT STARTED

## Phase Checklist

### Phase 9a: Port Public Figures Data
- [x] Copy 10 core figure JSONs to `backend/tests/data/public_figures/`
- [x] Port ground truth from DB to `backend/data/public_figures_ground_truth.json`
- [x] Verify chart format compatible with new pipeline

### Phase 9b: BenchmarkRunner Implementation
- [x] `backend/astroq/lk_prediction/benchmark_runner.py` created
- [x] `backend/astroq/lk_prediction/config_tuner.py` created
- [x] Unit tests for metric calculations passing

### Phase 9c: Incremental Figure Tests
- [x] `backend/tests/lk_prediction/test_benchmark.py` created
- [x] `TestSachinTendulkar` — tests passing
- [x] `TestAmitabhBachchan` — tests passing
- [x] `TestNarendraModi` — tests passing
- [x] `TestSteveJobs` — tests passing
- [x] `TestBillGates` — tests passing
- [ ] `TestPrincessDiana` — tests passing
- [ ] `TestShahRukhKhan` — tests passing
- [ ] `TestMichaelJackson` — tests passing
- [ ] `TestIndiraGandhi` — tests passing
- [ ] `TestElonMusk` — tests passing

### Phase 9d: Full Benchmark
- [x] Full run completed
- [x] Metrics documented (see below)

### Phase 10: Config Tuning
- [x] Config tuner ran ≥ 1 iteration
- [x] Best config saved to `backend/data/model_defaults_tuned.json`
- [ ] Final metrics hit targets

## Benchmark Scores (updated each run)

| Run | Date | Hit Rate | Offset | Natal Acc | FPR | Notes |
|-----|------|----------|--------|-----------|-----|-------|
| 1 | 2026-03-22 | 29.41% | 5.03 | 100% | 0% | Baseline Run (Targets not hit yet) |

## Target Scores

| Metric | Target |
|--------|--------|
| Hit Rate | > 80% |
| Offset | < 2.0yr |
| Natal Accuracy | > 85% |
| False Positive Rate | < 15% |

## Files Created

- [x] `backend/astroq/lk_prediction/benchmark_runner.py`
- [x] `backend/astroq/lk_prediction/config_tuner.py`
- [x] `backend/tests/lk_prediction/test_benchmark.py`
- [x] `backend/tests/data/public_figures/` (10 core charts)
- [x] `backend/data/public_figures_ground_truth.json`
- [x] `backend/data/model_defaults_tuned.json`
