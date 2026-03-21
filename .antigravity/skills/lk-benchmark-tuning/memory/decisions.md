# Benchmark & Tuning Skill — Decisions

## D1: Use JSON ground truth, not DB
**Date:** 2026-03-22  
**Decision:** Ground truth stored in `backend/data/public_figures_ground_truth.json`, NOT queried from DB  
**Rationale:** The new v2 codebase has no DB dependency for benchmarks; JSON is portable and version-controlled  
**Impact:** BenchmarkRunner reads from file, not SQLAlchemy session  

---

## D2: Port raw planet-house data, not enriched output
**Date:** 2026-03-22  
**Decision:** Port only `planets_in_houses` + birth metadata from old enriched charts. Do NOT use old enriched outputs directly.  
**Rationale:** Old enriched charts use old pipeline format (different field names, structure). New v2 pipeline must run fresh.  
**Impact:** Benchmark fixtures store minimal chart data; new pipeline enriches them  
**Format:**
```json
{
  "name": "Sachin Tendulkar",
  "dob": "1973-04-24",
  "birth_chart": { "chart_type": "Birth", "planets_in_houses": {...} },
  "annual_charts": { "1": {...}, "2": {...}, ... "75": {...} }
}
```

---

## D3: Incremental tests — one class per figure
**Date:** 2026-03-22  
**Decision:** Each public figure is its own pytest class, marked with `@pytest.mark.benchmark`  
**Rationale:** Running all 84 figures takes >10min; individual figure tests run in <30s  
**Usage:** `pytest -k "TestSachin"` for fast iteration; `pytest -m benchmark` for full suite  

---

## D4: Config tuner uses grid search (not Bayesian)
**Date:** 2026-03-22  
**Decision:** Phase 10 uses coarse grid search across 9 key config knobs  
**Rationale:** Grid search is deterministic, reproducible, and easy to debug. Bayesian optimization is overkill for 9 knobs.  
**Knob ranges:** See SKILL.md → "Config Knobs for Tuning"  
**Output:** `backend/data/model_defaults_tuned.json` — best config found  

---

## D5: Hit window is ±2 years (from spec)
**Date:** 2026-03-22  
**Decision:** A prediction is a "hit" if `abs(predicted_peak_age - actual_age) <= 2`  
**Rationale:** Matches the spec metric definition and old `AccuracyChecker` logic  

---

## D6: Core-10 figures for tuning, all 84 for final validation
**Date:** 2026-03-22  
**Decision:** Phase 10 tuning runs against just the 10 core figures (fast ~2min). Final validation runs all 84.  
**Rationale:** Core 10 have the best-validated ground truth (from CELEBRITY_DATA). Full 84 for final soundness check.  
