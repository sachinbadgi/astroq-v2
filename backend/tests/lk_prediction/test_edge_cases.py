"""
Edge Case Tests for AstroQ Prediction Engine.
Covers complex interactions identified during audit:
1. Dharmi Kundli vs Mangal Badh interaction.
2. Nested Masnui formations.
3. Probability Engine clamping and extreme strength handling.
"""

import json
import sqlite3
import pytest
from astroq.lk_prediction.grammar_analyser import GrammarAnalyser
from astroq.lk_prediction.probability_engine import ProbabilityEngine
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.data_contracts import ChartData, EnrichedPlanet
from astroq.lk_prediction.items_resolver import LKItemsResolver

@pytest.fixture
def tmp_db(tmp_path):
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE IF NOT EXISTS model_config (key TEXT PRIMARY KEY, value TEXT, figure TEXT)")
    conn.commit()
    conn.close()
    return str(db)

@pytest.fixture
def tmp_defaults(tmp_path):
    defaults = {"prob.cap_upper": 0.95, "prob.cap_lower": 0.05}
    f = tmp_path / "defaults.json"
    f.write_text(json.dumps(defaults))
    return str(f)

@pytest.fixture
def config(tmp_db, tmp_defaults):
    return ModelConfig(db_path=tmp_db, defaults_path=tmp_defaults)

@pytest.fixture
def grammar_analyser(config):
    return GrammarAnalyser(config)

@pytest.fixture
def prob_engine(config):
    return ProbabilityEngine(config)

# --------------------------------------------------------------------------
# 1. LKItemsResolver verification
# --------------------------------------------------------------------------

def test_items_resolver_real_data():
    """Verify that LKItemsResolver returns real data from the XLSX extraction."""
    resolver = LKItemsResolver()
    
    # Jupiter in H2 (Cowshed, Turmeric etc)
    items = resolver.get_planet_items("Jupiter", 2)
    assert "Turmeric" in items
    assert "Cowshed" in items
    
    # Rahu in H11 (Blue sapphire)
    rahu_items = resolver.get_planet_items("Rahu", 11)
    assert any("Blue sapphire" in it for it in rahu_items)
    
    # Sun Relatives H1 (Self)
    relatives = resolver.get_planetary_relatives("Sun", 1)
    assert "Self" in relatives

# --------------------------------------------------------------------------
# 2. Dharmi vs Mangal Badh Interaction
# --------------------------------------------------------------------------

def test_dharmi_mitigates_mangal_badh(grammar_analyser):
    """
    If a chart is Mangal Badh but also Dharmi (Jupiter + Saturn), 
    the Dharmi boost should mitigate the Mangal Badh penalty.
    """
    # Mangal Badh: Mars in H4, Sun in H1 (R2 logic)
    # Dharmi Kundli: Jupiter + Saturn in H4
    chart: ChartData = {
        "planets_in_houses": {
            "Mars": {"house": 4},
            "Sun": {"house": 1},
            "Jupiter": {"house": 4},
            "Saturn": {"house": 4}
        }
    }
    
    enriched = {
        "Mars": {"strength_total": 10.0, "house": 4},
        "Sun": {"strength_total": 10.0, "house": 1},
        "Jupiter": {"strength_total": 10.0, "house": 4},
        "Saturn": {"strength_total": 10.0, "house": 4}
    }
    
    grammar_analyser.apply_grammar_rules(chart, enriched)
    
    # 1. Verify status on chart
    assert chart.get("mangal_badh_status") == "Active"
    
    # 2. Verify status on enriched planet
    mars_meta = enriched["Mars"]
    assert mars_meta["dharmi_status"] == "Dharmi Teva"
    
    # 3. Strength check
    assert mars_meta["strength_breakdown"]["mangal_badh"] < 0
    assert mars_meta["strength_breakdown"]["dharmi"] > 0

# --------------------------------------------------------------------------
# 3. Nested Masnui Formations
# --------------------------------------------------------------------------

def test_nested_masnui_formation(grammar_analyser):
    """
    Verify that Artificial planets are detected in the chart.
    """
    # Sun + Venus in H1 = Artificial Jupiter
    chart: ChartData = {
        "planets_in_houses": {
            "Sun": {"house": 1},
            "Venus": {"house": 1}
        }
    }
    
    enriched = {
        "Sun": {"strength_total": 10.0, "house": 1},
        "Venus": {"strength_total": 10.0, "house": 1}
    }
    
    grammar_analyser.apply_grammar_rules(chart, enriched)
    
    masnuis = chart.get("masnui_grahas_formed", [])
    found = any(m["masnui_graha_name"] == "Artificial Jupiter" for m in masnuis)
    assert found is True

# --------------------------------------------------------------------------
# 4. Probability Clamping and Extreme Strength
# --------------------------------------------------------------------------

def test_probability_clamping_extreme_strength(prob_engine):
    """
    Ensure ProbabilityEngine handles extreme strengths and clamps results.
    """
    event_high = {"planet": "Sun", "magnitude": 500.0, "natal_score": 100.0, "prob_t_minus_1": 0.5}
    event_low = {"planet": "Saturn", "magnitude": -500.0, "natal_score": -100.0, "prob_t_minus_1": 0.5}
    
    res_high = prob_engine.batch_evaluate([event_high], age=40)[0]
    res_low = prob_engine.batch_evaluate([event_low], age=40)[0]
    
    assert res_high["final_probability"] <= 0.9501
    assert res_low["final_probability"] >= 0.0499
