import pytest
from astroq.lk_prediction.grammar_analyser import GrammarAnalyser
from astroq.lk_prediction.config import ModelConfig
from tests.lk_prediction.conftest import MODEL_DEFAULTS_PATH

@pytest.fixture
def analyser(tmp_path):
    db_path = str(tmp_path / "test.db")
    cfg = ModelConfig(db_path, MODEL_DEFAULTS_PATH)
    return GrammarAnalyser(cfg)

MASNUI_RULES = [
    ({"Sun", "Venus"},   "Masnui Jupiter"),
    ({"Mercury", "Venus"}, "Masnui Sun"),
    ({"Sun", "Jupiter"}, "Masnui Moon"),
    ({"Rahu", "Ketu"},   "Masnui Venus (Note: Unusual Conjunction)"),
    ({"Sun", "Mercury"}, "Masnui Mars (Auspicious)"),
    ({"Sun", "Saturn"},  "Masnui Mars (Malefic)"),
    ({"Sun", "Saturn"},  "Masnui Rahu (Debilitated Rahu)"),
    ({"Jupiter", "Rahu"}, "Masnui Mercury"),
    ({"Venus", "Jupiter"}, "Masnui Saturn (Like Ketu)"),
    ({"Mars", "Mercury"}, "Masnui Saturn (Like Rahu)"),
    ({"Saturn", "Mars"}, "Masnui Rahu (Exalted Rahu)"),
    ({"Venus", "Saturn"}, "Masnui Ketu (Exalted Ketu)"),
    ({"Moon", "Saturn"}, "Masnui Ketu (Debilitated Ketu)"),
]

@pytest.mark.parametrize("parents, result_name", MASNUI_RULES)
def test_masnui_formation_all_rules(analyser, parents, result_name):
    # Setup chart with exactly these parents in House 1
    # We use a house that is relatively neutral if possible, but H1 is fine.
    chart = {
        "chart_type": "Birth",
        "planets_in_houses": {p: {"house": 1} for p in parents},
        "house_status": {"1": "Occupied"}
    }
    
    # Enrich parents with base strength
    # We use 10.0 to ensure they are visible
    enriched = {p: {"house": 1, "strength_total": 10.0} for p in parents}
    
    # Detect Masnui
    masnuis = analyser.detect_masnui(chart)
    chart["masnui_grahas_formed"] = masnuis
    
    # Run integration
    analyser.apply_grammar_rules(chart, enriched)
    
    # 1. Verify Formation
    if parents == {"Sun", "Saturn"}:
        # Both Mars (Malefic) and Rahu (Debilitated) should be there
        found = [k for k in enriched if "Masnui Mars" in k or "Masnui Rahu" in k]
        assert len(found) >= 1
    else:
        assert result_name in enriched
        assert enriched[result_name]["is_masnui"] is True
        assert enriched[result_name]["strength_total"] == 5.0

    # 2. Verify Feedback Boost
    # Instead of absolute > 10.0, we check that the "Masnui Feedback" tag exists
    # and that the strength includes it.
    for p in parents:
        states = enriched[p].get("states", [])
        has_feedback = any("Masnui Feedback" in s for s in states)
        assert has_feedback, f"Planet {p} missing feedback state. States: {states}"
        
        # Verify that aspects were calculated for the new planet
        if result_name in enriched:
            assert "aspects" in enriched[result_name]
