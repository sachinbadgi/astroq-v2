"""
Data contracts for the simplified Lal Kitab Prediction Engine.
Matches the user's request for 'core lal kitab grammar logic'.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional, TypedDict, TYPE_CHECKING

if TYPE_CHECKING:
    from .grammar.base import GrammarHit


# ---------------------------------------------------------------------------
# Input Contract: Chart Data
# ---------------------------------------------------------------------------

class AspectInfo(TypedDict, total=False):
    aspecting_planet: str
    house: int
    strength: float
    aspect_type: str        # "Confrontation", "Foundation", etc.
    relationship: str       # "friend", "enemy"
    aspect_strength: float


class PlanetInHouse(TypedDict, total=False):
    house: int
    states: list[str]
    aspects: list[AspectInfo]
    strength_total: float
    sleeping_status: str
    dharmi_status: str


class ChartData(TypedDict, total=False):
    chart_type: str                         # "Birth" | "Yearly"
    chart_period: int                       # 0=birth, 1-75=annual year
    planets_in_houses: dict[str, PlanetInHouse]
    mangal_badh_status: str
    dharmi_kundli_status: str
    house_status: dict[str, str]            # {"1": "Occupied", "2": "Sleeping", ...}
    masnui_grahas_formed: list[dict]
    lal_kitab_debts: list[dict]
    achanak_chot_triggers: list[dict]
    varshaphal_metadata: dict[str, Any]


# ---------------------------------------------------------------------------
# Intermediate Contract: Enriched Chart
# ---------------------------------------------------------------------------

@dataclass
class EnrichedChart:
    """
    Typed result of ChartEnricher.enrich(). Wraps the source ChartData dict
    and provides typed access to all enrichment layers.

    Dict-compatible (__getitem__ / get) so SynthesisReporter and api/server.py
    continue to work without changes.

    planet_strengths is mutable during the grammar audit phase (step 4 of
    enrichment). After enrichment completes, it is read-only for downstream
    consumers.
    """
    source: ChartData
    masnui_planets: list[dict] = field(default_factory=list)
    house_status: dict[str, str] = field(default_factory=dict)
    planet_strengths: dict[str, EnrichedPlanet] = field(default_factory=dict)
    structural_type: str = ""
    dharmi_kundli_status: str = "Inactive"
    mangal_badh_status: str = "Inactive"
    debts: list[dict] = field(default_factory=list)
    grammar_hits: dict[str, list] = field(default_factory=dict)

    # Mapping from enrichment field names to the dict keys callers expect.
    # Enrichment fields are checked first, then fall through to source.
    _KEY_MAP = {
        "masnui_grahas_formed": "masnui_planets",
        "house_status": "house_status",
        "mangal_badh_status": "mangal_badh_status",
        "dharmi_kundli_status": "dharmi_kundli_status",
        "lal_kitab_debts": "debts",
        "grammar_audit_hits": "grammar_hits",
        "structural_type": "structural_type",
        "_enriched": "planet_strengths",
    }

    def __getitem__(self, key: str):
        if key in self._KEY_MAP:
            return getattr(self, self._KEY_MAP[key])
        return self.source[key]

    def get(self, key: str, default=None):
        try:
            return self[key]
        except KeyError:
            return default


# ---------------------------------------------------------------------------
# Intermediate Contract: Enriched Planet
# ---------------------------------------------------------------------------

class StrengthBreakdown(TypedDict, total=False):
    aspects: float
    dignity: float
    scapegoat: float
    disposition: float
    mangal_badh: float
    cycle_35yr: float
    bilmukabil: float
    sathi: float
    dhoka: float
    sleeping: float
    dharmi: float
    achanak_chot: float
    masnui_feedback: float
    rin: float


class EnrichedPlanet(TypedDict, total=False):
    house: int
    sleeping_status: str
    kaayam_status: str
    dharmi_status: str
    sathi_companions: list[str]
    bilmukabil_hostile_to: list[str]
    is_masnui_parent: bool
    masnui_feedback_strength: float
    dhoka_graha: bool
    achanak_chot_active: bool
    rin_debts: list[str]
    strength_total: float
    strength_breakdown: StrengthBreakdown


# ---------------------------------------------------------------------------
# Output Contract: LKPrediction
# ---------------------------------------------------------------------------

@dataclass
class LKPrediction:
    """Final prediction output for NotebookLM."""
    domain: str
    event_type: str
    prediction_text: str
    polarity: str                   # "benefic", "malefic"
    peak_age: int = 0
    magnitude: float = 0.0
    gravity_score: float = 0.0
    forensic_proof: str = ""
    affected_people: list[str] = field(default_factory=list)
    affected_items: list[str] = field(default_factory=list)
    source_planets: list[str] = field(default_factory=list)
    source_houses: list[int] = field(default_factory=list)
    source_rules: list[str] = field(default_factory=list)
    remedy_applicable: bool = False
    remedy_hints: list[str] = field(default_factory=list)
    timing_confidence: str = ""
    timing_signals: list[str] = field(default_factory=list)
    visual_manifest: dict[str, Any] = field(default_factory=dict)
    afflicts_living: bool = False


# ---------------------------------------------------------------------------
# Internal: Rule Hit
# ---------------------------------------------------------------------------

@dataclass
class RuleHit:
    """A rule that fired during evaluation."""
    rule_id: str
    domain: str
    description: str
    verdict: str
    magnitude: float
    scoring_type: str       # "boost", "penalty"
    primary_target_planets: list[str] = field(default_factory=list)
    target_houses: list[int] = field(default_factory=list)
    source_page: str = ""
    success_weight: float = 0.0
    specificity: int = 1
    afflicts_living: bool = False
    # Axis label derived from the primary planet pair's house geometry.
    # Populated by RulesEngine from aspect data. Used by FidelityGate.
    # E.g. "1-8", "1-7", "4-10", "2-6", "6-12", "8-2", "3-11", "unknown"
    axis: str = "unknown"
