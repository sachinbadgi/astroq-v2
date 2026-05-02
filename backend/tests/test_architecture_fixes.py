"""
TDD tests for architecture review fixes (b91e2872).

One class per fix. All tests exercise public interfaces only.
"""
import copy
import pytest

# ---------------------------------------------------------------------------
# C-1: VarshphalTimingEngine must NOT mutate shared rule dicts across calls
# ---------------------------------------------------------------------------

class MockStateC1:
    is_awake = True
    is_startled = False
    sustenance_factor = 1.0

class MockContextC1:
    def __init__(self, natal_h, annual_h, age=30):
        self._natal = natal_h
        self._annual = annual_h
        self.age = age
        self.ledger = None

    def get_natal_house(self, p): return self._natal.get(p)
    def get_house(self, p): return self._annual.get(p)
    def is_awake(self, p): return True
    def check_maturity_age(self, p): return True
    def has_180_degree_block(self, p): return False
    def get_complex_state(self, p): return MockStateC1()


class TestC1_RuleImmutability:
    """C-1: evaluate_varshphal_triggers must not mutate VARSHPHAL_TIMING_TRIGGERS."""

    def _make_finance_context(self):
        # Saturn natal H6 → annual Mars H4 triggers a finance rule
        return MockContextC1(
            natal_h={"Saturn": 6},
            annual_h={"Mars": 4},
        )

    def test_rule_desc_unchanged_after_call(self):
        from astroq.lk_prediction.varshphal_timing_engine import VarshphalTimingEngine
        from astroq.lk_prediction.lk_pattern_constants import VARSHPHAL_TIMING_TRIGGERS

        engine = VarshphalTimingEngine()
        # Record original descs for finance domain
        original_descs = [
            rule.get("desc", "")
            for rule in VARSHPHAL_TIMING_TRIGGERS.get("finance", [])
        ]

        ctx = self._make_finance_context()
        engine.evaluate_varshphal_triggers(ctx, "finance")

        # After call, all descs must be identical to original
        post_descs = [
            rule.get("desc", "")
            for rule in VARSHPHAL_TIMING_TRIGGERS.get("finance", [])
        ]
        assert original_descs == post_descs, (
            "evaluate_varshphal_triggers mutated shared VARSHPHAL_TIMING_TRIGGERS. "
            "Use dict(rule) copy before annotating."
        )

    def test_is_blocked_not_written_to_shared_dict(self):
        from astroq.lk_prediction.varshphal_timing_engine import VarshphalTimingEngine
        from astroq.lk_prediction.lk_pattern_constants import VARSHPHAL_TIMING_TRIGGERS

        engine = VarshphalTimingEngine()
        ctx = self._make_finance_context()
        engine.evaluate_varshphal_triggers(ctx, "finance")

        # The shared dicts must not have is_blocked, is_premature, sustenance_factor
        for rule in VARSHPHAL_TIMING_TRIGGERS.get("finance", []):
            assert "is_blocked" not in rule, (
                f"Rule '{rule.get('desc','?')}' was mutated: 'is_blocked' key written into shared dict"
            )

    def test_repeated_calls_produce_same_desc(self):
        """Two calls with identical inputs must return identical desc strings."""
        from astroq.lk_prediction.varshphal_timing_engine import VarshphalTimingEngine

        engine = VarshphalTimingEngine()
        ctx1 = self._make_finance_context()
        ctx2 = self._make_finance_context()

        triggers1 = engine.evaluate_varshphal_triggers(ctx1, "finance")
        triggers2 = engine.evaluate_varshphal_triggers(ctx2, "finance")

        descs1 = [t["desc"] for t in triggers1]
        descs2 = [t["desc"] for t in triggers2]
        assert descs1 == descs2, (
            "Repeated identical calls return different descs — shared dict mutation."
        )


# ---------------------------------------------------------------------------
# C-2: StateLedger.get_planet_state must not KeyError on Masnui names
# ---------------------------------------------------------------------------

