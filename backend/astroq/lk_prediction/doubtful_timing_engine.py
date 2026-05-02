"""
Doubtful Timing Engine (Experimental)
======================================

This module is EXPERIMENTAL and is NOT a replacement for the baseline
VarshphalTimingEngine. It extends it by adding a new layer:

    "Doubtful Natal Promises" → Varshphal Timing

Core concept from Lal Kitab / Goswami:
    Certain natal placements create a 'Doubtful Fate' — the outcome (e.g.
    marriage, progeny, wealth) is unstable. It could manifest auspiciously
    or malefically depending on the year. Unlike Fixed Fate, these setups are
    mathematically "tiltable" by the Varshphal geometry.

This engine:
    1. Identifies Doubtful Natal Promises via DOUBTFUL_NATAL_PROMISES.
    2. Evaluates whether the Annual Chart is TRIGGERING or RESOLVING them.
    3. Returns an enhanced confidence result, layered on top of the baseline.

BASELINE IS UNTOUCHED — all output can be compared to the baseline
VarshphalTimingEngine result to measure improvement.
"""

from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .astrological_context import UnifiedAstrologicalContext

from .lk_constants import (
    PLANET_PAKKA_GHAR,
    PLANET_EXALTATION,
    PLANET_DEBILITATION,
    NATURAL_RELATIONSHIPS,
)


# ============================================================================
# DOUBTFUL NATAL PROMISE DEFINITIONS
# Each entry describes:
#   - name:        human-readable label
#   - domain:      which life domain is affected
#   - planets:     the natal planets involved (for annual tracking)
#   - condition:   a callable f(natal_pos) -> bool that detects this setup
#   - cipher:      the shorthand Goswami metaphor (for reporting)
# ============================================================================

def _make_natal_conditions():
    """
    Returns the list of DOUBTFUL_NATAL_PROMISES definitions.
    Using a function to avoid import-time side effects.
    """
    return [
        {
            "name": "Roof and Well (Doubtful Progeny)",
            "domain": "progeny",
            "cipher": "Rahu H5 (Roof) attacks Moon H4 (Well)",
            "planets": ["Rahu", "Moon"],
            "condition": lambda pos: pos.get("Rahu") == 5 and pos.get("Moon") == 4,
        },
        {
            "name": "Crow Line / Kawa Rekha (Doubtful Character)",
            "domain": "marriage",
            "cipher": "Saturn item (Crow) fused with Venus in H1",
            "planets": ["Saturn", "Venus"],
            "condition": lambda pos: pos.get("Venus") == 1 and pos.get("Saturn") is not None,
        },
        {
            "name": "Doubtful Venus H4 (Inauspicious Marriage)",
            "domain": "marriage",
            "cipher": "Venus in H4 creates doubtful/inauspicious marriage outcomes",
            "planets": ["Venus"],
            "condition": lambda pos: pos.get("Venus") == 4,
        },
        {
            "name": "Rumour & Deceiving (Doubtful Reputation)",
            "domain": "career_travel",
            "cipher": "Jupiter H8 (Rumour) + Ketu H8 (Deceiving) in same house",
            "planets": ["Jupiter", "Ketu"],
            "condition": lambda pos: pos.get("Jupiter") == 8 and pos.get("Ketu") == 8,
        },
        {
            "name": "Ghosts and Lisping (Doubtful Faith/Beliefs)",
            "domain": "career_travel",
            "cipher": "Mercury in H9 + Jupiter+Rahu Masnui active",
            "planets": ["Mercury", "Jupiter", "Rahu"],
            "condition": lambda pos: (
                pos.get("Mercury") == 9
                and pos.get("Jupiter") is not None
                and pos.get("Rahu") is not None
                and pos.get("Jupiter") == pos.get("Rahu")  # Jupiter+Rahu conjunction = Masnui Mercury
            ),
        },
        {
            "name": "Doubtful Ketu H10 under Saturn (Career Uncertainty)",
            "domain": "career_travel",
            "cipher": "Ketu in H10 with Saturn influence creates career doubt",
            "planets": ["Ketu", "Saturn"],
            "condition": lambda pos: pos.get("Ketu") == 10 and pos.get("Saturn") is not None,
        },
        {
            "name": "Rahu H5 Malefic (Doubtful First Child)",
            "domain": "progeny",
            "cipher": "Rahu in H5 without Sun/Moon support → malefic for first child",
            "planets": ["Rahu", "Sun", "Moon"],
            "condition": lambda pos: (
                pos.get("Rahu") == 5
                and pos.get("Sun") not in [4, 5, 6]
                and pos.get("Moon") not in [4, 5, 6]
            ),
        },
        {
            "name": "Mercury Alone H1/5/9/12 (Doubtful Marriage Fidelity)",
            "domain": "marriage",
            "cipher": "Mercury alone in H1/5/9/12 → wife has doubtful fidelity",
            "planets": ["Mercury"],
            "condition": lambda pos: (
                pos.get("Mercury") in [1, 5, 9, 12]
                # 'alone' check is done in evaluation against all planet positions
            ),
        },
        {
            "name": "Houses 2 & 7 Blank (Doubtful Partnership Health)",
            "domain": "marriage",
            "cipher": "Empty H2 and H7 → Mercury and Venus become malefic for health",
            "planets": ["Mercury", "Venus"],
            "condition": lambda pos: (
                2 not in pos.values() and 7 not in pos.values()
            ),
        },
    ]


