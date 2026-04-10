# AutoResearch 2.0 (LSE) — Specification

> **LSE** = **L**earn · **S**elf-Evolve  
> A dual-agent system that back-tests every rule against a user's life events,
> discovers the chart-specific "delay constants" that generic rules miss,
> and then generates high-confidence future predictions using the personalised model.

---

## 1. Overview (The Core Idea)

The prediction engine already has ~1 000+ deterministic rules. However, two
charts with the same house-planet configuration can produce **different timing**.
Why? Because each chart has its own grammar overrides (sleeping houses, Mars
delays, travel cancellations, Rin debts) that shift the raw rule timing by
months or years.

AutoResearch 2.0 solves this by treating the past as a "training set":

```
Past Events (known) ──► Fit personalised model ──► Future predictions (confident)
```

The system uses **two cooperating agents**:

| Agent | Role |
|-------|------|
| **Researcher** | Hypothesis generation — reads rule failures and proposes grammar corrections |
| **Validator** | Simulation execution — re-runs the pipeline with each hypothesis and reports metrics |

They iterate until the **historical hit rate reaches ≥ 95%**, then the final
model generates future predictions.

---

## 2. Step-by-Step Example: Solving a Specific Horoscope

### 📥 Step 1: Input Data (The "Baseline")

The user provides birth details and a **Life Event Log** for back-testing.

**Chart**: Sun in H1, Jupiter in H9, Saturn in H10.

**Life Events**:

| Age | Event |
|-----|-------|
| 18  | Move to foreign city for studies |
| 24  | First major job in finance |
| 29  | Marriage |
| 35  | Sudden health issue related to stomach |

---

### 🔬 Step 2: Phase 1 — Knowledge Extraction

The **Researcher Agent** scans the Lal Kitab PDFs and the current `rules.db`
for every condition triggered by this specific chart.

**Identified Rules**:

| Rule ID | Rule | Source |
|---------|------|--------|
| Rule A | Sun in H1 + Jupiter in H9 = "Ruler of the World" (Great wealth) | LK p. 87 |
| Rule B | Saturn in H10 = "Stone Heart" (Strict career, sudden fall) | LK p. 134 |
| Rule C | H4 is empty → H10 is a "Sleeping House" (grammar override) | LK Grammar |

---

### ⚙️ Step 3: Phase 2 — Initial Simulation (The Gap)

The **Validator Agent** runs `run_prediction_pipeline()` for ages 1–75 and
reports results back to the Researcher.

**Validator Report**:

| Rule | Predicted Age | Actual Age | Result |
|------|--------------|------------|--------|
| Rule A (wealth) | 22 | 24 | ❌ FAIL (2-yr offset) |
| Rule B (fall) | 30 | 35 | ❌ FAIL (5-yr offset) |
| Rule C (sleeping H10) | no career events | Job at 24 | ❌ CONTRADICTION |

---

### 🧠 Step 4: Phase 3 — Dual-Agent Evolution (Solving the Chart)

The Researcher and Validator **iterate** to find the "Chart DNA".

#### Iteration 1

**Hypothesis**: "Maybe the 'Sleeping House' rule for H10 is cancelled because
the user moved cities (H12 activity) at age 18?"

- **Test**: Validator re-runs with `h12_travel_cancels_h10_sleep = True`.
- **Result**: Job at 24 now appears. But timing is still 2 years off.

#### Iteration 2

**Hypothesis**: "Mars is in H8 (malefic). In Lal Kitab p. 142, Mars H8 delays
Sun H1 results by 1/8th of the cycle (~2.5 years)."

- **Test**: Validator applies `mars_h8_delay_constant = 2.5` to all Sun H1 rules.
- **Result**: 
  - Predicted Job moves from Age 22 → **24.5** ✅ HIT
  - Predicted Health issue moves from Age 32 → **35.0** ✅ HIT

#### Convergence Criteria

| Metric | Target |
|--------|--------|
| Back-test Hit Rate | ≥ 95% (events within ±1 yr of actual) |
| Mean Absolute Offset | ≤ 1.0 yr |
| Max iterations | 20 |

---

### 🎯 Step 5: Phase 4 — High-Confidence Future Prediction

Once the past is explained, the system generates **future predictions** using
the personalised model (with all delay constants and grammar overrides applied).

**Confidence Score**: 98%  
*(Derived from: back-test hit rate of 100% across 4 historical events)*

**Example Prediction**:
> "At Age 42, Rule B (Saturn H10) will trigger a property purchase. However,
> because of the fixed 2.5-year Mars H8 delay constant discovered during
> back-testing, this will actually manifest at **Age 44.5**."

---

## 3. The "LSE" Mechanics

| Component | What it Does |
|-----------|-------------|
| **Learn (L)** | Extracts delay constants and grammar overrides from the user's historical event match |
| **Self-Evolve (SE)** | Mutates the generic rule-set into a **Personalised Model** specific to this one user |

The personalised model is stored as a set of `ModelConfig` figure-specific
overrides (see `config.py: set_override(key, value, figure="{name}")`).

---

## 4. Data Structures

### 4.1 Life Event Log (Input)

```python
LifeEvent = {
    "age": int,                  # Age at which the event occurred
    "domain": str,               # "profession", "health", "marriage", etc.
    "description": str,          # Free-text description
    "is_verified": bool          # True if independently confirmed
}

LifeEventLog = list[LifeEvent]
```

