"""
Data contracts for the simplified Lal Kitab Prediction Engine.
Matches the user's request for 'core lal kitab grammar logic'.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional, TypedDict


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
    affected_people: list[str] = field(default_factory=list)
    affected_items: list[str] = field(default_factory=list)
    source_planets: list[str] = field(default_factory=list)
    source_houses: list[int] = field(default_factory=list)
    source_rules: list[str] = field(default_factory=list)
    remedy_applicable: bool = False
    remedy_hints: list[str] = field(default_factory=list)


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