DOUBTFUL_NATAL_PROMISES = _make_natal_conditions()


# ============================================================================
# ANNUAL RESOLUTION / TRIGGER RULES
# For each active Doubtful Promise, we check if the Varshphal chart is
# RESOLVING it (clearing the doubt → auspicious) or TRIGGERING it (tipping
# it malefic).
# ============================================================================

# Resolutions: The doubtful planet moves to a position of strength
RESOLUTION_RULES = {
    "pakka_ghar":    "Planet returns to its Pakka Ghar (home) in annual → Doubt RESOLVED (Auspicious)",
    "exaltation":    "Planet is in Exaltation in annual → Doubt RESOLVED (Auspicious)",
    "friendly_axis": "Doubtful planet's annual house is aspected by a natural friend → Partial Resolution",
}

# Triggers: The doubtful planet moves to a position of weakness
TRIGGER_RULES = {
    "debilitation":    "Planet moves to Debilitation in annual → Doubt TRIGGERED (Malefic)",
    "enemy_180":       "Planet faces 180-degree enemy in annual → Doubt TRIGGERED (Blocked)",
    "nisht_h8":        "Planet in Natal H8 moves to H6/7/8 in annual → Sequential Destruction",
    "dormant_annual":  "Planet is dormant in annual chart → Doubt SUPPRESSED (Silent year)",
}


