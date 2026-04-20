# Pipeline Data Integrity

This page documents the data isolation principles and architectural guardrails required to prevent **Planetary Location Hallucinations** in the Lal Kitab pipeline.

## The "Shadow Variable" Trap

Because Python uses references for dictionaries, the nested structures within the `full_payload` (specifically `planets_in_houses`) can inadvertently be shared between the Natal and Annual chart objects.

### The Failure Mode
If the `LKPredictionPipeline` loops through 75 years of annual charts without **Deep Copying**, any modification or enrichment applied to an annual chart (e.g., adding "Masnui" flags or temporary house shifts) can bleed back into the Natal chart object if they share the same dictionary identity.

**Historical Bug**: In April 2026, a bug was found where the `planets_data` variable in `generate_llm_payload` was shadowed in the annual timeline loop. This caused the **Natal Profile** to always show the planetary positions of the **75th year (Age 74)** instead of the birth placements.

## Data Isolation Mandates

1. **Explicit Immortality**: Natal chart data must be considered **ReadOnly** once loaded. Use `copy.deepcopy()` immediately upon ingestion in `load_natal_baseline`.
2. **Local Scoping**: Every annual year processing step in the `timeline` must operate on its own unique copy of the chart data.
3. **Variable Naming**: Avoid generic names like `planets_data` or `enriched` in methods that process both Natal and Annual data in the same scope. Use `natal_planets_data` vs `annual_planets_data`.

## System Consistency (Vedic vs KP)

Lal Kitab analysis is highly sensitive to the Ayansama and House System.
- **Rule**: Never mix `vedic` (Lahiri/Whole Sign) and `kp` (Krishnamurti/Placidus) systems for the same person.
- **Enforcement**: The `ChartGenerator.build_full_chart_payload` must strictly inherit the `chart_system` for all yearly charts.

## Verification Workflow

Whenever the `pipeline.py` or `chart_generator.py` is modified:
1. Run a regeneration of the "sachin" profile (the ground truth).
2. Compare the generated `natal_promise_baseline` against the expected birth data.
3. Verify that **Jupiter** remains in its expected house (e.g., House 2 for Vedic, House 1 for KP).
4. Confirm that the **Ascendant (Asc)** marker is entirely absent from the planetary dictionaries.
5. Verify that no probabilistic fields (`probability`, `belief`, `confidence`) exist in the output JSON.
