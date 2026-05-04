"""
timing_engine_protocol.py
=========================
Formal seam for timing-engine adapters.

Defines the Protocol that VarshphalTimingEngine and DoubtfulTimingEngine
must both satisfy. ContextualAssembler selects the correct adapter based
on the prediction's fate_type (GRAHA_PHAL → Varshphal, RASHI_PHAL → Doubtful).

One adapter = hypothetical seam.
Two adapters = real seam. This is the real seam.

Adapters
--------
VarshphalTimingEngine  — implements Fixed Fate (Graha Phal) timing logic.
                         Full Goswami 1952 geometric trigger evaluation.
DoubtfulTimingEngine   — implements Doubtful Fate (Rashi Phal) timing logic.
                         Evaluates DOUBTFUL_NATAL_PROMISES against annual chart.

Usage (ContextualAssembler)
---------------------------
    engine = TimingEngineRouter.for_fate_type(fate_type, varshphal, doubtful)
    result = engine.get_timing_confidence(context, domain, fate_type, age)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .astrological_context import UnifiedAstrologicalContext


# ---------------------------------------------------------------------------
# Canonical return schema
# ---------------------------------------------------------------------------
# Both adapters MUST return a dict that satisfies this shape.
# Fields marked Optional are absent on non-applicable paths.
#
#   confidence:     "High" | "Medium" | "Low" | "None"
#   prohibited:     True if an age-gate blocked this year entirely
#   reason:         human-readable explanation of the confidence rating
#   triggers:       list[str] — trigger descriptions that fired
#   warnings:       list[str] — non-blocking alerts
#   raw_matches:    list[dict] — full trigger objects (VarshphalTimingEngine only)
#   friction_signal: str | None — system-friction annotation
#
# Minimum required keys: confidence, prohibited, reason, triggers, warnings.
TIMING_RESULT_KEYS = frozenset({"confidence", "prohibited", "reason", "triggers", "warnings"})


def validate_timing_result(result: Dict[str, Any], adapter_name: str = "") -> None:
    """Raises ValueError if result is missing required keys."""
    missing = TIMING_RESULT_KEYS - result.keys()
    if missing:
        raise ValueError(
            f"TimingEngine adapter '{adapter_name}' returned an invalid result. "
            f"Missing keys: {missing}"
        )


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------
try:
    from typing import Protocol, runtime_checkable
except ImportError:
    from typing_extensions import Protocol, runtime_checkable  # type: ignore


@runtime_checkable
class TimingEngine(Protocol):
    """
    Structural interface for timing-engine adapters.

    A timing engine maps (context, domain, fate_type, age) → TimingResult.
    Any object with a matching `get_timing_confidence` signature satisfies this
    protocol without explicit inheritance.
    """

    def get_timing_confidence(
        self,
        context: "UnifiedAstrologicalContext",
        domain: str,
        fate_type: str,
        age: int,
    ) -> Dict[str, Any]:
        """
        Evaluate the timing confidence for a prediction.

        Parameters
        ----------
        context   : The full astrological context for this chart year.
        domain    : The prediction domain (e.g. 'marriage', 'career_travel').
        fate_type : 'GRAHA_PHAL' | 'RASHI_PHAL' | 'HYBRID'
        age       : The chart year (1–75).

        Returns
        -------
        dict with at least keys: confidence, prohibited, reason, triggers, warnings.
        """
        ...


# ---------------------------------------------------------------------------
# Router: selects the correct adapter for a given fate_type
# ---------------------------------------------------------------------------
class TimingEngineRouter:
    """
    Selects the right timing-engine adapter based on fate_type.

    GRAHA_PHAL → VarshphalTimingEngine  (Fixed Fate, full geometric evaluation)
    RASHI_PHAL → DoubtfulTimingEngine   (Doubtful Fate, promise resolution)
    HYBRID     → VarshphalTimingEngine  (treat as fixed; most conservative)
    """

    @staticmethod
    def for_fate_type(
        fate_type: str,
        varshphal_engine: TimingEngine,
        doubtful_engine: TimingEngine,
    ) -> TimingEngine:
        """Returns the correct adapter for the given fate_type."""
        if fate_type == "RASHI_PHAL":
            return doubtful_engine
        return varshphal_engine  # GRAHA_PHAL, HYBRID, unknown → Varshphal

    @staticmethod
    def route_and_call(
        fate_type: str,
        varshphal_engine: TimingEngine,
        doubtful_engine: TimingEngine,
        context: "UnifiedAstrologicalContext",
        domain: str,
        age: int,
    ) -> Dict[str, Any]:
        """Convenience: routes + calls in one step."""
        engine = TimingEngineRouter.for_fate_type(fate_type, varshphal_engine, doubtful_engine)
        result = engine.get_timing_confidence(context, domain, fate_type, age)
        validate_timing_result(result, type(engine).__name__)
        return result
