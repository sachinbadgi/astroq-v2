"""
AspectFidelityEvaluator
=======================
Universal primitive for dignity-weighted aspect accuracy.

Encodes the "Hammer and Anvil" research findings as a single,
stateless multiplier table. All fate-specific engines (FidelityGate,
VarshphalTimingEngine, DoubtfulTimingEngine) call this for consistent
dignity-based accuracy scoring.

Research Basis (from empirical fuzzing):
  - Weak Anvil Rule:  Low-dignity Target → hit probability peaks
  - Strong Shield:    High-dignity Target → dampened (×0.30)
  - Takkar Paradox:   Both Low on 1-8 axis → 83% accuracy
  - Gali Sweet Spot:  Source High + Target Medium on 2-6 → 89.7% accuracy
"""
from __future__ import annotations

from typing import Literal

# Axis label constants — used across FidelityGate, VarshphalTimingEngine, DoubtfulTimingEngine
AXIS_1_8  = "1-8"    # Takkar / Confrontation
AXIS_1_7  = "1-7"    # Opposition / Bilmukabil
AXIS_4_10 = "4-10"   # Square
AXIS_2_6  = "2-6"    # Gali / Blocked
AXIS_6_12 = "6-12"   # Resolution axis (Mashkooq)
AXIS_8_2  = "8-2"    # Fixed Wealth axis (Graha Phal)
AXIS_3_11 = "3-11"   # Support / Trine
AXIS_UNKNOWN = "unknown"

# Canonical mapping from house-pair frozenset to axis label
HOUSE_PAIR_TO_AXIS: dict[frozenset, str] = {
    frozenset({1, 8}):  AXIS_1_8,
    frozenset({1, 7}):  AXIS_1_7,
    frozenset({4, 10}): AXIS_4_10,
    frozenset({2, 6}):  AXIS_2_6,
    frozenset({6, 12}): AXIS_6_12,
    frozenset({8, 2}):  AXIS_8_2,   # same as {2, 8} — frozenset deduplicates
    frozenset({3, 11}): AXIS_3_11,
}

DignityCategory = Literal["Low", "Medium", "High"]


class AspectFidelityEvaluator:
    """
    Stateless evaluator: dignity category → aspect fidelity multiplier.

    Usage:
        afe = AspectFidelityEvaluator()
        cat = afe.categorize(strength_total)          # "Low" | "Medium" | "High"
        mult = afe.score_aspect("1-8", src_str, tgt_str)  # 0.0 – 2.0
    """

    # Dignity thresholds derived from DignityEngine scoring ranges:
    #   Debilitated ≈ -5.0  |  Pakka Ghar ≈ +2.2  |  Exalted ≈ +5.0
    LOW_THRESHOLD: float  = -2.0
    HIGH_THRESHOLD: float =  2.2

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def categorize(self, strength_total: float) -> DignityCategory:
        """Bucket a planet's strength_total into Low / Medium / High."""
        if strength_total <= self.LOW_THRESHOLD:
            return "Low"
        if strength_total >= self.HIGH_THRESHOLD:
            return "High"
        return "Medium"

    def score_aspect(
        self,
        axis: str,
        source_strength: float,
        target_strength: float,
    ) -> float:
        """
        Return a fidelity multiplier (0.0 – 2.0) for an aspect configuration.

        Multipliers are derived from empirical accuracy rates:
          - 1.0  = baseline (no change to magnitude)
          - >1.0 = high-fidelity configuration → boost
          - <1.0 = low-fidelity / noisy → dampen
          - 0.0  = strong silence signal → suppress entirely

        Callers should multiply hit.magnitude by this value.
        """
        src = self.categorize(source_strength)
        tgt = self.categorize(target_strength)
        return self._lookup(axis, src, tgt)

    @classmethod
    def axis_from_houses(cls, house_a: int, house_b: int) -> str:
        """Derive axis label from a pair of houses."""
        return HOUSE_PAIR_TO_AXIS.get(frozenset({house_a, house_b}), AXIS_UNKNOWN)

    # ------------------------------------------------------------------ #
    # Internal Lookup Table                                                #
    # ------------------------------------------------------------------ #

    def _lookup(
        self, axis: str, src: DignityCategory, tgt: DignityCategory
    ) -> float:
        # ── 1-8 Takkar ──────────────────────────────────────────────────
        if axis == AXIS_1_8:
            if src == "Low" and tgt == "Low":
                return 1.83   # Takkar Paradox: both weak → 83% accuracy
            if src == "High" or tgt == "High":
                return 0.50   # High-strength Takkar: noisy
            return 1.0        # Mixed / baseline

        # ── 1-7 Opposition ──────────────────────────────────────────────
        if axis == AXIS_1_7:
            if tgt == "High":
                return 0.30   # Strong Shield: dampen, don't suppress — genuine signals survive
            if tgt == "Low":
                return 1.30   # Weak anvil: susceptible
            return 0.80       # Medium target: modest

        # ── 4-10 Square ─────────────────────────────────────────────────
        if axis == AXIS_4_10:
            if tgt == "Low":
                return 1.85   # Conditional Precision: 85% hit rate
            if tgt == "High":
                return 0.60   # Planet resists trigger
            return 1.10       # Medium target: moderate

        # ── 2-6 Gali / Blocked ──────────────────────────────────────────
        if axis == AXIS_2_6:
            if src == "High" and tgt == "Medium":
                return 1.90   # Gali Sweet Spot: 89.7% hit rate
            if tgt == "Low":
                return 1.40   # Weak anvil still susceptible
            return 0.80       # Other configs: baseline

        # ── 6-12 Axis (base; DTE applies its own Mashkooq boost) ────────
        if axis == AXIS_6_12:
            return 1.0        # Fate engine applies multiplier on top

        # ── 8-2 Fixed Wealth Axis (base; gated by FidelityGate) ─────────
        if axis == AXIS_8_2:
            return 1.0        # FidelityGate applies ×1.62 for GRAHA_PHAL

        # ── 3-11 Support ────────────────────────────────────────────────
        if axis == AXIS_3_11:
            return 0.80       # Generally stabilizing, low predictive value

        # ── Unknown axis ─────────────────────────────────────────────────
        return 1.0
