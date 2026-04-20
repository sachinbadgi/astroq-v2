"""
Remedy Logic Precision Tests.

Validates the Karmic Remedy Engine (remedy_engine.py):
1. Safe House Contract (Birth x Annual intersection).
2. Goswami Priority Scoring (Unblock H8, Companion Pairs, Doubtful status).
3. Kendra Priority tie-breaking.
4. Lifetime Projection and Residuals.
"""

import pytest
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.remedy_engine import RemedyEngine

class MockResolver:
    def get_planet_items(self, planet, house):
        return [f"{planet}_{house}_item"]

@pytest.fixture
def remedy_suite(tmp_path):
    # Setup paths
    db_path = tmp_path / "rules_remedy.db"
    defaults_path = tmp_path / "defaults_remedy.json"
    
    import json
    with open(defaults_path, "w") as f:
        json.dump({
            "remedy.goswami_h9_weight": 30,
            "remedy.goswami_h2_weight": 20,
            "remedy.goswami_h4_weight": 10,
            "remedy.goswami_unblock_weight": 50,
            "remedy.goswami_pair_weight": 40,
            "remedy.goswami_doubtful_weight": 20,
            "remedy.shifting_boost": 2.5,
            "remedy.residual_impact_factor": 0.05,
        }, f)
        
    cfg = ModelConfig(db_path=str(db_path), defaults_path=str(defaults_path))
    return cfg, RemedyEngine(cfg, MockResolver())

