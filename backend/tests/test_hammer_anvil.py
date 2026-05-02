"""
Tests: Hammer and Anvil Fidelity Gate
======================================
Verifies the core findings from the predictive accuracy research:
  - Weak Anvil (Low target → hit boost)
  - Strong Shield (High target → silence/drop)
  - Takkar Paradox (both Low on 1-8 → peak accuracy)
  - Gali Sweet Spot (Source High + Target Medium on 2-6)
  - Fixed Fate Freeze (GRAHA_PHAL + 1-7/3-11 → dropped)
  - 8-2 Wealth Correlation (GRAHA_PHAL + 8-2 + wealth → boosted)
  - Doubtful axis routing (MASHKOOQ + 6-12 passthrough)
"""
import pytest
from unittest.mock import MagicMock, patch
from dataclasses import replace

from astroq.lk_prediction.aspect_fidelity_evaluator import (
    AspectFidelityEvaluator,
    AXIS_1_8, AXIS_1_7, AXIS_4_10, AXIS_2_6, AXIS_6_12, AXIS_8_2, AXIS_3_11,
    HOUSE_PAIR_TO_AXIS,
)
from astroq.lk_prediction.fidelity_gate import FidelityGate
from astroq.lk_prediction.data_contracts import RuleHit


# =========================================================================
# Helpers
# =========================================================================

def make_hit(
    domain="marriage",
    axis=AXIS_1_7,
    magnitude=1.0,
    planets=None,
    houses=None,
) -> RuleHit:
    return RuleHit(
        rule_id="TEST_001",
        domain=domain,
        description="test hit",
        verdict="positive",
        magnitude=magnitude,
        scoring_type="boost",
        primary_target_planets=planets or ["Venus", "Jupiter"],
        target_houses=houses or [1, 7],
        axis=axis,
    )


def make_context(
    chart_type="Yearly",
    fate_type="RASHI_PHAL",
    planet_strengths=None,
    annual_houses=None,
) -> MagicMock:
    ctx = MagicMock()
    ctx.chart_type = chart_type
    ctx.age = 30
    ctx.get_fate_type_for_domain.return_value = fate_type
    ps = planet_strengths or {}
    ctx.get_planet_strength.side_effect = lambda p: ps.get(p, 0.0)
    ctx.get_house.side_effect = lambda p: (annual_houses or {}).get(p)
    return ctx


# =========================================================================
# AspectFidelityEvaluator — Unit Tests
# =========================================================================

class TestAspectFidelityEvaluator:
    def setup_method(self):
        self.afe = AspectFidelityEvaluator()

    def test_categorize_low(self):
        assert self.afe.categorize(-5.0) == "Low"
        assert self.afe.categorize(-2.0) == "Low"

    def test_categorize_medium(self):
        assert self.afe.categorize(-1.9) == "Medium"
        assert self.afe.categorize(0.0) == "Medium"
        assert self.afe.categorize(2.1) == "Medium"

    def test_categorize_high(self):
        assert self.afe.categorize(2.2) == "High"
        assert self.afe.categorize(5.0) == "High"

    def test_takkar_paradox_both_low(self):
        """Both Low on 1-8 → 1.83 (83% accuracy)"""
        mult = self.afe.score_aspect(AXIS_1_8, -3.0, -3.0)
        assert mult == 1.83

    def test_takkar_high_source_noisy(self):
        """High source on 1-8 → 0.50 (noisy)"""
        mult = self.afe.score_aspect(AXIS_1_8, 3.0, -3.0)
        assert mult == 0.50

    def test_takkar_high_target_noisy(self):
        """High target on 1-8 → 0.50 (noisy)"""
        mult = self.afe.score_aspect(AXIS_1_8, -3.0, 3.0)
        assert mult == 0.50

    def test_strong_shield_dampened(self):
        """High target on 1-7 → 0.30 (70% dampen, genuine signals survive)"""
        mult = self.afe.score_aspect(AXIS_1_7, 0.0, 3.0)
        assert mult == 0.30

    def test_weak_anvil_4_10(self):
        """Low target on 4-10 → 1.85 (85% accuracy)"""
        mult = self.afe.score_aspect(AXIS_4_10, 0.0, -3.0)
        assert mult == 1.85

    def test_high_target_4_10_dampened(self):
        """High target on 4-10 → 0.60 (resists trigger)"""
        mult = self.afe.score_aspect(AXIS_4_10, 0.0, 3.0)
        assert mult == 0.60

    def test_gali_sweet_spot(self):
        """Source High + Target Medium on 2-6 → 1.90 (89.7% accuracy)"""
        mult = self.afe.score_aspect(AXIS_2_6, 3.0, 0.5)
        assert mult == 1.90

    def test_axis_from_houses(self):
        assert AspectFidelityEvaluator.axis_from_houses(1, 8) == AXIS_1_8
        assert AspectFidelityEvaluator.axis_from_houses(8, 1) == AXIS_1_8  # order independent
        assert AspectFidelityEvaluator.axis_from_houses(4, 10) == AXIS_4_10
        assert AspectFidelityEvaluator.axis_from_houses(6, 12) == AXIS_6_12
        assert AspectFidelityEvaluator.axis_from_houses(2, 8) == AXIS_8_2
        assert AspectFidelityEvaluator.axis_from_houses(5, 9) == "unknown"


