"""
FidelityGate
============
Hard filter on RuleHit objects — inserted between RulesEngine and
ContextualAssembler in Pipeline.generate_predictions().

This is the **primary noise-reduction mechanism** for the Hammer and
Anvil logic. It either drops low-fidelity hits or adjusts their
magnitude based on the planet dignity / fate type / axis configuration.

Design decisions:
  - GRAHA_PHAL uses WHITELIST mode: all annual hits dropped EXCEPT
    the 8-2 wealth axis and Pakka Ghar returns.
  - HYBRID fate_type is treated as RASHI_PHAL (conservative).
  - Birth charts: this gate is a no-op (chart_type != "Yearly").
  - Unknown domains default to RASHI_PHAL (conservative).

Statistical basis for each rule is cited inline.
"""
from __future__ import annotations

import logging
from typing import List

from .data_contracts import RuleHit
from .aspect_fidelity_evaluator import (
    AspectFidelityEvaluator,
    AXIS_1_7,
    AXIS_1_8,
    AXIS_2_6,
    AXIS_4_10,
    AXIS_6_12,
    AXIS_8_2,
    AXIS_3_11,
)
from .lk_constants import PLANET_PAKKA_GHAR

logger = logging.getLogger(__name__)

# Domains classified as "wealth" for the 8-2 Fixed Wealth Correlation
WEALTH_DOMAINS = {"money", "property", "inheritance", "wealth", "finance"}


