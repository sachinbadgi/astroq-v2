# Benchmark & Tuning Skill — Learnings

## 2026-03-22 — Skill Creation (Session 1)

### Key Findings from Reference Codebase

**Public Figures Data:**
- 84 public figures with enriched chart JSONs in `D:\astroq-mar26\backend\tests\data\public_figures\`
- Chart format: `{"chart_0": {...birth chart...}, "chart_1": {...year 1...}, ..., "chart_75": {...}}`
- Each `chart_N` is a full enriched pipeline output with `planets_in_houses`, `mangal_badh_status`, etc.
- Ground truth lives in `astroq.db` → `benchmark_ground_truth` table
- Fields: `figure_name`, `event_name`, `age`, `domain`, `event_date`

**10 Core Figures (from benchmark_dataset.py CELEBRITY_DATA):**
1. Amitabh Bachchan — 4 events (Career/Marriage/Health/Finance)
2. Sachin Tendulkar — 4 events (Career×3, Marriage)  
3. Narendra Modi — 3 events (Career×3)
4. Steve Jobs — 4 events (Career×3, Health)
5. Bill Gates — 3 events (Career, Marriage×2)
6. Princess Diana — 3 events (Marriage×2, Health)
7. Shah Rukh Khan — 3 events (Marriage, Career×2)
8. Michael Jackson — 4 events (Career×2, Legal, Health)
9. Indira Gandhi — 3 events (Career×2, Health)
10. Elon Musk — 3 events (Career×2, Finance)

**Old BenchmarkRunner Architecture:**
- The old `run_accuracy_benchmark.py` used DB-stored ground truth
- New implementation should use `backend/data/public_figures_ground_truth.json` instead (no DB dep)
- Hit = `abs(predicted_age - actual_age) <= 2` (±2 year window)
- Old runner detected "closest_peak_age" from probability curve's detected peaks

**Chart Format Notes:**
- The new `pipeline.py` produces `list[LKPrediction]`, NOT a 75-year curve dict
- The new `benchmark_runner.py` must use `run_prediction_pipeline()` and assess peak ages
- The key bridge: `probability_engine.run_domain_model()` returns `list[dict]` with `age` + `probability` per year

**AccuracyChecker Pattern (from old code):**
```python
# A hit is when the closest peak is within ±2 years
peaks = [yr for yr, p in prob_curve if p > threshold]
closest_peak = min(peaks, key=lambda age: abs(age - actual_age))
is_hit = abs(closest_peak - actual_age) <= 2
offset = abs(closest_peak - actual_age)
```

### Design Decisions Made
- See `decisions.md` for architectural choices settled today

### Things to Watch Out For
- The enriched chart JSONs from the old codebase use the OLD pipeline format (not the new v2 format)
- We CANNOT directly use them as input to the new pipeline — we need to extract `planets_in_houses` and re-run through new pipeline
- Alternatively: port just the birth/annual PLANET-HOUSE data (not enriched outputs) and generate new enriched data
- **RECOMMENDED**: Extract raw planet-house data from old enriched charts, run through new v2 pipeline
