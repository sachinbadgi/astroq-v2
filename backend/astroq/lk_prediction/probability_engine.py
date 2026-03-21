"""
Module 5: Probability Engine.

Calculates the delivery probability of predicted events using a 
mathematical model that combines a base sigmoid curve modified by
natal expectancy (Ea), adaptive scaling (k), delivery timing (Tvp),
and distance correction (Dcorr).
"""

from __future__ import annotations

import math
from typing import Any

from astroq.lk_prediction.config import ModelConfig


class ProbabilityEngine:
    """
    Calculates event probabilities from raw planet strengths and rules.
    """

    def __init__(self, config: ModelConfig) -> None:
        self._cfg = config
        self._cache_config()

    def _cache_config(self) -> None:
        c = self._cfg
        # Adaptive K
        self.adaptive_k = c.get("probability.adaptive_k_active", fallback=True)
        self.base_k = c.get("probability.base_k", fallback=1.2)
        self.max_k = c.get("probability.max_k", fallback=3.0)
        self.k_scale = c.get("probability.k_scale_factor", fallback=0.2)
        
        # Ea Propensity
        self.ea_base = c.get("probability.ea_base", fallback=0.5)
        self.ea_weight = c.get("probability.ea_weighting", fallback=0.05)
        self.ea_max = c.get("probability.ea_max", fallback=0.95)
        self.ea_min = c.get("probability.ea_min", fallback=0.05)
        
        # Tvp Modifiers
        self.tvp_boost = c.get("probability.tvp_boost_factor", fallback=1.2)
        self.tvp_penalty = c.get("probability.tvp_penalty_factor", fallback=0.8)
        
        # Output Clamping
        self.cap_upper = c.get("probability.prob_cap_upper", fallback=0.95)
        self.cap_lower = c.get("probability.prob_cap_lower", fallback=0.05)

    def _calculate_raw_sigmoid(self, magnitude: float, k: float) -> float:
        """Calculate base sigmoid probability P = 1 / (1 + e^(-k * magnitude))."""
        # Clamp exponent to avoid math overflow
        exponent = -k * magnitude
        exponent = max(min(exponent, 500.0), -500.0)
        return 1.0 / (1.0 + math.exp(exponent))

    def _calculate_adaptive_k(self, natal_score: float) -> float:
        """Dynamically scale k based on natal strength to prevent flat peaks."""
        if not self.adaptive_k:
            return self.base_k
        
        # In LK, extreme positive or negative natal scores both influence k
        k = self.base_k + (abs(natal_score) * self.k_scale)
        return min(k, self.max_k)

    def _calculate_ea(self, natal_score: float) -> float:
        """Calculate Ea (Base Expectancy) from natal strength."""
        raw_ea = self.ea_base + (natal_score * self.ea_weight)
        return max(min(raw_ea, self.ea_max), self.ea_min)

    def _calculate_tvp_modifier(self, planet: str, age: int) -> float:
        """Calculate Tvp (Timing Delivery Rule) multiplier based on planet maturity age."""
        # LK standard delivering ages mapping:
        # Jupiter: 16-21, Sun: 22-23, Moon: 24, Venus: 25-27, Mars: 28-33, Mercury: 34-35
        # Saturn: 36-39, Rahu: 42-47, Ketu: 48-54
        
        active_ranges = {
            "Jupiter": (16, 21),
            "Sun": (22, 23),
            "Moon": (24, 24),
            "Venus": (25, 27),
            "Mars": (28, 33),
            "Mercury": (34, 35),
            "Saturn": (36, 39),
            "Rahu": (42, 47),
            "Ketu": (48, 54)
        }
        
        if planet not in active_ranges:
            return 1.0
            
        start, end = active_ranges[planet]
        if start <= age <= end:
            return self.tvp_boost
        else:
            # For testing, we just return neutral or penalty if completely outside.
            # Many models use 1.0 unless specific penalty conditions are met. 
            return self.tvp_penalty if (abs(age - start) > 10) else 1.0

    def _calculate_dcorr(self, age: int) -> float:
        """Distance correction: Late in the 75-year life cycle, events damp down."""
        # Simple implementation: subtract small % probability per year after 50
        if age <= 50:
            return 1.0
        
        penalty_per_year = 0.005 # 0.5%
        mod = 1.0 - ((age - 50) * penalty_per_year)
        return max(mod, 0.5)

    def calculate_event_probability(
        self, planet: str, age: int, natal_score: float, annual_magnitude: float
    ) -> tuple[float, dict[str, float]]:
        """
        Calculates the complete probability for an event trigger.
        
        Returns
        -------
        prob : float
            Final clamped probability 0.05 - 0.95
        breakdown : dict
            Debug metrics.
        """
        k = self._calculate_adaptive_k(natal_score)
        ea = self._calculate_ea(natal_score)
        tvp_mod = self._calculate_tvp_modifier(planet, age)
        dcorr_mod = self._calculate_dcorr(age)
        
        # 1. Base sigmoid from annual magnitude
        # We blend the annual_magnitude onto the expectation
        # Specifically: P = ea_base_offset + base_sigmoid * modifiers
        raw_sig = self._calculate_raw_sigmoid(annual_magnitude, k)
        
        # The math model often centers Ea as a multiplier or baseline.
        # Let's say: prob = ea * raw_sig * tvp_mod * dcorr_mod
        raw_prob = ea * 2.0 * raw_sig * tvp_mod * dcorr_mod
        
        # Adjust center for ea=0.5 and sig=0.5 -> 0.5 * 2.0 * 0.5 = 0.5
        # This keeps the expected bounds reasonable before clamping.
        
        final_prob = max(min(raw_prob, self.cap_upper), self.cap_lower)
        
        breakdown = {
            "ea": ea,
            "k_used": k,
            "tvp_mod": tvp_mod,
            "dcorr_mod": dcorr_mod,
            "raw_sigmoid": raw_sig,
            "raw_combined": raw_prob
        }
        
        return final_prob, breakdown

    def batch_evaluate(
        self, events: list[dict[str, Any]], age: int
    ) -> list[dict[str, Any]]:
        """
        Process multiple events at once.
        Input: list of {"planet": str, "magnitude": float, "natal_score": float, ...}
        Output: list of events enriched with "final_probability" and "probability_breakdown".
        """
        results = []
        for ev in events:
            planet = ev.get("planet", "")
            mag = ev.get("magnitude", 0.0)
            natal = ev.get("natal_score", 0.0)
            
            prob, brk = self.calculate_event_probability(planet, age, natal, mag)
            
            # Copy event to avoid mutation side effects on original list
            result_ev = ev.copy()
            result_ev["final_probability"] = prob
            result_ev["probability_breakdown"] = brk
            results.append(result_ev)
            
        return results