class TestC2_StateLedgerMasnuiSafety:
    """C-2: StateLedger.get_planet_state must handle 'Masnui Venus' gracefully."""

    def test_masnui_prefix_is_stripped(self):
        from astroq.lk_prediction.state_ledger import StateLedger
        ledger = StateLedger()
        # Should not raise
        state = ledger.get_planet_state("Masnui Venus")
        assert state is not None

    def test_masnui_returns_same_base_state(self):
        from astroq.lk_prediction.state_ledger import StateLedger
        ledger = StateLedger()
        base_state = ledger.get_planet_state("Venus")
        masnui_state = ledger.get_planet_state("Masnui Venus")
        # Both must refer to the same underlying PlanetaryState object
        assert base_state is masnui_state

    def test_unknown_planet_returns_default(self):
        from astroq.lk_prediction.state_ledger import StateLedger
        from astroq.lk_prediction.state_ledger import PlanetaryState
        ledger = StateLedger()
        state = ledger.get_planet_state("UnknownPlanet")
        assert isinstance(state, PlanetaryState)


# ---------------------------------------------------------------------------
# C-3: LifecycleEngine must log/warn on VARSHPHAL_YEAR_MATRIX miss
# ---------------------------------------------------------------------------

class TestC3_LifecycleMatrixGap:
    """C-3: Gaps in VARSHPHAL_YEAR_MATRIX must not silently produce wrong positions."""

    def test_matrix_gap_triggers_warning(self, caplog):
        """When natal_h has no entry in the year matrix, a warning must be logged."""
        import logging
        from astroq.lk_prediction.lifecycle_engine import LifecycleEngine

        engine = LifecycleEngine()

        # House 13 is invalid — guaranteed to be absent from year matrix
        # Pass it as a natal position to force a miss
        invalid_natal = {
            "Sun": 13,   # invalid house — not in any year matrix row
            "Moon": 1, "Mars": 2, "Mercury": 3, "Jupiter": 4,
            "Venus": 5, "Saturn": 6, "Rahu": 7, "Ketu": 8,
        }

        with caplog.at_level(logging.WARNING, logger="astroq.lk_prediction.lifecycle_engine"):
            engine.run_75yr_analysis(invalid_natal)

        warning_messages = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        assert any("matrix" in m.lower() or "missing" in m.lower() or "gap" in m.lower()
                   for m in warning_messages), (
            "LifecycleEngine must emit a warning when VARSHPHAL_YEAR_MATRIX has a gap. "
            f"Got warnings: {warning_messages}"
        )


# ---------------------------------------------------------------------------
# M-3: GravityScorer must NOT double-apply recoil
# ---------------------------------------------------------------------------

class MockStateM3:
    modifier = "None"

class TestM3_GravityNoDoubleRecoil:
    """M-3: gravity_score must not apply the Startled multiplier twice."""

    def test_startled_modifier_not_doubled(self):
        """
        When a planet is Startled, GravityScorer's 2× multiplier should NOT
        compound with the recoil already baked into hit.magnitude by calculate_rule_magnitude.

        We verify by checking: gravity_score == |magnitude| * domain_weight (no extra 2×).
        If double-applied, gravity_score would be 2× too large.
        """
        from astroq.lk_prediction.contextual_assembler import GravityScorer, DOMAIN_WEIGHTS
        from astroq.lk_prediction.data_contracts import RuleHit

        hit = RuleHit(
            rule_id="test_rule",
            domain="Marriage",
            description="test",
            verdict="malefic",
            magnitude=-1.0,   # already post-recoil
            scoring_type="penalty",
            primary_target_planets=["Venus"],
        )

        # A state with Startled modifier
        class StartledState:
            modifier = "Startled Malefic"

        score = GravityScorer.calculate_score(hit, StartledState())
        domain_weight = DOMAIN_WEIGHTS.get("Marriage", 1.0)

        # If recoil is NOT doubled, score == 1.0 * 2.0 * 1.4 = 2.8
        # If recoil IS doubled (bug), score would be even larger (e.g. 5.6)
        # The fix is: GravityScorer should NOT apply the 2× state_multiplier
        # because calculate_rule_magnitude already did it.
        expected = abs(hit.magnitude) * domain_weight   # 1.0 * 1.4 = 1.4
        assert abs(score - expected) < 0.01, (
            f"GravityScorer applied state_multiplier on top of already-scaled magnitude. "
            f"Expected {expected:.2f}, got {score:.2f}. "
            "Remove state_multiplier from GravityScorer — recoil is handled by calculate_rule_magnitude."
        )


