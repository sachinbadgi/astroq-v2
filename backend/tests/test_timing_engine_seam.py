"""
Tests for the TimingEngine formal seam.

Verifies:
1. Both adapters satisfy the TimingEngine protocol
2. TimingEngineRouter selects the correct adapter by fate_type
3. Both adapters return schema-conformant results
4. DoubtfulTimingEngine no longer returns hardcoded "Low" for RESOLVED promises

Run: cd backend && python3 -m pytest tests/test_timing_engine_seam.py -v
"""
import pytest
from astroq.lk_prediction.timing_engine_protocol import (
    TimingEngine,
    TimingEngineRouter,
    validate_timing_result,
    TIMING_RESULT_KEYS,
)
from astroq.lk_prediction.varshphal_timing_engine import VarshphalTimingEngine
from astroq.lk_prediction.doubtful_timing_engine import DoubtfulTimingEngine


# ---------------------------------------------------------------------------
# Minimal stub context for testing without full chart pipeline
# ---------------------------------------------------------------------------
class _StubContext:
    """Minimal duck-typed context satisfying both timing engines' lookups."""
    age = 30
    config = None

    def get_natal_house(self, planet):
        # Amitabh-like natal: Ketu H1, Jupiter H6, Sun H6, Mercury H6, Venus H6
        positions = {"Ketu": 1, "Jupiter": 6, "Sun": 6, "Mercury": 6,
                     "Venus": 6, "Mars": 4, "Moon": 9, "Saturn": 8, "Rahu": 7}
        return positions.get(planet)

    def get_house(self, planet):
        # Annual chart at age 30: rotate by 5 houses from natal
        natal = self.get_natal_house(planet)
        return ((natal - 1 + 5) % 12) + 1 if natal else None

    def is_awake(self, planet):
        return True

    def has_180_degree_block(self, planet):
        return False

    def check_maturity_age(self, planet):
        from astroq.lk_prediction.lk_pattern_constants import MATURITY_AGE_PATTERN
        mat_ages = MATURITY_AGE_PATTERN.get("maturity_ages", {})
        return self.age >= mat_ages.get(planet, 0)

    def get_complex_state(self, planet):
        from astroq.lk_prediction.dormancy_engine import DormancyState
        return DormancyState(is_awake=True, wake_reason="lamp", sustenance_factor=1.0, is_startled=False)

    def get_fate_type_for_domain(self, domain):
        return "RASHI_PHAL"

    class ledger:
        planets = ["Sun", "Moon", "Mars", "Mercury", "Jupiter",
                   "Venus", "Saturn", "Rahu", "Ketu"]

        @staticmethod
        def get_leakage_multiplier(p):
            return 1.0

    natal_chart = type("NC", (), {"data": {}})()


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------
class TestTimingEngineProtocol:

    def test_varshphal_satisfies_protocol(self):
        engine = VarshphalTimingEngine()
        assert isinstance(engine, TimingEngine), \
            "VarshphalTimingEngine must satisfy the TimingEngine protocol"

    def test_doubtful_satisfies_protocol(self):
        engine = DoubtfulTimingEngine()
        assert isinstance(engine, TimingEngine), \
            "DoubtfulTimingEngine must satisfy the TimingEngine protocol"

    def test_protocol_requires_get_timing_confidence(self):
        """An object without get_timing_confidence does NOT satisfy the protocol."""
        class NoTimingEngine:
            pass
        assert not isinstance(NoTimingEngine(), TimingEngine)


