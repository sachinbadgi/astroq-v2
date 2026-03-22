# Implementation Plan — Chapter 8 (Goswami 1952) Alignment

Align the `RemedyEngine` with specific nuances from Chapter 8 of B.M. Goswami’s 1952 book, including Mars Malefic specifics, Birth Day remedies, and the canonical "Order of Remedies" sequence.

## Proposed Changes

### Configuration
#### [MODIFY] [model_defaults.json](file:///d:/astroq-v2/backend/data/model_defaults.json)
- Add mappings for `remedy.mangal_badh_hints`.
- Add mappings for `remedy.birth_day_remedies`.

### Core Logic
#### [MODIFY] [remedy_engine.py](file:///d:/astroq-v2/backend/astroq/lk_prediction/remedy_engine.py)
- **Special Mars Remedies**: If `mangal_badh_status` is active in the chart, append high-priority Mars-specific hints.
- **Birth Day Remedies**: Implement `_get_birth_weekday()` to derive the native's birth day from `birth_time` and suggest the "Helpful Remedy" accordingly.
- **Order of Remedies**: Implement logic to prioritize planets in "Kendra" houses (1, 10, 7, 4) in the final hint list, following the book's sequence for which remedy to start first.

### Prediction Pipeline
#### [MODIFY] [prediction_translator.py](file:///d:/astroq-v2/backend/astroq/lk_prediction/prediction_translator.py)
- Pass the full `ChartData` or `birth_time` to the `RemedyEngine` methods to enable birth-day aware hints.

---

## Verification Plan

### Automated Tests
- **Unit Tests**: Add tests to `test_remedy_engine.py` to verify:
    - Mars Malefic hints are present when `mangal_badh_status` is "Active".
    - Weekday is correctly derived and the corresponding remedy is suggested.
    - Hints are sorted according to the Kendra house priority (1 > 10 > 7 > 4).
- **Execution**: `pytest backend/tests/lk_prediction/test_remedy_engine.py -v`

### Manual Verification
- Run the interactive chart builder for `sachin` (Born 1977-11-28, a Monday).
- Verify the output includes:
    1. A "Helpful Remedy" based on Monday (Moon's day).
    2. Specific Mars remedies if Mangal Badh is detected.
    3. The hints are ordered starting with House 1 (if any) or follows the Kendra priority.
- **Execution**: `python backend/tests/lk_prediction/interactive_chart_builder.py`
