"""
FidelityShield
==============
Centralized gatekeeper for predictive fidelity. 
Filters RuleHit objects based on Fate Type (Graha vs Rashi), 
Planetary State (MachineLedger), and Dignity Ladder (Hierarchy of Power).
"""
import logging
from typing import List, Optional, Any, Dict
from dataclasses import replace

from .data_contracts import RuleHit
from .aspect_fidelity_evaluator import (
    AspectFidelityEvaluator,
    AXIS_1_7, AXIS_1_8, AXIS_2_6, AXIS_4_10,
    AXIS_6_12, AXIS_8_2, AXIS_3_11
)

logger = logging.getLogger(__name__)

WEALTH_DOMAINS = {"money", "property", "inheritance", "wealth", "finance"}

class FidelityShield:
    """
    Deep Module: Centralizes fate-aware suppression logic.
    Eliminates 'Confidence Drift' by enforcing strict mechanical gates.
    """

    def __init__(self) -> None:
        self._evaluator = AspectFidelityEvaluator()

    def evaluate_signals(self, hits: List[RuleHit], context: Any) -> List[RuleHit]:
        """
        Primary interface: returns filtered and adjusted hits.
        """
        if context.chart_type != "Yearly":
            return hits

        filtered: List[RuleHit] = []
        for hit in hits:
            result = self.evaluate_signal(hit, context)
            if result is not None:
                filtered.append(result)
        
        return filtered

    def evaluate_signal(self, hit: RuleHit, context: Any) -> Optional[RuleHit]:
        """
        Returns a magnitude-adjusted RuleHit or None if suppressed.
        """
        # Sanitize targets
        targets = hit.primary_target_planets
        if not hasattr(targets, "__iter__") or isinstance(targets, bool):
            # Coerce to empty list if invalid
            hit = replace(hit, primary_target_planets=[])
        
        domain = hit.domain.strip().lower()
        fate_type = context.get_fate_type_for_domain(domain)
        axis = hit.axis

        # ── GRAHA_PHAL (Fixed Fate): Whitelist Logic ────────────────────────
        # 1. Check for Debilitation (Hard Suppression)
        if fate_type == "GRAHA_PHAL":
            for planet in hit.primary_target_planets:
                house = context.get_house(planet)
                if house and context.dignity_engine.get_dignity_ladder_score(planet, house) < 0:
                    return None # Debilitated -> No Fixed Result
            
            # 2. Check for Dormancy (Suppression)
            all_dormant = True
            for planet in hit.primary_target_planets:
                if context.is_awake(planet):
                    all_dormant = False
                    break
            if all_dormant:
                return None

            # 3. Magnitude Scaling (×0.80 Baseline)
            multiplier = 0.80
            if axis == AXIS_8_2 and any(w in domain for w in WEALTH_DOMAINS):
                multiplier = 1.62
            
            # Confirm confirmation signals
            if self._has_confirmation_signal(hit, context):
                multiplier = max(multiplier, 1.0)
            
            return replace(hit, magnitude=hit.magnitude * multiplier)

        # ── RASHI_PHAL (Doubtful Fate): Blacklist Logic ─────────────────────
        return self._evaluate_rashi_phal(hit, axis, context)

    def _evaluate_rashi_phal(self, hit: RuleHit, axis: str, context: Any) -> Optional[RuleHit]:
        # Dignity checks
        target_strength = self._get_target_strength(hit, context)
        source_strength = self._get_source_strength(hit, context)
        
        # 1. 1-7 Axis (Strong Shield)
        if axis == AXIS_1_7:
            if self._evaluator.categorize(target_strength) == "High":
                return replace(hit, magnitude=hit.magnitude * 0.30)
            mult = self._evaluator.score_aspect(AXIS_1_7, source_strength, target_strength)
            return replace(hit, magnitude=hit.magnitude * mult)

        # 2. 1-8 Axis (Takkar)
        if axis == AXIS_1_8:
            mult = self._evaluator.score_aspect(AXIS_1_8, source_strength, target_strength)
            return replace(hit, magnitude=hit.magnitude * mult)

        # 3. 4-10 Axis (Conditional Precision)
        if axis == AXIS_4_10:
            mult = self._evaluator.score_aspect(AXIS_4_10, source_strength, target_strength)
            return replace(hit, magnitude=hit.magnitude * mult)

        # 4. 2-6 Axis (Domain Gate)
        if axis == AXIS_2_6:
            mult = self._evaluator.score_aspect(AXIS_2_6, source_strength, target_strength)
            if not self._any_planet_is_domain_karaka(hit, context):
                mult *= 0.10
            return replace(hit, magnitude=hit.magnitude * mult)

        # 5. 3-11 Axis (Dampen)
        if axis == AXIS_3_11:
            return replace(hit, magnitude=hit.magnitude * 0.80)

        return hit

    def _has_confirmation_signal(self, hit: RuleHit, context: Any) -> bool:
        """Checks for Pakka Ghar return or Maturity Age window."""
        for planet in hit.primary_target_planets:
            house = context.get_house(planet)
            # Use Dignity Ladder for Return detection
            if context.dignity_engine.get_dignity_ladder_score(planet, house) >= 1.5:
                return True
            
            # Maturity Age window
            if context.check_maturity_age(planet):
                # If they are exactly at maturity age (or within window)
                from .lk_pattern_constants import MATURITY_AGE_PATTERN
                mat_age = MATURITY_AGE_PATTERN.get("maturity_ages", {}).get(planet, 0)
                if mat_age and abs(context.age - mat_age) <= 1:
                    return True
        return False

    def _get_target_strength(self, hit: RuleHit, context: Any) -> float:
        return context.get_planet_strength(hit.primary_target_planets[0]) if hit.primary_target_planets else 0.0

    def _get_source_strength(self, hit: RuleHit, context: Any) -> float:
        return context.get_planet_strength(hit.primary_target_planets[1]) if len(hit.primary_target_planets) >= 2 else 0.0

    def _any_planet_is_domain_karaka(self, hit: RuleHit, context: Any) -> bool:
        from .lk_pattern_constants import CYCLE_DOMAIN_KARAKAS
        domain = hit.domain.strip().lower()
        karakas = CYCLE_DOMAIN_KARAKAS.get(domain, [])
        if not karakas: return True
        
        targets = hit.primary_target_planets
        if not hasattr(targets, "__iter__") or isinstance(targets, bool):
            logger.error(f"RuleHit {hit.rule_id} has invalid primary_target_planets: {targets} (type: {type(targets)})")
            return True # Conservative fallback
            
        return any(p in karakas for p in targets)
