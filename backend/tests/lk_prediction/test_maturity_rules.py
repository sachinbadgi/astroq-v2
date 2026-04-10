import json
import sqlite3
import pytest

from astroq.lk_prediction.rules_engine import RulesEngine
from astroq.lk_prediction.config import ModelConfig


def _seed_maturity_rules(db_path: str) -> None:
    """Seed a test DB with the specific maturity / rationale rules being tested."""
    con = sqlite3.connect(db_path)
    con.execute("""CREATE TABLE IF NOT EXISTS deterministic_rules (
        id TEXT PRIMARY KEY, domain TEXT, description TEXT, condition TEXT,
        verdict TEXT, scale TEXT, scoring_type TEXT, source_page TEXT,
        success_weight REAL)""")
    rules = [
        # Age-36 cycle rule
        ("LK_MAT_CYC_36_MARR", "marriage", "New cycle at 36",
         json.dumps({"type": "placement", "planet": "Saturn", "houses": [4]}),
         "Cycle Marriage", "major", "boost", "p1", 0.9),
        # Rationale rule: Saturn in H4 at age 36
        ("RAT_SATURN_H4_36", "career", "Saturn H4 rationale",
         json.dumps({"type": "placement", "planet": "Saturn", "houses": [4]}),
         "Saturn H4 verdict", "moderate", "penalty", "p2", 0.7),
        # Rationale rule: Venus in H10 at age 36
        ("RAT_VENUS_H10_36", "wealth", "Venus H10 rationale",
         json.dumps({"type": "placement", "planet": "Venus", "houses": [10]}),
         "Venus H10 verdict", "moderate", "boost", "p3", 0.8),
        # Rahu in H9 maturity rule (age 42)
        ("RAT_RAHU_H9_42", "fortune", "Rahu H9 maturity",
         json.dumps({"type": "placement", "planet": "Rahu", "houses": [9]}),
         "Rahu H9 verdict", "major", "boost", "p4", 0.85),
        # Mercury in H9 maturity rule (age 34)
        ("RAT_MERCURY_H9_34", "wealth", "Mercury H9 maturity",
         json.dumps({"type": "placement", "planet": "Mercury", "houses": [9]}),
         "Mercury H9 verdict", "major", "boost", "p5", 0.8),
    ]
    con.executemany(
        "INSERT OR REPLACE INTO deterministic_rules VALUES (?,?,?,?,?,?,?,?,?)",
        rules,
    )
    con.commit()
    con.close()


@pytest.fixture
def rules_engine(tmp_db, tmp_defaults):
    """Self-contained RulesEngine using tmp fixtures (no production DB dependency)."""
    _seed_maturity_rules(tmp_db)
    config = ModelConfig(db_path=tmp_db, defaults_path=tmp_defaults)
    return RulesEngine(config)

def test_saturn_maturity_rules(rules_engine):
    # Mock data for Age 36
    # RulesEngine expects 'chart_period' for age
    # and 'planets_in_houses' for placement
    chart_36 = {
        "chart_period": 36,
        "planets_in_houses": {
            "Saturn": {"house": 4, "aspects": []},
            "Venus": {"house": 10, "aspects": []}
        },
        "house_status": {"10": "Occupied"}
    }
    
    hits = rules_engine.evaluate_chart(chart_36)
    rule_ids = [h.rule_id for h in hits]
    
    # 1. New Cycle rule (ID: LK_MAT_CYC_36_MARR)
    assert "LK_MAT_CYC_36_MARR" in rule_ids
    
    # 2. Migrated Rationale rule (ID: RAT_SATURN_H4_36)
    assert "RAT_SATURN_H4_36" in rule_ids
    
    # 3. Migrated Rationale rule (ID: RAT_VENUS_H10_36)
    assert "RAT_VENUS_H10_36" in rule_ids

def test_rahu_maturity_rules(rules_engine):
    # Mock data for Age 42
    chart_42 = {
        "chart_period": 42,
        "planets_in_houses": {
            "Rahu": {"house": 9, "aspects": []}
        }
    }
    
    hits = rules_engine.evaluate_chart(chart_42)
    rule_ids = [h.rule_id for h in hits]
    
    # 1. Rahu in H9 Maturity rule
    assert "RAT_RAHU_H9_42" in rule_ids

def test_mercury_maturity_rules(rules_engine):
    # Mock data for Age 34
    chart_34 = {
        "chart_period": 34,
        "planets_in_houses": {
            "Mercury": {"house": 9, "aspects": []}
        }
    }
    
    hits = rules_engine.evaluate_chart(chart_34)
    rule_ids = [h.rule_id for h in hits]
    
    # 1. Mercury in H9 Maturity rule
    assert "RAT_MERCURY_H9_34" in rule_ids
