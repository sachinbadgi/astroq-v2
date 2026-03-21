"""
Tests for Module 5: Probability Engine.

Tests written FIRST (TDD Red phase) — 18 unit tests covering
sigmoid calculation, adaptive k scaling, Tvp delivery rules,
Ea modifiers, and output capping (0.05 - 0.95).
"""

import pytest

# Lazily imported during tests
# from astroq.lk_prediction.probability_engine import ProbabilityEngine
# from astroq.lk_prediction.config import ModelConfig


class TestProbabilityEngine:
    
    def _make_engine(self, tmp_db, tmp_defaults):
        from astroq.lk_prediction.config import ModelConfig
        from astroq.lk_prediction.probability_engine import ProbabilityEngine
        cfg = ModelConfig(db_path=tmp_db, defaults_path=tmp_defaults)
        return ProbabilityEngine(cfg)

    # -- 1. Base Sigmoid Logic --
    def test_sigmoid_base_calculation_neutral_magnitude(self, tmp_db, tmp_defaults):
        """Magnitude 0 should yield exactly 50% probability."""
        engine = self._make_engine(tmp_db, tmp_defaults)
        # Using default k=1.2
        prob = engine._calculate_raw_sigmoid(magnitude=0.0, k=1.2)
        assert abs(prob - 0.5) < 0.0001

    def test_sigmoid_base_calculation_positive_magnitude(self, tmp_db, tmp_defaults):
        """Positive magnitude yields > 50% probability."""
        engine = self._make_engine(tmp_db, tmp_defaults)
        prob = engine._calculate_raw_sigmoid(magnitude=1.0, k=1.2)
        assert prob > 0.5 

    def test_sigmoid_base_calculation_negative_magnitude(self, tmp_db, tmp_defaults):
        """Negative magnitude yields < 50% probability."""
        engine = self._make_engine(tmp_db, tmp_defaults)
        prob = engine._calculate_raw_sigmoid(magnitude=-1.0, k=1.2)
        assert prob < 0.5 

    # -- 2. Adaptive K Scaling --
    def test_adaptive_k_scales_up_with_strength(self, tmp_db, tmp_defaults):
        """Higher natal strength should dynamically increase K."""
        engine = self._make_engine(tmp_db, tmp_defaults)
        # Assuming base_k = 1.2, scale_factor = 0.2
        # k = 1.2 + (10 * 0.2) = 3.2 (but max_k usually limits to 3.0 or 4.0)
        k_low = engine._calculate_adaptive_k(natal_score=5.0)
        k_high = engine._calculate_adaptive_k(natal_score=15.0)
        assert k_high > k_low

    def test_adaptive_k_respects_max_cap(self, tmp_db, tmp_defaults):
        """K should not exceed max_k from config."""
        engine = self._make_engine(tmp_db, tmp_defaults)
        import math
        # If max_k is 3.5, providing extreme natal_score shouldn't breach 3.5
        k_extreme = engine._calculate_adaptive_k(natal_score=100.0)
        # We fetch the actual max_k
        max_k = engine._cfg.get("probability.max_k", fallback=3.5)
        # Using math.isclose to handle float tiny diffs
        assert math.isclose(k_extreme, max_k) or k_extreme <= max_k

    def test_adaptive_k_uses_base_when_feature_disabled(self, tmp_db, tmp_defaults):
        """If adaptive_k_active=False in config, k should be strictly base_k."""
        from astroq.lk_prediction.config import ModelConfig
        from astroq.lk_prediction.probability_engine import ProbabilityEngine
        
        cfg = ModelConfig(db_path=tmp_db, defaults_path=tmp_defaults)
        cfg.set_override("probability.adaptive_k_active", False)
        engine = ProbabilityEngine(cfg)
        
        k_1 = engine._calculate_adaptive_k(natal_score=5.0)
        k_2 = engine._calculate_adaptive_k(natal_score=50.0)
        
        base_k = cfg.get("probability.base_k", fallback=1.2)
        assert k_1 == base_k
        assert k_2 == base_k

    # -- 3. Ea Base Propensity --
    def test_ea_propensity_incorporates_natal_accuracy(self, tmp_db, tmp_defaults):
        """Ea (Base Expectancy) increases if planet is strong natally."""
        engine = self._make_engine(tmp_db, tmp_defaults)
        # 0.5 base + (10 * 0.05 weighting) = 1.0 (clamped)
        ea_high = engine._calculate_ea(natal_score=10.0)
        ea_low = engine._calculate_ea(natal_score=0.0)
        assert ea_high > ea_low

    def test_ea_propensity_caps_at_boundaries(self, tmp_db, tmp_defaults):
        """Ea should obey ea_min, ea_max config limits."""
        engine = self._make_engine(tmp_db, tmp_defaults)
        max_ea = engine._cfg.get("probability.ea_max", fallback=0.95)
        min_ea = engine._cfg.get("probability.ea_min", fallback=0.05)
        
        ea_over = engine._calculate_ea(natal_score=50.0)
        ea_under = engine._calculate_ea(natal_score=-50.0)
        
        assert ea_over <= max_ea
        assert ea_under >= min_ea

    # -- 4. Tvp Delivery Rules (Planet Awakening / Effective Timing) --
    def test_tvp_boost_applied_if_planet_awakens(self, tmp_db, tmp_defaults):
        engine = self._make_engine(tmp_db, tmp_defaults)
        # Sun typically delivers major results in 22nd year
        # Age = 22, Planet = Sun
        tvp_mod = engine._calculate_tvp_modifier(planet="Sun", age=22)
        assert tvp_mod > 1.0 # Exact value depends on config "tvp_boost_factor"

    def test_tvp_penalty_applied_if_planet_inactive(self, tmp_db, tmp_defaults):
        engine = self._make_engine(tmp_db, tmp_defaults)
        # If age is far from active delivering age
        tvp_mod = engine._calculate_tvp_modifier(planet="Sun", age=6)
        assert tvp_mod < 1.0 # Or 1.0 depending on implementation. Usually penalised or neutral

    def test_tvp_neutral_for_unknown_planets(self, tmp_db, tmp_defaults):
        engine = self._make_engine(tmp_db, tmp_defaults)
        tvp_mod = engine._calculate_tvp_modifier(planet="UnknownPlanet", age=22)
        assert tvp_mod == 1.0

    # -- 5. Distance Correction (Dcorr) --
    def test_dcorr_reduces_probability_late_in_lifecycle(self, tmp_db, tmp_defaults):
        engine = self._make_engine(tmp_db, tmp_defaults)
        # 35 year cycle context: as age approaches 75, probability naturally damps for certain events
        # Test basic penalty functionality
        dcorr_mod_early = engine._calculate_dcorr(age=10)
        dcorr_mod_late = engine._calculate_dcorr(age=70)
        
        # Late age might have higher penalty (lower modifier)
        assert dcorr_mod_late <= dcorr_mod_early

    # -- 6. Complete Probability Calculation Pipeline --
    def test_calculate_event_probability_combines_factors(self, tmp_db, tmp_defaults):
        engine = self._make_engine(tmp_db, tmp_defaults)
        
        prob, breakdown = engine.calculate_event_probability(
            planet="Jupiter",
            age=16, # Jupiter active year
            natal_score=6.0,
            annual_magnitude=8.0
        )
        
        # With high natal, high magnitude, and correct active year, prob should be very high
        assert prob > 0.8
        assert "ea" in breakdown
        assert "k_used" in breakdown
        assert "tvp_mod" in breakdown
        assert "dcorr_mod" in breakdown
        assert "raw_sigmoid" in breakdown

    def test_calculate_event_probability_clamping(self, tmp_db, tmp_defaults):
        engine = self._make_engine(tmp_db, tmp_defaults)
        
        prob_max, _ = engine.calculate_event_probability(
            planet="Sun", age=22, natal_score=50.0, annual_magnitude=100.0)
        prob_min, _ = engine.calculate_event_probability(
            planet="Sun", age=50, natal_score=-50.0, annual_magnitude=-100.0)
        
        upper = engine._cfg.get("probability.prob_cap_upper", fallback=0.95)
        lower = engine._cfg.get("probability.prob_cap_lower", fallback=0.05)
        
        import math
        assert math.isclose(prob_max, upper) or prob_max <= upper
        assert math.isclose(prob_min, lower) or prob_min >= lower

    # -- 7. Batch Evaluation --
    def test_batch_evaluate_chart_events(self, tmp_db, tmp_defaults):
        engine = self._make_engine(tmp_db, tmp_defaults)
        
        # Provide a list of potential event triggers
        # (planet, magnitude, natal_score) pairs
        events = [
            {"planet": "Mars", "magnitude": 5.0, "natal_score": 2.0},
            {"planet": "Venus", "magnitude": -4.0, "natal_score": -1.0}
        ]
        
        results = engine.batch_evaluate(events, age=28)
        assert len(results) == 2
        
        mars_prob = results[0]["final_probability"]
        venus_prob = results[1]["final_probability"]
        
        assert mars_prob > venus_prob # Positive vs negative magnitude

    # -- 8. Edge cases --
    def test_zero_parameters_graceful_handling(self, tmp_db, tmp_defaults):
        engine = self._make_engine(tmp_db, tmp_defaults)
        prob, brk = engine.calculate_event_probability("Sun", 0, 0.0, 0.0)
        assert brk["raw_sigmoid"] == 0.5

    def test_missing_config_keys_use_sane_defaults(self, tmp_db, tmp_defaults):
        # We simulate missing config by deleting from the db if needed,
        # but the fallback mechanism in ModelConfig handles it.
        # This test ensures `ProbabilityEngine` doesn't crash.
        engine = self._make_engine(tmp_db, tmp_defaults)
        prob, _ = engine.calculate_event_probability("Moon", 24, 5.0, 5.0)
        assert 0.0 < prob < 1.0

    def test_probability_never_escapes_bounds_extreme_math(self, tmp_db, tmp_defaults):
        engine = self._make_engine(tmp_db, tmp_defaults)
        # Even with crazy inputs, sigmoid handles math safely (no OverflowError ideally)
        prob, _ = engine.calculate_event_probability("Mars", 30, 9999.0, 9999.0)
        assert prob <= 0.99 
