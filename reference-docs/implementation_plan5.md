# Integration of Lal Kitab Chapters 16-19 Rules

## Goal Description
Integrate the deterministic astrological rules from chapters 16, 17, 18, and 19 of B.M. Gosvami's 1952 Lal Kitab into the prediction model. These chapters cover specifically:
- **Chapter 16**: Individuals Dominated by Planets, Professions, Service Income, and Travel directions.
- **Chapter 17**: Marriage timing, propitious/inauspicious conditions, number of marriages, and Progeny (child birth, gender, issuelessness).
- **Chapter 18**: Money Matters (Income unit calculations based on exalted/live planets).
- **Chapter 19**: Additional related domains.

The goal is to update the core `lk_prediction_model_v2.md` document with these domains, write TDD tests for the rule resolution, and finally inject the compiled rules into the SQLite `rules.db` so the `RulesEngine` can evaluate them.

## Proposed Changes

### Model Documentation
#### [MODIFY] lk_prediction_model_v2.md
- Add the new domains: `service/profession`, `travel`, `marriage`, `progeny`, and `wealth/income` to the "Deterministic Rules Engine" section.
- Outline the specific condition structures required for these rules. For instance, testing for "Sun-Mercury together in H1" or "Venus in H4".

### TDD Tests
#### [MODIFY] backend/tests/lk_prediction/test_rules_engine.py
- Following the "SUPERPOWERS TDD" approach, write failing test cases first. 
- Create test functions for specific new rules (e.g. `test_marriage_rule_venus_h4`, `test_progeny_rule_ketu_h11`) by injecting mock rules into the in-memory SQLite test DB.
- Ensure the rule evaluation correctly applies `AND`, `OR`, `NOT`, and `placement` conditions for the new rule payloads.

### Rules Data Seeding
#### [NEW] backend/scripts/add_gosvami_ch16_19_rules.py
- Create a Python script to insert exactly the newly extracted rules into `backend/data/rules.db`.
- The rules will be formatted with correct JSON `condition` string, mapping to `target_houses`, `primary_target_planets`, `scoring_type`, `scale`, and `domain`.
- Examples of rules to add:
  - **Marriage**: Venus in H.No. 4 comes to H.No. 4 in annual chart -> Marriage doubtful/delayed (Penalty).
  - **Progeny**: Ketu in H.No. 11 along with male planets in H.No. 1/5 -> Male Child (Boost).
  - **Progeny**: Rahu-Ketu-Saturn in H.No. 5 -> Obstruction in child birth (Penalty).
  - **Travel**: Ketu in H.No. 7 -> Change of city/travel certain and auspicious (Boost).
  - **Profession**: Sun in H.No. 10 -> Accounts/Books/Govt (Boost).

## Verification Plan
### Automated Tests
- Run `pytest backend/tests/lk_prediction/test_rules_engine.py -v` to ensure the core rules engine can correctly parse and apply the new condition structures without errors.
- Run `python backend/scripts/add_gosvami_ch16_19_rules.py` to safely inject rules into `rules.db`.

### Manual / Structural Verification
- Check `sqlite3 backend/data/rules.db "SELECT count(*) FROM deterministic_rules WHERE source_page LIKE '%Gosvami%'"` to verify insertion.
- Generate a test chart containing one of the specific triggers (e.g. Ketu in H7) using `backend/generate_test_chart.py` and ensure the pipeline outputs the corresponding prediction.
