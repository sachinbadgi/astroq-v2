# Benchmark & Tuning Skill — Learnings

## 2026-03-22 — Skill Creation (Session 1)
*(See previous entries)*

## 2026-03-22 — Autoresearch Experiments (Superpowers Framework)

**Objective:**
Execute 5 structured experiments to move Hit Rate from 29.41% to >80% and Offset from 5.03 to <2.0.

**Experiments Conducted:**
1. **Classification Thresholds**: Lowered `threshold_absolute` from 0.70 down to 0.35 and `threshold_delta` from 0.25 to 0.05. *Result: No change in Hit Rate (29.41%).*
2. **Probability Sigmoid Curve**: Scaled `sigmoid_k` from 0.15 to 0.40 to stretch/compress probabilities. *Result: No change.*
3. **Delivery Multipliers**: Increased `delivery_pucca_ghar` from 1.5 to 3.5. *Result: No change.*
4. **Rule Scaling**: Increased `rules.boost_scaling` from 0.04 to 0.15. *Result: No change.*
5. **Maturation Peaks**: Set `delivery_maturation` to 0.0 to disable default maturation peaks completely. *Result: No change.*

**Key Learning & Hypothesis:**
The fact that dropping the probability detection thresholds all the way down to `0.35` (where almost any pulse should trigger an event) AND drastically inflating the rule scalers resulted in **zero difference** to the Hit Rate (still 10/34 hits) indicates a **fundamental bottleneck earlier in the pipeline**. 

Because we recently completed Phase 8 (Grammar Analyser Complete), the sheer volume of negative penalties (like Mangal Badh, Dharmis, sleeping planets) are likely structurally suppressing the base `strength_total` below 2.0. In `pipeline.py`, planets with `strength_total < 2.0` that have no overriding rules are completely skipped. 

**Next Steps:**
To improve the model's accuracy, future tuning MUST focus on the base `strength_engine.py` and `grammar_analyser.py` multipliers (e.g. `w_badh`, `w_sleep`) rather than just the final Probability thresholders. The probability scaling works perfectly, but the input magnitudes getting fed into it are structurally flat across all 75 years.