### 4.2 Chart DNA (Output of Back-Testing)

```python
ChartDNA = {
    "figure_id": str,            # Unique figure identifier
    "back_test_hit_rate": float, # 0.0 – 1.0
    "mean_offset_years": float,  # MAE in years
    "iterations_run": int,
    "alignments": {
        # planet_house: target milestone age
        "mars_h8": 28,
        "saturn_h4": 36,
    },
    "grammar_overrides": {
        # rule_id or grammar_key: override value
        "h10_sleeping_cancelled_by_h12_travel": True,
    },
    "config_overrides": dict,    # Saved to ModelConfig as figure overrides
    "confidence_score": float,   # Derived from back_test_hit_rate
    "generated_at": str          # ISO timestamp
}
```

### 4.3 LSE Prediction (Final Output)

```python
LSEPrediction = {
    **LKPrediction,              # All standard prediction fields (see data_contracts.py)
    "personalised": True,
    "chart_dna_applied": ChartDNA,
    "raw_peak_age": int,         # Before delay constant applied
    "adjusted_peak_age": float,  # After delay constant applied
    "confidence_source": str,    # "back_test_100pct" | "back_test_partial" | "generic"
}
```

---

## 5. Algorithm

```
FUNCTION solve_chart(birth_chart, life_event_log, max_iterations=20):

  # Phase 1: Knowledge Extraction
  rules = researcher.extract_applicable_rules(birth_chart)
  
  # Phase 2: Initial Simulation
  baseline_predictions = validator.run_pipeline(birth_chart, config=DEFAULT)
  gap_report = validator.compare_to_events(baseline_predictions, life_event_log)
  
  # Phase 3: Iterative Evolution
  best_dna = None
  best_hit_rate = 0.0
  
  FOR iteration in 1..max_iterations:
    # UPDATED: find_rationale() looks for specific LK conditions for each gap
    hypotheses = []
    FOR gap in gap_report.entries:
        IF gap.is_hit: CONTINUE
        
        rationale = researcher.find_astrological_rationale(gap, birth_chart)
        IF rationale:
            hypotheses.extend(researcher.generate_hypotheses_from_rationale(rationale))
    
    FOR hypothesis in hypotheses:
      config = apply_hypothesis(DEFAULT_CONFIG, hypothesis)
      predictions = validator.run_pipeline(birth_chart, config)
      result = validator.compare_to_events(predictions, life_event_log)
      
      IF result.hit_rate > best_hit_rate:
        best_hit_rate = result.hit_rate
        best_dna = build_chart_dna(hypothesis, result)
      
      gap_report = result.gap_report
    
    IF best_hit_rate >= 0.95:
      BREAK

  # Phase 4: Future Predictions
  SAVE best_dna as figure config overrides
  RETURN validator.run_pipeline(birth_chart, config=best_dna.config_overrides)

---

### 9. Astrological Rationale Rules (Milestones)
The Researcher doesn't just "guess" delays. It must find a matching Lal Kitab condition and align to the nearest canonical milestone:

| Condition | Astrological Logic | Proposed Alignment |
|-----------|--------------------|---------------------|
| **Takrav (Confrontation)** | Sun H1 vs Saturn H7. Mutual aspect. | Age 36 (Saturn Maturity) |
| **Soya Ghar (Sleeping)** | Target house is empty + no activation. | Age 36 (Saturn Maturity) |
| **Grah-Yuti (Enmity)** | Jupiter with Rahu/Ketu (Guru-Chandal). | Age 42 (Rahu Maturity) |
| **Mars-H8 (Badh)** | Mars in H8 triggers delays. | Age 28 (Mars Maturity) |
| **Saturn H5 (Blind)** | Progeny delay until cycle end. | Age 48 (Ketu/Cycle) |
| **Cycle Reset** | 35-Year Cycle Completion. | Age 36 (Reset Year) |

---

## 6. Integration Points

| System Component | How LSE Uses It |
|-----------------|----------------|
| `pipeline.py` | Core `run_prediction_pipeline()` — called by Validator in every iteration |
| `config.py` | `set_override(key, value, figure=id)` — stores discovered delay constants |
| `rules_engine.py` | Researcher reads `fired_rules` to identify which rules triggered (or didn't) |
| `benchmark_runner.py` | LSE reuses its `compare_to_events()` metric logic for back-testing |
| `grammar_analyser.py` | Grammar override hypotheses are tested via config flags |
| `rules.db` | Read-only. LSE never mutates the rules DB — only config overrides |

---

## 7. Confidence Score Formula

```
confidence_score = (
    back_test_hit_rate * 0.70      # Primary signal
  + (1 - mean_offset_years / 5) * 0.20   # Timing precision (capped at 5yr)
  + verified_event_ratio * 0.10   # Weight for verified vs self-reported events
)
```

Range: 0.0 – 1.0. A score ≥ 0.90 unlocks `"certain"` confidence tier in the
`PredictionTranslator`.

---

## 8. Success Criteria

| Criterion | Target |
|-----------|--------|
| Back-test Hit Rate | ≥ 95% on historical events |
| Mean Offset | ≤ 1.0 year |
| Iterations to Convergence | ≤ 15 (average) |
| Confidence Score | ≥ 0.90 for well-documented charts |
| Future Prediction Coverage | All 8 life domains |