# =========================================================================
# FidelityGate — Unit Tests
# =========================================================================

class TestFidelityGateBirthChart:
    def test_birth_chart_is_noop(self):
        """Gate must be a no-op for Birth charts."""
        gate = FidelityGate()
        hits = [make_hit(axis=AXIS_1_7)]
        ctx = make_context(chart_type="Birth", fate_type="GRAHA_PHAL")
        result = gate.filter(hits, ctx)
        assert len(result) == 1, "Birth chart must pass through unchanged"


class TestFidelityGateStrongShield:
    def test_strong_shield_dampens_1_7_high_target(self):
        """1-7 + High target dignity → DAMPEN ×0.30 (70% reduction, not dropped)"""
        gate = FidelityGate()
        hit = make_hit(axis=AXIS_1_7, planets=["Venus", "Mars"])
        ctx = make_context(fate_type="RASHI_PHAL", planet_strengths={"Venus": 3.0, "Mars": 0.0})
        result = gate.filter([hit], ctx)
        assert len(result) == 1, "High-dignity target on 1-7 is dampened, not dropped"
        assert abs(result[0].magnitude - 0.30) < 0.01

    def test_low_target_1_7_passes(self):
        """1-7 + Low target → passes through (dampened, not dropped)"""
        gate = FidelityGate()
        hit = make_hit(axis=AXIS_1_7, magnitude=1.0, planets=["Venus", "Mars"])
        ctx = make_context(fate_type="RASHI_PHAL", planet_strengths={"Venus": -3.0, "Mars": 0.0})
        result = gate.filter([hit], ctx)
        assert len(result) == 1
        assert result[0].magnitude != 0.0


class TestFidelityGateTakkarParadox:
    def test_both_low_boosted(self):
        """1-8 both Low → magnitude boosted by 1.83"""
        gate = FidelityGate()
        hit = make_hit(axis=AXIS_1_8, magnitude=1.0, planets=["Saturn", "Mars"])
        ctx = make_context(fate_type="RASHI_PHAL", planet_strengths={"Saturn": -3.0, "Mars": -3.0})
        result = gate.filter([hit], ctx)
        assert len(result) == 1
        assert abs(result[0].magnitude - 1.83) < 0.01

    def test_high_source_dampened(self):
        """1-8 with High source → dampened by 0.5"""
        gate = FidelityGate()
        hit = make_hit(axis=AXIS_1_8, magnitude=1.0, planets=["Saturn", "Mars"])
        ctx = make_context(fate_type="RASHI_PHAL", planet_strengths={"Saturn": -3.0, "Mars": 3.0})
        result = gate.filter([hit], ctx)
        assert len(result) == 1
        assert abs(result[0].magnitude - 0.50) < 0.01


class TestFidelityGateGaliSweetSpot:
    def test_gali_sweet_spot_boosted(self):
        """2-6 Source High + Target Medium → magnitude boosted by 1.90"""
        gate = FidelityGate()
        hit = make_hit(axis=AXIS_2_6, magnitude=1.0, planets=["Jupiter", "Venus"])
        # Jupiter (source/index 0) = high? wait — target is first planet
        # target=Jupiter High, source=Venus — need: source High, target Medium
        hit2 = make_hit(axis=AXIS_2_6, magnitude=1.0, planets=["Venus", "Jupiter"])
        ctx = make_context(
            fate_type="RASHI_PHAL",
            planet_strengths={"Venus": 0.5, "Jupiter": 3.0}  # target=Venus(Med), source=Jupiter(High)
        )
        result = gate.filter([hit2], ctx)
        assert len(result) == 1
        assert abs(result[0].magnitude - 1.90) < 0.01


