# Benchmark Specification — Lal Kitab Prediction Model v2

## 1. Data Format

### Public Figure Chart File
Each figure has a JSON with raw chart data for birth + 75 annual years:
```json
{
  "name": "Sachin Tendulkar",
  "dob": "1973-04-24",
  "tob": "16:15",
  "place": "Mumbai, India",
  "birth_chart": {
    "chart_type": "Birth",
    "chart_period": 0,
    "planets_in_houses": { "Sun": {"house": 4, ...}, ... },
    "house_status": {}
  },
  "annual_charts": {
    "1":  { "chart_type": "Yearly", "chart_period": 1, "planets_in_houses": {...} },
    "16": { "chart_type": "Yearly", "chart_period": 16, "planets_in_houses": {...} },
    ...
  }
}
```

### Ground Truth File (`public_figures_ground_truth.json`)
```json
[
  {
    "name": "Sachin Tendulkar",
    "events": [
      {"age": 16, "domain": "profession", "description": "International cricket debut"},
      {"age": 22, "domain": "marriage",   "description": "Marriage to Anjali"},
      {"age": 38, "domain": "profession", "description": "Cricket World Cup victory"},
      {"age": 40, "domain": "profession", "description": "Retirement from cricket"}
    ]
  }
]
```

## 2. Metric Formulas

### Hit Rate
```
hit = abs(predicted_peak_age - actual_age) <= HIT_WINDOW (default: 2)
hit_rate = count(hits) / count(all_events)
target: > 0.80
```

### Offset (Mean Absolute Error)
```
offset_per_event = abs(closest_peak_age - actual_age)
  where closest_peak_age = argmin_age(peaks, key=|age - actual_age|)
avg_offset = mean(offset_per_event) across all events
target: < 2.0
```

### Natal Accuracy
```
natal_correct = domain_detected_at_natal_level == event.domain
natal_accuracy = count(natal_correct) / count(all_events)
target: > 0.85
```

### False Positive Rate
```
fp = predicted_peaks that have NO ground_truth event within ±3 years
fpr = count(fp) / count(all_predicted_peaks)
target: < 0.15
```

## 3. Benchmark Runner Algorithm

```
FOR each figure in ground_truth:
  1. Load birth_chart + annual_charts JSON
  2. Run strength + grammar on birth_chart → natal_enriched
  3. FOR each domain in figure.events:
     a. Run run_domain_model(domain, natal_enriched, annual_charts) → prob_curve
     b. Detect peaks: years where probability > threshold AND delta > min_delta
     c. FOR each event in domain.events:
        - Find closest peak to event.age
        - Compute hit (±2yr), offset (years error)
        - Check natal_accuracy: does natal prob for domain > 0.5?
     d. Collect FP: peaks with no GT event within ±3yr
  4. Save figure_metrics = {hit_rate, offset, natal_accuracy, fpr}

5. Aggregate all figures → global_metrics
6. Report: table per figure + overall aggregate
```

## 4. Config Tuner Algorithm

```
GRID SEARCH (coarse first, fine second):

Phase 1 — Coarse (3 values per knob, ~100 combinations):
  knobs = [sigmoid_k, pucca_ghar, intensification, maturation,
           boost_scaling, penalty_cap, abs_threshold, delta_threshold]
  
  FOR config in cartesian_product(knob_ranges):
    SET config overrides
    RUN benchmark on core_10 figures (fast ~2min)
    RECORD (hit_rate, offset, natal_acc, fpr, composite_score)
    
  composite_score = (hit_rate/0.80) + (1 - offset/2.0) + (natal_acc/0.85) + (1 - fpr/0.15)
  FIND top_5_configs by composite_score

Phase 2 — Fine (narrow range around top configs):
  FOR each of top_5_configs:
    RUN fine grid around each knob ±20%
    PICK best config

Phase 3 — Validate:
  RUN best_config on all 84 figures
  REPORT final metrics
  SAVE to backend/data/model_defaults_tuned.json
```

## 5. Composite Score Formula

```python
def composite_score(metrics):
    hr_score   = metrics["hit_rate"]    / 0.80   # 1.0 = at target
    off_score  = 1.0 - metrics["offset"] / 2.0   # 1.0 = at target
    nat_score  = metrics["natal_acc"]   / 0.85
    fpr_score  = 1.0 - metrics["fpr"]   / 0.15
    return (hr_score + off_score + nat_score + fpr_score) / 4.0
    # > 1.0 means all metrics beat target
```