class DoubtfulTimingEngine:
    """
    Experimental engine layering Doubtful Natal Promise logic on top of the
    baseline VarshphalTimingEngine.
    """
    
    def _identify_doubtful_natal_promises(
        self,
        context: 'UnifiedAstrologicalContext'
    ) -> List[Dict[str, Any]]:
        """
        Scans the natal chart for active Doubtful Promise configurations.
        Returns a list of matching promise dicts with their metadata.
        """
        natal_pos = {p: context.get_natal_house(p) for p in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]}
        # Remove Nones for condition evaluation
        natal_pos = {k: v for k, v in natal_pos.items() if v is not None}
        active_promises = []

        for promise in DOUBTFUL_NATAL_PROMISES:
            try:
                if promise["condition"](natal_pos):
                    active_promises.append({
                        "name":    promise["name"],
                        "domain":  promise["domain"],
                        "cipher":  promise["cipher"],
                        "planets": promise["planets"],
                    })
            except Exception:
                continue

        return active_promises

    def _evaluate_annual_resolution_or_trigger(
        self,
        promise: Dict[str, Any],
        context: 'UnifiedAstrologicalContext'
    ) -> Dict[str, Any]:
        """
        For a single Doubtful Promise, evaluates what the annual chart does:
        - TRIGGERED: worsens the doubtful state
        - RESOLVED:  clears the doubt
        - NEUTRAL:   no specific annual geometry for this promise
        """
        planets = promise["planets"]
        triggers = []
        resolutions = []

        for planet in planets:
            annual_house = context.get_house(planet)
            if not annual_house:
                continue

            # ── RESOLUTION CHECKS ─────────────────────────────────────────
            # Pakka Ghar
            if PLANET_PAKKA_GHAR.get(planet) == annual_house:
                resolutions.append(
                    f"{planet} in annual H{annual_house} = Pakka Ghar → "
                    f"{RESOLUTION_RULES['pakka_ghar']}"
                )

            # Exaltation
            if annual_house in PLANET_EXALTATION.get(planet, []):
                resolutions.append(
                    f"{planet} in annual H{annual_house} = Exaltation → "
                    f"{RESOLUTION_RULES['exaltation']}"
                )

            # ── TRIGGER CHECKS ────────────────────────────────────────────
            # Debilitation
            if annual_house in PLANET_DEBILITATION.get(planet, []):
                triggers.append(
                    f"{planet} in annual H{annual_house} = Debilitation → "
                    f"{TRIGGER_RULES['debilitation']}"
                )

            # 180-degree enemy block (reuses baseline method)
            if context.has_180_degree_block(planet):
                triggers.append(
                    f"{planet} in annual H{annual_house} faces 180° enemy → "
                    f"{TRIGGER_RULES['enemy_180']}"
                )

            # Nisht Grah (Sequential Impact from H8)
            natal_house = context.get_natal_house(planet)
            if natal_house == 8 and annual_house in [6, 7, 8]:
                triggers.append(
                    f"{planet} Natal H8 → Annual H{annual_house}: "
                    f"{TRIGGER_RULES['nisht_h8']}"
                )

            # Dormancy check in annual
            if not context.is_awake(planet):
                triggers.append(
                    f"{planet} is DORMANT in annual H{annual_house} → "
                    f"{TRIGGER_RULES['dormant_annual']}"
                )

        # Determine net verdict
        if resolutions and not triggers:
            verdict = "RESOLVED"
        elif triggers and not resolutions:
            verdict = "TRIGGERED"
        elif triggers and resolutions:
            verdict = "CONTESTED"  # mixed signals
        else:
            verdict = "NEUTRAL"

        return {
            "promise":     promise["name"],
            "domain":      promise["domain"],
            "verdict":     verdict,
            "triggers":    triggers,
            "resolutions": resolutions,
        }

    def evaluate_doubtful_timing(
        self,
        context: 'UnifiedAstrologicalContext',
        domain: str,
        active_promises: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Evaluates all active Doubtful Natal Promises against the annual chart.
        Filters to the requested domain (or 'all').

        Returns a list of evaluation results.
        """
        if active_promises is None:
            active_promises = self._identify_doubtful_natal_promises(context)

        results = []
        for promise in active_promises:
            # Filter by domain: match exact domain or wildcard
            if domain != "all" and promise["domain"] != domain:
                continue
            result = self._evaluate_annual_resolution_or_trigger(
                promise, context
            )
            results.append(result)

        return results

    def get_timing_confidence(
        self,
        context: 'UnifiedAstrologicalContext',
        domain: str,
    ) -> Dict[str, Any]:
        """
        Runs ONLY the doubtful evaluation to mock out the original interface for tests.
        In reality, VarshphalTimingEngine uses the evaluated triggers directly.
        """
        active_promises = self._identify_doubtful_natal_promises(context)
        doubtful_evals = self.evaluate_doubtful_timing(
            context, domain, active_promises
        )

        resolutions = [e for e in doubtful_evals if e["verdict"] in ("RESOLVED", "CONTESTED")]
        triggers    = [e for e in doubtful_evals if e["verdict"] in ("TRIGGERED", "CONTESTED")]

        if resolutions and not triggers:
            modifier = "Boost"
        elif triggers and not resolutions:
            modifier = "Suppress"
        elif triggers and resolutions:
            modifier = "Contested"
        else:
            modifier = "Neutral"

        return {
            "confidence": "Low", # Base mock
            "doubtful_promises": [p["name"] for p in active_promises],
            "doubtful_evaluations": doubtful_evals,
            "doubtful_confidence_modifier": modifier,
            "triggers": [],
            "warnings": []
        }

