"""
Data contracts for the LK Prediction Model v2.

All shared types used across modules are defined here to ensure
consistent interfaces between components.  Includes LSE (AutoResearch 2.0)
types: LifeEvent, GapReport, ChartDNA, LSEPrediction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional, TypedDict, Dict


def normalize_planets(planets_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensures that planet data is always in the format {planet: {house: int, ...}}
    Handles legacy entries that might just be {planet: house_int}.
    """
    if not isinstance(planets_data, dict):
        return {}
        
    normalized = {}
    for planet, data in planets_data.items():
        if isinstance(data, (int, float)):
            normalized[planet] = {"house": int(data)}
        elif isinstance(data, dict):
            normalized[planet] = data
        else:
            normalized[planet] = data
            
    return normalized


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
    magnitude: float = 0.0
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


# ---------------------------------------------------------------------------
# AutoResearch 2.0 (LSE) — Life Event Log
# ---------------------------------------------------------------------------

class LifeEvent(TypedDict, total=False):
    """A single known life event supplied by the user for back-testing."""
    age: int            # Age at which the event occurred
    domain: str         # "profession", "health", "marriage", etc.
    description: str    # Free-text description
    is_verified: bool   # True if independently confirmed


# Type alias
LifeEventLog = list[LifeEvent]


# ---------------------------------------------------------------------------
# AutoResearch 2.0 (LSE) — Gap Report (Validator output)
# ---------------------------------------------------------------------------

class GapEntry(TypedDict, total=False):
    """Comparison of one life event vs the engine's prediction."""
    life_event: LifeEvent
    predicted_peak_age: Optional[int]   # None if no prediction matched the domain
    offset: Optional[float]             # predicted - actual (None if no prediction)
    is_hit: bool                        # abs(offset) <= 1.0  (DEC-004)
    matched_prediction_text: str


class GapReport(TypedDict, total=False):
    """Full back-test comparison report produced by ValidatorAgent."""
    entries: list[GapEntry]
    hit_rate: float         # hits / total  (0.0 – 1.0)
    mean_offset: float      # mean abs(offset) across all entries
    total: int
    hits: int
    domain_scores: dict[str, float]  # per-domain hit rates
    domain_fp_counts: dict[str, int] # per-domain false positive counts
    contradictions: list[str]  # events with NO matching prediction domain
    false_positives: list[str] # raw prediction texts that were unused




# ---------------------------------------------------------------------------
# AutoResearch 2.0 (LSE) — Chart DNA (personalised model)
# ---------------------------------------------------------------------------

@dataclass
class ChartDNA:
    """
    Personalised model discovered by LSEOrchestrator for a specific figure.
    Saved to the ``chart_dna`` SQLite table via ChartDNARepository.
    """
    figure_id: str
    back_test_hit_rate: float           # 0.0 – 1.0
    mean_offset_years: float
    iterations_run: int
    delay_constants: dict[str, float] = field(default_factory=dict)
    # e.g. {"delay.mars_h8": 2.5, "delay.sun_h1": -1.0}
    milestone_alignments: dict[str, int] = field(default_factory=dict)
    # e.g. {"align.saturn_h5": 48, "align.rahu_h9": 42}
    grammar_overrides: dict[str, Any] = field(default_factory=dict)
    # e.g. {"grammar.h10_sleeping_cancelled_by_h12_travel": True}
    config_overrides: dict[str, Any] = field(default_factory=dict)
    # Merged view of both (what was set via config.set_override)
    confidence_score: float = 0.0
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def compute_confidence(self, verified_event_ratio: float = 1.0) -> float:
        """
        confidence = hit_rate*0.70 + precision*0.20 + verified*0.10
        precision = 1 - mean_offset/5  (capped at 0..1)
        """
        precision = max(0.0, 1.0 - self.mean_offset_years / 5.0)
        score = (
            self.back_test_hit_rate * 0.70
            + precision * 0.20
            + verified_event_ratio * 0.10
        )
        self.confidence_score = round(min(1.0, score), 4)
        return self.confidence_score


# ---------------------------------------------------------------------------
# AutoResearch 2.0 (LSE) — LSE Prediction (personalised output)
# ---------------------------------------------------------------------------

@dataclass
class LSEPrediction:
    """
    A prediction generated after back-testing. Wraps the standard
    LKPrediction fields and adds personalisation metadata.
    """
    # --- Standard LKPrediction fields (mirrored for type-safety) ---
    domain: str
    event_type: str
    prediction_text: str
    confidence: str
    polarity: str
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
    # --- LSE-specific fields ---
    personalised: bool = True
    chart_dna_applied: Optional[ChartDNA] = None
    raw_peak_age: int = 0       # Before delay constant applied
    adjusted_peak_age: float = 0.0  # After delay constant applied
    confidence_source: str = "generic"
    # Possible values: "back_test_100pct" | "back_test_partial" | "generic"

    @classmethod
    def from_lk_prediction(cls, lk: "LKPrediction", dna: Optional[ChartDNA] = None,
                           delay: float = 0.0) -> "LSEPrediction":
        """Promote a standard LKPrediction into an LSEPrediction."""
        confidence_source = "generic"
        if dna:
            if dna.back_test_hit_rate >= 1.0:
                confidence_source = "back_test_100pct"
            elif dna.back_test_hit_rate > 0.0:
                confidence_source = "back_test_partial"

        raw_age = lk.peak_age
        adj_age = raw_age + delay
        return cls(
            domain=lk.domain,
            event_type=lk.event_type,
            prediction_text=lk.prediction_text,
            confidence=lk.confidence,
            polarity=lk.polarity,
            peak_age=int(adj_age) if delay else lk.peak_age,
            age_window=lk.age_window,
            probability=lk.probability,
            affected_people=lk.affected_people,
            affected_items=lk.affected_items,
            source_planets=lk.source_planets,
            source_houses=lk.source_houses,
            source_rules=lk.source_rules,
            remedy_applicable=lk.remedy_applicable,
            remedy_hints=lk.remedy_hints,
            personalised=dna is not None,
            chart_dna_applied=dna,
            raw_peak_age=raw_age,
            adjusted_peak_age=adj_age,
            confidence_source=confidence_source,
        )


# ---------------------------------------------------------------------------
# AutoResearch 2.0 (LSE) — Solve Result (orchestrator output)
# ---------------------------------------------------------------------------

@dataclass
class LSESolveResult:
    """Returned by LSEOrchestrator.solve_chart()."""
    chart_dna: ChartDNA
    future_predictions: list[LSEPrediction] = field(default_factory=list)
    iterations_run: int = 0
    converged: bool = False
    gap_report: Optional[GapReport] = None  # NEW: Final best gap report