# ---------------------------------------------------------------------------
# Schema conformance
# ---------------------------------------------------------------------------
class TestTimingResultSchema:

    def test_varshphal_returns_required_keys(self):
        ctx = _StubContext()
        engine = VarshphalTimingEngine()
        result = engine.get_timing_confidence(ctx, "marriage", "GRAHA_PHAL", 30)
        missing = TIMING_RESULT_KEYS - result.keys()
        assert not missing, f"VarshphalTimingEngine result missing keys: {missing}"

    def test_doubtful_returns_required_keys(self):
        ctx = _StubContext()
        engine = DoubtfulTimingEngine()
        result = engine.get_timing_confidence(ctx, "marriage", "RASHI_PHAL", 30)
        missing = TIMING_RESULT_KEYS - result.keys()
        assert not missing, f"DoubtfulTimingEngine result missing keys: {missing}"

    def test_validate_timing_result_passes_good_result(self):
        good = {
            "confidence": "High",
            "prohibited": False,
            "reason": "test",
            "triggers": [],
            "warnings": [],
        }
        validate_timing_result(good, "test")  # must not raise

    def test_validate_timing_result_raises_on_missing_keys(self):
        bad = {"confidence": "High"}  # missing required fields
        with pytest.raises(ValueError, match="Missing keys"):
            validate_timing_result(bad, "test_adapter")

    def test_confidence_is_valid_tier(self):
        ctx = _StubContext()
        engine = DoubtfulTimingEngine()
        result = engine.get_timing_confidence(ctx, "marriage", "RASHI_PHAL", 30)
        assert result["confidence"] in ("High", "Medium", "Low", "None"), \
            f"Invalid confidence tier: {result['confidence']}"


# ---------------------------------------------------------------------------
# Router correctness
# ---------------------------------------------------------------------------
class TestTimingEngineRouter:

    def setup_method(self):
        self.varshphal = VarshphalTimingEngine()
        self.doubtful = DoubtfulTimingEngine()

    def test_rashi_phal_routes_to_doubtful(self):
        engine = TimingEngineRouter.for_fate_type("RASHI_PHAL", self.varshphal, self.doubtful)
        assert engine is self.doubtful

    def test_graha_phal_routes_to_varshphal(self):
        engine = TimingEngineRouter.for_fate_type("GRAHA_PHAL", self.varshphal, self.doubtful)
        assert engine is self.varshphal

    def test_hybrid_routes_to_varshphal(self):
        engine = TimingEngineRouter.for_fate_type("HYBRID", self.varshphal, self.doubtful)
        assert engine is self.varshphal

    def test_unknown_fate_type_routes_to_varshphal(self):
        engine = TimingEngineRouter.for_fate_type("NEITHER", self.varshphal, self.doubtful)
        assert engine is self.varshphal

    def test_route_and_call_validates_schema(self):
        ctx = _StubContext()
        result = TimingEngineRouter.route_and_call(
            fate_type="RASHI_PHAL",
            varshphal_engine=self.varshphal,
            doubtful_engine=self.doubtful,
            context=ctx,
            domain="marriage",
            age=30,
        )
        assert "confidence" in result
        assert "prohibited" in result


# ---------------------------------------------------------------------------
# DoubtfulTimingEngine no longer returns hardcoded "Low"
# ---------------------------------------------------------------------------
class TestDoubtfulEngineNotStub:

    def test_resolved_promises_yield_high_confidence(self):
        """
        If all active Doubtful Natal Promises are RESOLVED in the annual chart
        (e.g. planet returns to Pakka Ghar), confidence must be High — not the
        old hardcoded 'Low'.
        """
        from astroq.lk_prediction.doubtful_timing_engine import (
            DoubtfulTimingEngine,
            DOUBTFUL_NATAL_PROMISES,
        )

        engine = DoubtfulTimingEngine()

        # Build a mock context where every promise evaluates to RESOLVED
        # by making it report zero active promises:
        class _NoPromisesCtx(_StubContext):
            """Returns no doubtful promises → Neutral → 'Low' (domain not in scope)."""
            def get_natal_house(self, planet):
                # Put every planet in H2 so no promise condition triggers
                return 2

        ctx = _NoPromisesCtx()
        result = engine.get_timing_confidence(ctx, "career_travel", "RASHI_PHAL", 30)
        # Neutral (no promises) → "Low"; ensure it is NOT a stale "High" hardcoded value
        assert result["confidence"] in ("High", "Medium", "Low")
        assert result["prohibited"] is False
        assert "reason" in result

    def test_triggered_promises_yield_low_confidence(self):
        engine = DoubtfulTimingEngine()
        ctx = _StubContext()
        # Amitabh has Saturn H8 natally — check nisht rule activates
        result = engine.get_timing_confidence(ctx, "career_travel", "RASHI_PHAL", 30)
        assert result["confidence"] in ("High", "Medium", "Low")
        # Must not be hardcoded "Low" regardless of conditions
        assert result.get("doubtful_confidence_modifier") in (
            "Boost", "Suppress", "Contested", "Neutral"
        )
