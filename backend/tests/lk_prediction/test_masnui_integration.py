import pytest
from astroq.lk_prediction.grammar_analyser import GrammarAnalyser
from astroq.lk_prediction.config import ModelConfig
from tests.lk_prediction.conftest import MODEL_DEFAULTS_PATH

def test_masnui_jupiter_strength_and_feedback(tmp_path):
    # Setup
    db_path = str(tmp_path / "test.db")
    cfg = ModelConfig(db_path, MODEL_DEFAULTS_PATH)
    analyser = GrammarAnalyser(cfg)

    # Mock chart: Sun and Venus in House 1 should form Artificial Jupiter
    chart = {
        "chart_type": "Birth",
        "planets_in_houses": {
            "Sun": {"house": 1, "is_masnui": False},
            "Venus": {"house": 1, "is_masnui": False}
        },
        "house_status": {"1": "Occupied"}
    }
    
    # 1. Detect Masnui
    masnuis = analyser.detect_masnui(chart)
    chart["masnui_grahas_formed"] = masnuis
    
    # 2. Apply Grammar (Integration)
    # Give parents some base strength to see the delta
    enriched = {
        "Sun": {"house": 1, "strength_total": 10.0},
        "Venus": {"house": 1, "strength_total": 10.0}
    }
    analyser.apply_grammar_rules(chart, enriched)
    
    # 3. Assertions
    assert "Masnui Jupiter" in enriched
    m_jup = enriched["Masnui Jupiter"]
    assert m_jup["strength_total"] == 5.0 # Base strength for Masnui
    
    # Debug prints
    print(f"\nSun Strength: {enriched['Sun']['strength_total']}")
    print(f"Sun States: {enriched['Sun'].get('states', [])}")
    print(f"Venus Strength: {enriched['Venus']['strength_total']}")
    print(f"Venus States: {enriched['Venus'].get('states', [])}")

    # Feedback check: 5.0 * 0.3 = 1.5 boost to each parent
    # Plus whatever other rules fired
    assert any("Masnui Feedback" in s for s in enriched["Sun"]["states"])
    assert enriched["Sun"]["strength_total"] >= 11.5
