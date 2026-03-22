"""
Phase D: Tvp Boost Integration Tests for ProbabilityEngine.
"""

from __future__ import annotations

import json
import sqlite3
import pytest

from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.probability_engine import ProbabilityEngine

@pytest.fixture
def dummy_config(tmp_path):
    defaults = {
        "probability.adaptive_k_active": False,
        "probability.base_k": 1.0,
        "probability.ea_base": 0.5,
        "probability.tvp_boost_factor": 1.2,
        "probability.prob_cap_upper": 0.95,
        "probability.prob_cap_lower": 0.05,
        "remedy.tvp_boost_per_unit": 0.25, # Custom boost: 25%
    }
    f = tmp_path / "defaults.json"
    f.write_text(json.dumps(defaults))
    
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE IF NOT EXISTS model_config (key TEXT PRIMARY KEY, value TEXT, figure TEXT)")
    conn.commit()
    conn.close()
    return ModelConfig(db_path=str(db), defaults_path=str(f))


class TestProbabilityEngineTvpBoost:

    def test_tvp_boost_increases_when_remedy_applied_safely(self, dummy_config):
        """Safe remedy applied → Tvp_base * (1 + tvp_boost_per_unit)."""
        engine = ProbabilityEngine(config=dummy_config)
        # Calculate without remedy
        prob_base, brk_base = engine.calculate_event_probability(
            planet="Sun", age=30, natal_score=0.0, annual_magnitude=1.0
        )
        
        # Calculate with safe remedy
        applied = [{"planet": "Sun", "age": 30, "target_house": 2, "is_safe": True}]
        prob_remedy, brk_rem = engine.calculate_event_probability(
            planet="Sun", age=30, natal_score=0.0, annual_magnitude=1.0, applied_remedies=applied
        )
        
        # tvp_mod should be exactly 1.25x larger
        assert brk_rem["tvp_mod"] == pytest.approx(brk_base["tvp_mod"] * 1.25)
        # Final prob should logically increase
        assert prob_remedy > prob_base

    def test_tvp_unchanged_when_no_remedy_applied(self, dummy_config):
        """No remedies → Tvp unchanged."""
        engine = ProbabilityEngine(config=dummy_config)
        prob1, brk1 = engine.calculate_event_probability(
            planet="Mars", age=25, natal_score=0.0, annual_magnitude=5.0
        )
        prob2, brk2 = engine.calculate_event_probability(
            planet="Mars", age=25, natal_score=0.0, annual_magnitude=5.0, applied_remedies=[]
        )
        
        assert prob1 == pytest.approx(prob2)
        assert brk1["tvp_mod"] == pytest.approx(brk2["tvp_mod"])

    def test_tvp_boost_uses_config_tvp_boost_per_unit(self, dummy_config):
        """Engine reads remedy.tvp_boost_per_unit from config."""
        engine = ProbabilityEngine(config=dummy_config)
        applied = [{"planet": "Moon", "age": 40, "target_house": 1, "is_safe": True}]
        _, brk_rem = engine.calculate_event_probability(
            planet="Moon", age=40, natal_score=0.0, annual_magnitude=5.0, applied_remedies=applied
        )
        
        # Default outside active range (Moon at 40) is typically tvp_penalty or 1.0 depending on rules.
        # Let's test by comparing tvp_mod.
        _, brk_base = engine.calculate_event_probability(
            planet="Moon", age=40, natal_score=0.0, annual_magnitude=5.0
        )
        assert brk_rem["tvp_mod"] == pytest.approx(brk_base["tvp_mod"] * 1.25)

    def test_tvp_boost_unsafe_remedy_no_extra_boost(self, dummy_config):
        """Unsafe remedy (is_safe=False) → no Tvp boost."""
        engine = ProbabilityEngine(config=dummy_config)
        applied_unsafe = [{"planet": "Venus", "age": 28, "target_house": 1, "is_safe": False}]
        
        prob_unsafe, brk_unsafe = engine.calculate_event_probability(
            planet="Venus", age=28, natal_score=0.0, annual_magnitude=5.0, applied_remedies=applied_unsafe
        )
        
        prob_base, brk_base = engine.calculate_event_probability(
            planet="Venus", age=28, natal_score=0.0, annual_magnitude=5.0
        )
        
        # Since it's unsafe, tvp_mod should be identical
        assert brk_unsafe["tvp_mod"] == pytest.approx(brk_base["tvp_mod"])
        assert prob_unsafe == pytest.approx(prob_base)