class FidelityGate:
    """
    Stateless filter: given a list of RuleHit objects and the current
    UnifiedAstrologicalContext, returns a filtered (and magnitude-adjusted)
    list where low-fidelity annual hits are dropped.
    """

    def __init__(self) -> None:
        self._evaluator = AspectFidelityEvaluator()

    def filter(
        self,
        hits: List[RuleHit],
        context,  # UnifiedAstrologicalContext — typed loosely to avoid circular import
    ) -> List[RuleHit]:
        """
        Apply fate-type and dignity-weighted filtering to rule hits.

        Only meaningful for annual (Yearly) charts. Birth charts pass through
        unchanged.
        """
        if context.chart_type != "Yearly":
            return hits  # No-op for birth charts

        filtered: List[RuleHit] = []
        for hit in hits:
            result = self._evaluate_hit(hit, context)
            if result is not None:
                filtered.append(result)

        dropped = len(hits) - len(filtered)
        if dropped > 0:
            logger.debug(
                "FidelityGate suppressed %d/%d hits for age=%s",
                dropped, len(hits), context.age
            )
        return filtered

    # ------------------------------------------------------------------ #
    # Internal: per-hit evaluation                                        #
    # ------------------------------------------------------------------ #

    def _evaluate_hit(self, hit: RuleHit, context) -> "RuleHit | None":
        """
        Returns the (possibly magnitude-adjusted) hit, or None if suppressed.
        """
        domain = hit.domain.strip().lower()
        fate_type = context.get_fate_type_for_domain(domain)
        axis = hit.axis

        # ── GRAHA_PHAL: Whitelist mode ──────────────────────────────────
        # Fixed Fate is structurally resistant to annual planetary movements.
        # Annual aspects act as stabilizers, not triggers (16-20% hit rate).
        # Only the 8-2 wealth axis and Pakka Ghar returns are reliable signals.
        if fate_type == "GRAHA_PHAL":
            return self._evaluate_fixed_fate(hit, axis, domain, context)

        # ── MASHKOOQ (NEITHER with doubtful promise): Axis boost ────────
        # Handled by DoubtfulTimingEngine; gate just applies 6-12 magnitude boost
        if fate_type == "NEITHER":
            # Pass through — DoubtfulTimingEngine handles these
            return hit

        # ── RASHI_PHAL / HYBRID-as-RASHI_PHAL: Blacklist mode ──────────
        return self._evaluate_rashi_phal(hit, axis, context)

    def _evaluate_fixed_fate(
        self, hit: RuleHit, axis: str, domain: str, context
    ) -> "RuleHit | None":
        """
        GRAHA_PHAL blacklist mode (inverted from whitelist).
        Fixed Fate is structurally resistant to annual noise — the data shows
        it has the best recall (Marriage 40%, Progeny 100%, Health 38.6%).
        Only DROP when there is a clear counter-signal:
        - Source planet is debilitated in the annual chart
        - ALL primary target planets are dormant (no activation possible)
        Everything else passes through with a conservative ×0.70 baseline.
        """
        from .lk_constants import PLANET_DEBILITATION

        # ── Drop condition 1: Source planet debilitated in annual chart ──
        for planet in hit.primary_target_planets:
            annual_house = context.get_house(planet)
            if annual_house and annual_house in PLANET_DEBILITATION.get(planet, []):
                logger.debug(
                    "FidelityGate: GRAHA_PHAL DROP %s debilitated in annual H%d → %s",
                    planet, annual_house, hit.rule_id
                )
                return None

        # ── Drop condition 2: ALL primary target planets are dormant ─────
        if hit.primary_target_planets:
            all_dormant = True
            for planet in hit.primary_target_planets:
                if context.is_awake(planet):
                    all_dormant = False
                    break
            if all_dormant:
                logger.debug(
                    "FidelityGate: GRAHA_PHAL DROP all planets dormant → %s",
                    hit.rule_id
                )
                return None

        # ── Baseline: KEEP with conservative ×0.50 multiplier ──────────
        base_mult = 0.50

        # Boost: 8-2 Fixed Wealth Correlation (61.9% Hit / 81.4% Silence)
        if axis == AXIS_8_2 and any(w in domain for w in WEALTH_DOMAINS):
            base_mult = 1.62
            logger.debug("FidelityGate: GRAHA_PHAL 8-2 wealth BOOST ×1.62 → %s", hit.rule_id)

        # Boost: Pakka Ghar return in annual chart (natal confirmation)
        if self._is_pakka_ghar_return(hit, context):
            base_mult = max(base_mult, 1.0)
            logger.debug("FidelityGate: GRAHA_PHAL Pakka Ghar return KEEP → %s", hit.rule_id)

        # Boost: Maturity Age window
        if context.age is not None:
            from .lk_pattern_constants import MATURITY_AGE_PATTERN
            maturity_ages = MATURITY_AGE_PATTERN.get("maturity_ages", {})
            mat_window = 2
            if getattr(context, 'config', None):
                try:
                    mat_window = int(context.config.get("timing.maturity_age_window", fallback=2))
                except (TypeError, ValueError):
                    mat_window = 2
            for planet in hit.primary_target_planets:
                m_age = maturity_ages.get(planet, 0)
                if m_age and abs(context.age - m_age) <= mat_window:
                    base_mult = max(base_mult, 1.0)
                    logger.debug(
                        "FidelityGate: GRAHA_PHAL Maturity Age window KEEP (age=%s, %s maturity=%s) → %s",
                        context.age, planet, m_age, hit.rule_id
                    )
                    break

        return self._clone_with_magnitude(hit, hit.magnitude * base_mult)


    def _evaluate_rashi_phal(
        self, hit: RuleHit, axis: str, context
    ) -> "RuleHit | None":
        """
        RASHI_PHAL / HYBRID blacklist mode — drop or adjust specific configs.
        """
        # Get target planet strength for dignity checks
        target_strength = self._get_target_strength(hit, context)
        source_strength = self._get_source_strength(hit, context)

        # ── Strong Shield: 1-7 + High target → DAMPEN ×0.30 (was DROP) ──
        # High-dignity planets on 1-7 axis are resistant to annual triggers,
        # but strong configurations (high magnitude) can still manifest.
        # A 70% magnitude reduction gates noise while preserving genuine signal.
        if axis == AXIS_1_7:
            cat = self._evaluator.categorize(target_strength)
            if cat == "High":
                logger.debug("FidelityGate: Strong Shield DAMPEN ×0.30 1-7+High → %s", hit.rule_id)
                return self._clone_with_magnitude(hit, hit.magnitude * 0.30)
            # Low target on 1-7 — modest but keep
            mult = self._evaluator.score_aspect(AXIS_1_7, source_strength, target_strength)
            return self._clone_with_magnitude(hit, hit.magnitude * mult)

        # ── Takkar 1-8: both Low → BOOST ×1.83; any High → DAMPEN ×0.5 ─
        if axis == AXIS_1_8:
            mult = self._evaluator.score_aspect(AXIS_1_8, source_strength, target_strength)
            return self._clone_with_magnitude(hit, hit.magnitude * mult)

        # ── Conditional Precision: 4-10 + Low target → BOOST ×1.85 ─────
        if axis == AXIS_4_10:
            mult = self._evaluator.score_aspect(AXIS_4_10, source_strength, target_strength)
            return self._clone_with_magnitude(hit, hit.magnitude * mult)

        # ── Gali Sweet Spot: 2-6, Source High + Target Medium → ×1.90 ──
        if axis == AXIS_2_6:
            mult = self._evaluator.score_aspect(AXIS_2_6, source_strength, target_strength)
            # Domain relevance gate: 2-6 axis is structurally noisy (high FP rate).
            # Require at least one involved planet to be a domain karaka — otherwise
            # dampen to ×0.10 to suppress indiscriminate firing.
            if not self._any_planet_is_domain_karaka(hit, context):
                mult *= 0.10
                logger.debug("FidelityGate: 2-6 axis domain gate DAMPEN → %s", hit.rule_id)
            return self._clone_with_magnitude(hit, hit.magnitude * mult)

        # ── 6-12 Axis: Mashkooq boost applied by DoubtfulTimingEngine ───
        if axis == AXIS_6_12:
            return hit  # Pass through; DTE applies the ~100% accuracy boost

        # ── 3-11 Support: low predictive value — dampen ─────────────────
        if axis == AXIS_3_11:
            return self._clone_with_magnitude(hit, hit.magnitude * 0.80)

        # ── Unknown / other axes: pass through unchanged ─────────────────
        return hit

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _get_target_strength(self, hit: RuleHit, context) -> float:
        """Returns the strength of the first primary target planet."""
        if hit.primary_target_planets:
            return context.get_planet_strength(hit.primary_target_planets[0])
        return 0.0

    def _get_source_strength(self, hit: RuleHit, context) -> float:
        """Returns the strength of the second primary planet (source/hammer)."""
        if len(hit.primary_target_planets) >= 2:
            return context.get_planet_strength(hit.primary_target_planets[1])
        return 0.0

    def _any_planet_is_domain_karaka(self, hit: RuleHit, context) -> bool:
        """
        Returns True if any primary target planet is a karaka for the hit's domain.
        Uses CYCLE_DOMAIN_KARAKAS from lk_pattern_constants for the mapping.
        """
        from .lk_pattern_constants import CYCLE_DOMAIN_KARAKAS
        domain = hit.domain.strip().lower()
        karakas = CYCLE_DOMAIN_KARAKAS.get(domain, [])
        if not karakas:
            return True  # Unknown domains pass through (no gate)
        for planet in hit.primary_target_planets:
            if planet in karakas:
                return True
        return False

    def _is_pakka_ghar_return(self, hit: RuleHit, context) -> bool:
        """
        Returns True if any primary target planet is in its Pakka Ghar
        in the current annual chart — a natal confirmation signal.
        """
        for planet in hit.primary_target_planets:
            annual_house = context.get_house(planet)
            pakka_house = PLANET_PAKKA_GHAR.get(planet)
            if annual_house and pakka_house and annual_house == pakka_house:
                return True
        return False

    @staticmethod
    def _clone_with_magnitude(hit: RuleHit, new_magnitude: float) -> RuleHit:
        """
        Returns a shallow copy of the hit with updated magnitude.
        Does NOT mutate the original (which may be shared across calls).
        """
        from dataclasses import replace
        return replace(hit, magnitude=new_magnitude)