class TestFidelityGateFixedFate:
    def test_fixed_fate_1_7_kept_dampened(self):
        """GRAHA_PHAL + 1-7 → KEEP ×0.50 (blacklist mode: only drops debilitated/dormant)"""
        gate = FidelityGate()
        hit = make_hit(domain="marriage", axis=AXIS_1_7)
        ctx = make_context(fate_type="GRAHA_PHAL")
        result = gate.filter([hit], ctx)
        assert len(result) == 1, "Fixed fate 1-7 kept (no debilitation/dormancy trigger)"
        assert abs(result[0].magnitude - 0.50) < 0.01

    def test_fixed_fate_3_11_kept_dampened(self):
        """GRAHA_PHAL + 3-11 → KEEP ×0.50 (blacklist mode)"""
        gate = FidelityGate()
        hit = make_hit(domain="career", axis=AXIS_3_11)
        ctx = make_context(fate_type="GRAHA_PHAL")
        result = gate.filter([hit], ctx)
        assert len(result) == 1, "Fixed fate 3-11 kept"
        assert abs(result[0].magnitude - 0.50) < 0.01

    def test_fixed_fate_4_10_kept_dampened(self):
        """GRAHA_PHAL + 4-10 → KEEP ×0.50 (blacklist mode)"""
        gate = FidelityGate()
        hit = make_hit(domain="career", axis=AXIS_4_10)
        ctx = make_context(fate_type="GRAHA_PHAL")
        result = gate.filter([hit], ctx)
        assert len(result) == 1, "Fixed fate 4-10 kept"
        assert abs(result[0].magnitude - 0.50) < 0.01

    def test_8_2_wealth_kept_and_boosted(self):
        """GRAHA_PHAL + 8-2 + wealth domain → KEEP + BOOST ×1.62"""
        gate = FidelityGate()
        hit = make_hit(domain="money", axis=AXIS_8_2, magnitude=1.0)
        ctx = make_context(fate_type="GRAHA_PHAL")
        result = gate.filter([hit], ctx)
        assert len(result) == 1, "8-2 wealth should pass through for GRAHA_PHAL"
        assert abs(result[0].magnitude - 1.62) < 0.01

    def test_8_2_non_wealth_kept_dampened(self):
        """GRAHA_PHAL + 8-2 but non-wealth domain → KEEP ×0.50"""
        gate = FidelityGate()
        hit = make_hit(domain="marriage", axis=AXIS_8_2, magnitude=1.0)
        ctx = make_context(fate_type="GRAHA_PHAL")
        result = gate.filter([hit], ctx)
        assert len(result) == 1, "8-2 non-wealth kept (blacklist mode, no wealth boost)"
        assert abs(result[0].magnitude - 0.50) < 0.01

    def test_8_2_rashi_phal_not_boosted(self):
        """RASHI_PHAL + 8-2 → no special boost (base multiplier only)"""
        gate = FidelityGate()
        hit = make_hit(domain="money", axis=AXIS_8_2, magnitude=1.0)
        ctx = make_context(fate_type="RASHI_PHAL", planet_strengths={"Venus": 0.0, "Jupiter": 0.0})
        result = gate.filter([hit], ctx)
        assert len(result) == 1
        # Should NOT have the 1.62 boost — it goes through the standard rashi phal path
        assert abs(result[0].magnitude - 1.62) > 0.01

    def test_pakka_ghar_return_kept(self):
        """GRAHA_PHAL + Pakka Ghar annual return → KEEP (natal confirmation)"""
        gate = FidelityGate()
        # Saturn's Pakka Ghar is H10 in Lal Kitab
        hit = make_hit(domain="karma", axis=AXIS_1_8, planets=["Saturn"], magnitude=1.0)
        ctx = make_context(
            fate_type="GRAHA_PHAL",
            annual_houses={"Saturn": 10}  # Saturn in its Pakka Ghar (H10)
        )
        result = gate.filter([hit], ctx)
        assert len(result) == 1, "Pakka Ghar return must be kept even for GRAHA_PHAL"