# ---------------------------------------------------------------------------
# M-5: Birth chart must receive a clean StateLedger, not the live mutable one
# ---------------------------------------------------------------------------

class TestM5_BirthChartCleanLedger:
    """M-5: pipeline.generate_predictions for Birth chart must not share the lifecycle ledger."""

    def _make_minimal_chart(self, chart_type="Birth"):
        return {
            "chart_type": chart_type,
            "chart_period": 0,
            "planets_in_houses": {
                "Sun": {"house": 1}, "Moon": {"house": 2}, "Mars": {"house": 3},
                "Mercury": {"house": 4}, "Jupiter": {"house": 5},
                "Venus": {"house": 6}, "Saturn": {"house": 7},
                "Rahu": {"house": 8}, "Ketu": {"house": 9},
            },
            "house_status": {str(i): "Occupied" for i in range(1, 10)},
        }

    def test_birth_chart_ledger_is_independent(self):
        """
        After calling generate_predictions for a Birth chart,
        mutating the lifecycle ledger must NOT affect a second Birth chart call.
        """
        from astroq.lk_prediction.pipeline import LKPredictionPipeline
        from astroq.lk_prediction.config import ModelConfig
        import os

        db_path = os.path.join(
            os.path.dirname(__file__), "..", "astroq", "data", "rules.db"
        )
        if not os.path.exists(db_path):
            pytest.skip("rules.db not present — skipping pipeline integration test")

        config_path = os.path.join(
            os.path.dirname(__file__), "..", "astroq", "data", "config.ini"
        )
        cfg = ModelConfig(db_path, config_path)
        pipe = LKPredictionPipeline(cfg)

        natal = self._make_minimal_chart("Birth")
        pipe.load_natal_baseline(natal)

        # First call
        pipe.generate_predictions(natal)

        # Corrupt the lifecycle ledger
        pipe.lifecycle.ledger.apply_trauma("Sun", 999.0)

        # Second call — if Birth chart uses the live ledger, Sun's state will be Burst
        # and magnitude-based predictions will differ. With a clean ledger it's identical.
        # We just verify no exception and that Sun's trauma doesn't bleed in:
        from astroq.lk_prediction.state_ledger import StateLedger
        # Capture what context is built with
        ledger_used = []
        original_generate = pipe.generate_predictions

        def patched_generate(chart, **kwargs):
            from astroq.lk_prediction.astrological_context import UnifiedAstrologicalContext
            orig_init = UnifiedAstrologicalContext.__init__
            def _capture(self_ctx, enriched, natal_chart=None, ledger=None, config=None):
                ledger_used.append(ledger)
                orig_init(self_ctx, enriched, natal_chart, ledger, config)
            UnifiedAstrologicalContext.__init__ = _capture
            result = original_generate(chart, **kwargs)
            UnifiedAstrologicalContext.__init__ = orig_init
            return result

        pipe.generate_predictions = patched_generate
        pipe.generate_predictions(natal)

        assert ledger_used, "Context was never constructed — test setup broken"
        captured = ledger_used[0]
        # Birth chart must NOT get the corrupted ledger (trauma_points on Sun should be 0)
        if captured is not None:
            sun_state = captured.get_planet_state("Sun")
            assert sun_state.trauma_points < 999.0, (
                "Birth chart received the live mutable lifecycle ledger. "
                "Pipeline must pass a fresh StateLedger() for Birth chart calls."
            )