class TestRemedyPrecision:

    def test_safe_house_contract_intersection(self, remedy_suite):
        """A house must be safe in BOTH Birth and Annual charts to be a match."""
        cfg, engine = remedy_suite
        # Jupiter targets: [2, 4, 5, 9, 11, 12]
        
        # Birth: Venus (Enemy) in H2. House 2 is blocked in Birth.
        # Annual: Mercury (Enemy) in H5. House 5 is blocked in Annual.
        birth_chart = {
            "planets_in_houses": {
                "Venus": {"house": 2},
                "Jupiter": {"house": 1}
            }
        }
        annual_chart = {
            "planets_in_houses": {
                "Mercury": {"house": 5},
                "Jupiter": {"house": 8}
            }
        }
        
        options = engine.get_year_shifting_options(birth_chart, annual_chart, age=30)
        jup_res = options["Jupiter"]
        
        # Houses [2, 5] should be in conflicts, not in safe_matches
        safe_houses = [opt.house for opt in jup_res.safe_matches]
        assert 2 not in safe_houses
        assert 5 not in safe_houses
        # 4, 9, 11, 12 should be safe
        assert 9 in safe_houses
        assert 4 in safe_houses

    def test_goswami_unblock_rule_p148(self, remedy_suite):
        """Planet in H8 gets +50 unblock score for H2 and H4."""
        cfg, engine = remedy_suite
        # Jupiter in H8 (Annual)
        birth_chart = {"planets_in_houses": {"Jupiter": {"house": 1}}}
        annual_chart = {"planets_in_houses": {"Jupiter": {"house": 8}}}
        
        options = engine.get_year_shifting_options(birth_chart, annual_chart, age=30)
        jup_res = options["Jupiter"]
        
        h2_opt = next(o for o in jup_res.safe_matches if o.house == 2)
        h4_opt = next(o for o in jup_res.safe_matches if o.house == 4)
        h9_opt = next(o for o in jup_res.safe_matches if o.house == 9)
        
        # H2 score = 10 (base) + 20 (H2 weight) + 50 (Unblock) = 80
        assert h2_opt.score == 80
        # H4 score = 10 (base) + 10 (H4 weight) + 50 (Unblock) = 70
        assert h4_opt.score == 70
        # H9 score = 10 (base) + 30 (H9 weight) = 40
        assert h9_opt.score == 40

    def test_goswami_companion_pair_rule(self, remedy_suite):
        """Moon + Jupiter in same house triggers +40 pair weight for preferred targets."""
        cfg, engine = remedy_suite
        # Moon and Jupiter together in House 1 (Annual)
        # Pair targets for (Moon, Jup) = [2, 4, 10]
        birth_chart = {"planets_in_houses": {"Moon": {"house": 1}, "Jupiter": {"house": 1}}}
        annual_chart = {"planets_in_houses": {"Moon": {"house": 1}, "Jupiter": {"house": 1}}}
        
        options = engine.get_year_shifting_options(birth_chart, annual_chart, age=30)
        jup_res = options["Jupiter"]
        
        # Jupiter normally gets base 10 + H2 weight 20 = 30.
        # Now adds +40 for being with Moon and targeting H2.
        h2_opt = next(o for o in jup_res.safe_matches if o.house == 2)
        assert h2_opt.score == 10 + 20 + 40 # 70

    def test_kendra_priority_tiebreak(self, remedy_suite):
        """Tie-breaking hints by Kendra Priority (1 > 10 > 7 > 4)."""
        cfg, engine = remedy_suite
        # Mock options where H1 and H10 have same score.
        # Let's say Sun (H1, H5 safe). Base=10.
        # We'll artificially inject scores by choosing a planet with equal weights.
        
        # Move all other planets away to avoid accidental pair triggers
        from astroq.lk_prediction.remedy_engine import STANDARD_PLANETS
        pih = {p: {"house": i+10} for i, p in enumerate(STANDARD_PLANETS)}
        pih["Sun"] = {"house": 6}
        chart = {"planets_in_houses": pih}
        
        # Use volatile override to force High rank AND disable house weights to force tie
        cfg.set_volatile_overrides({
            "remedy.high_score_threshold": 5,
            "remedy.goswami_h9_weight": 0,
            "remedy.goswami_h2_weight": 0,
            "remedy.goswami_h4_weight": 0
        })
        
        options = engine.get_year_shifting_options(chart, chart, age=30)
        
        # Hints should include House 1 before House 5 if they have same score.
        hints = engine.generate_remedy_hints(options)
        
        # Filter for Sun hints
        sun_hints = [h for h in hints if "Sun" in h]
        
        assert len(sun_hints) > 0
        # House 1 should be the FIRST Sun hint because scores are equal (10)
        # and Kendra (1) beats non-Kendra (5).
        assert "House 1" in sun_hints[0]

    def test_lifetime_residual_impact(self, remedy_suite):
        """Residual impact (0.05) carry-forward across ages."""
        cfg, engine = remedy_suite
        birth_chart = {"planets_in_houses": {"Sun": {"house": 1}}}
        # 3 annual charts (Age 1, 2, 3)
        annual_charts = {
            1: {"planets_in_houses": {"Sun": {"house": 1, "strength_total": 10.0}}},
            2: {"planets_in_houses": {"Sun": {"house": 1, "strength_total": 10.0}}},
            3: {"planets_in_houses": {"Sun": {"house": 1, "strength_total": 10.0}}},
        }
        # Apply remedy at Age 1 only. Boost=2.5.
        applied = [{"planet": "Sun", "age": 1, "is_safe": True}]
        
        proj = engine.simulate_lifetime_strength(birth_chart, annual_charts, applied)
        sun_traj = proj.planets["Sun"]["remedy"]
        
        # Age 1: 10.0 (base) + 2.5 (boost) + (2.5 * 0.05) (residual) = 12.625.
        # Wait, the code says:
        # boost = applied_boost
        # residual += boost * residual_factor
        # total = base + boost + residual
        # So Age 1: 10.0 + 2.5 + 0.125 = 12.625.
        assert sun_traj[0] == 12.625
        
        # Age 2: 10.0 (base) + 0.0 (boost) + 0.125 (residual) = 10.125.
        assert sun_traj[1] == 10.125
        
        # Age 3: 10.0 (base) + 0.125 (residual) = 10.125.
        assert sun_traj[2] == 10.125
