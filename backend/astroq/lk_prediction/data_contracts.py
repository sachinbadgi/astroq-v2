"""
Data contracts for the LK Prediction Model v2.

All shared types used across modules are defined here to ensure
consistent interfaces between components.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypedDict


# ---------------------------------------------------------------------------
# Input Contract: Chart Data
# ---------------------------------------------------------------------------

class AspectInfo(TypedDict, total=False):
    aspecting_planet: str
    house: int
    strength: float
    aspect_type: str        # "Confrontation", "Foundation", "General Condition", etc.
    relationship: str       # "friend", "enemy", "equal"
    aspect_strength: float  # Numeric strength from ASPECT_STRENGTH_DATA


class PlanetInHouse(TypedDict, total=False):
    house: int
    states: list[str]           # ["Exalted", "Fixed House Lord", ...]
    aspects: list[AspectInfo]
    strength_total: float
    sleeping_status: str
    dharmi_status: str


class ChartData(TypedDict, total=False):
    chart_type: str                         # "Birth" | "Yearly"
    chart_period: int                       # 0=birth, 1-75=annual year
    planets_in_houses: dict[str, PlanetInHouse]
    mangal_badh_counter: int
    mangal_badh_status: str
    dharmi_kundli_status: str
    house_status: dict[str, str]            # {"1": "Occupied", "2": "Sleeping House", ...}
    masnui_grahas_formed: list[dict]
    lal_kitab_debts: list[dict]
    achanak_chot_triggers: list[dict]
    varshaphal_metadata: dict[str, Any]
    dhoka_graha_analysis: list[dict]


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
    # From StrengthEngine
    house: int
    raw_aspect_strength: float
    dignity_score: float
    scapegoat_adjustment: float

    # From GrammarAnalyser
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

    # Final
    strength_total: float
    strength_breakdown: StrengthBreakdown


# ---------------------------------------------------------------------------
# Output Contract: LKPrediction
# ---------------------------------------------------------------------------

@dataclass
class LKPrediction:
    """Final prediction output from the pipeline."""
    domain: str                     # "career", "marriage", "health", etc.
    event_type: str                 # "promotion", "marriage_timing", etc.
    prediction_text: str            # Natural language prediction
    confidence: str                 # "certain", "highly_likely", "possible"
    polarity: str                   # "benefic", "malefic", "mixed"
    peak_age: int = 0
    age_window: tuple[int, int] = (0, 0)
    probability: float = 0.0
    affected_people: list[str] = field(default_factory=list)
    affected_items: list[str] = field(default_factory=list)
    source_planets: list[str] = field(default_factory=list)
    source_houses: list[int] = field(default_factory=list)
    source_rules: list[str] = field(default_factory=list)
    remedy_applicable: bool = False
    remedy_hints: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Intermediate: Classified Event (between EventClassifier and Translator)
# ---------------------------------------------------------------------------

@dataclass
class ClassifiedEvent:
    """Event detected and classified by the EventClassifier."""
    planet: str
    house: int
    domains: list[str]
    sentiment: str          # "BENEFIC", "MALEFIC", "VOLATILE", "MIXED"
    probability: float
    magnitude: float
    is_peak: bool
    peak_type: str          # "ABSOLUTE", "MOMENTUM", "NONE"
    prediction_text: str
    contributing_rules: list[str] = field(default_factory=list)
    peak_age: int = 0
    age_window: tuple[int, int] = (0, 0)
    ea: float = 0.0               
    source_planets: list[str] = field(default_factory=list)
    source_houses: list[int] = field(default_factory=list)
    fate_type: str = ""     # "graha_phal", "rashi_phal"


# ---------------------------------------------------------------------------
# Intermediate: Rule Hit (from RulesEngine)
# ---------------------------------------------------------------------------

@dataclass
class RuleHit:
    """A rule that fired during evaluation."""
    rule_id: str
    domain: str
    description: str
    verdict: str
    magnitude: float
    scoring_type: str       # "boost", "penalty", "neutral"
    primary_target_planets: list[str] = field(default_factory=list)
    target_houses: list[int] = field(default_factory=list)
    source_page: str = ""
    specificity: int = 0
    success_weight: float = 0.0
