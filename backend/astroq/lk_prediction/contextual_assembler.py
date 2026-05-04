import json
import os
import logging
from typing import List, Dict, Any, Optional
from .data_contracts import RuleHit, LKPrediction, ChartData
from .state_ledger import StateLedger
from .remedy_engine import RemedyEngine
from .varshphal_timing_engine import VarshphalTimingEngine
from .doubtful_timing_engine import DoubtfulTimingEngine
from .timing_engine_protocol import TimingEngineRouter
from .lk_constants import PLANET_HOUSE_ITEMS, PLANET_RELATIVES
from .astrological_context import UnifiedAstrologicalContext

logger = logging.getLogger(__name__)

DOMAIN_WEIGHTS = {
    "Health": 1.5,
    "Marriage": 1.4,
    "Progeny": 1.3,
    "Money": 1.2,
    "Property": 1.1,
    "General": 1.0
}



class GravityScorer:
    """Helper to calculate the impact magnitude of a rule hit."""

    @staticmethod
    def calculate_score(hit: RuleHit, planet_state: Any) -> float:
        # M-3 FIX: Do NOT apply a state_multiplier for Startled here.
        # hit.magnitude already has the Startled recoil folded in by
        # UnifiedAstrologicalContext.calculate_rule_magnitude (step 5).
        # Multiplying again would double the effect for every Startled planet.
        base_strength = abs(hit.magnitude)
        domain_weight = DOMAIN_WEIGHTS.get(hit.domain, 1.0)
        return base_strength * domain_weight

from .narrative_engine import NarrativeEngine

class ContextualAssembler:
    """
    DEEP MODULE: The central interpretative layer of the Lal Kitab Prediction Engine.
    Hides the complexity of:
    1. Gravity scoring (Magnitude * State * Domain).
    2. Narrative assembly (Delegated to NarrativeEngine).
    3. Timing Analysis: routes to VarshphalTimingEngine (GRAHA_PHAL) or
       DoubtfulTimingEngine (RASHI_PHAL) via TimingEngineRouter.
    4. Remedy coordination.
    """

    def __init__(
        self,
        narrative_engine: Optional[NarrativeEngine] = None,
        remedy_engine: Optional[RemedyEngine] = None,
        timing_engine: Optional[VarshphalTimingEngine] = None
    ):
        self.narrative = narrative_engine or NarrativeEngine()
        self.remedies = remedy_engine or RemedyEngine()
        # Primary adapter: Graha Phal (Fixed Fate) timing
        self.varshphal_engine = timing_engine or VarshphalTimingEngine()
        # Secondary adapter: Rashi Phal (Doubtful Fate) timing
        self.doubtful_engine = DoubtfulTimingEngine()

    def assemble(
        self,
        rule_hits: List[RuleHit],
        context: UnifiedAstrologicalContext = None,
        **kwargs
    ) -> List[LKPrediction]:
        """
        Assembles rule hits into high-fidelity predictions with timing and remedies.

        Backward-compatible: also accepts old-style (chart=..., ledger=...) kwargs.
        """
        # Backward compat: auto-wrap old-style chart + ledger
        if context is None:
            from .data_contracts import EnrichedChart
            chart = kwargs.get("chart", {})
            ledger = kwargs.get("ledger", StateLedger())
            context = UnifiedAstrologicalContext(
                enriched=EnrichedChart(source=chart),
                ledger=ledger,
            )

        predictions = []
        for hit in rule_hits:
            # 1. Resolve State from Context
            primary_planet = hit.primary_target_planets[0] if hit.primary_target_planets else "Jupiter"
            p_state = context.get_planet_ledger_state(primary_planet)
            recoil_mult = context.get_recoil_multiplier(primary_planet)
            
            # 2. Gravity Score (Extracted to Deep Helper)
            # Magnitude already includes recoil from the Context calculation
            gravity_score = GravityScorer.calculate_score(hit, p_state) 
            
            # 3. Narrative Assembly (DEEP MODULE: Delegation to NarrativeEngine)
            prediction_text = self.narrative.assemble_narrative(
                hit_description=hit.description,
                domain=hit.domain,
                target_houses=hit.target_houses,
                magnitude=hit.magnitude,
                state_modifier=p_state.modifier
            )
            
            # 4. Final Prediction Object
            p = LKPrediction(
                domain=hit.domain,
                event_type=hit.rule_id,
                prediction_text=prediction_text,
                polarity="MALEFIC" if hit.magnitude < 0 else "BENEFIC",
                peak_age=context.age,
                magnitude=hit.magnitude,
                gravity_score=gravity_score,
                forensic_proof=f"[{hit.rule_id}] {hit.description} (Recoil Applied)",
                source_planets=hit.primary_target_planets,
                source_houses=hit.target_houses,
                source_rules=[hit.rule_id],
                visual_manifest=self._generate_visual_manifest(hit, p_state.modifier),
                afflicts_living=hit.afflicts_living
            )
            
            # 5. Enrich with Relatives/Items
            self._enrich_physical_markers(p)
            
            # 6. Remedy Coordination
            self._coordinate_remedies(p, context)
                
            # 7. Timing Analysis (DEEP MODULE: Delegation to TimingEngine)
            if context.natal_chart and context.chart_type == "Yearly":
                self._apply_timing_analysis(p, context)
            
            predictions.append(p)

        # Final sort by gravity (highest impact first)
        predictions.sort(key=lambda x: x.gravity_score, reverse=True)
        return predictions

    def _coordinate_remedies(self, p: LKPrediction, context: UnifiedAstrologicalContext):
        current_positions = {pl: context.get_house(pl) for pl in context.chart.planets}
        remedy_hints = self.remedies.get_remedies_for_prediction(p, context.ledger, current_positions)
        if remedy_hints:
            p.remedy_hints.extend(remedy_hints)
            p.remedy_applicable = True

    def _generate_visual_manifest(self, hit: RuleHit, state_modifier: str) -> Dict[str, Any]:
        is_malefic = hit.magnitude < 0
        intensity = abs(hit.magnitude)
        
        manifest = {
            "icon": "fracture_bolt" if is_malefic and intensity > 1.2 else "activity_pulse",
            "color_grade": "amber_alert" if is_malefic and intensity > 1.0 else "neutral_gray",
            "friction_intensity": intensity if is_malefic else 0.0,
            "momentum_vector": intensity if not is_malefic else -intensity * 0.5,
            "vibration_frequency": "high" if "Startled" in state_modifier else "stable"
        }
        
        if not is_malefic:
            manifest["icon"] = "momentum_arrow"
            manifest["color_grade"] = "emerald_growth" if intensity > 1.0 else "soft_green"
            
        return manifest

    def _enrich_physical_markers(self, p: LKPrediction):
        """Maps planets and houses to relatives and items."""
        for planet in p.source_planets:
            for house in p.source_houses:
                rel = PLANET_RELATIVES.get(planet, {}).get(house)
                if rel: p.affected_people.extend(rel.split("/"))
                p.affected_items.extend(PLANET_HOUSE_ITEMS.get(planet, {}).get(house, []))
        
        p.affected_people = sorted(list(set([x for x in p.affected_people if x])))

    def _apply_timing_analysis(
        self,
        p: LKPrediction,
        context: UnifiedAstrologicalContext
    ):
        # Route to the correct timing adapter based on fate_type.
        # GRAHA_PHAL → VarshphalTimingEngine  (geometric Goswami triggers)
        # RASHI_PHAL → DoubtfulTimingEngine   (promise resolution)
        fate_type = context.get_fate_type_for_domain(p.domain)
        timing_result = TimingEngineRouter.route_and_call(
            fate_type=fate_type,
            varshphal_engine=self.varshphal_engine,
            doubtful_engine=self.doubtful_engine,
            context=context,
            domain=p.domain.lower(),
            age=context.age or 0,
        )

        p.timing_confidence = timing_result["confidence"]

        if timing_result.get("prohibited"):
            p.timing_signals.append(f"PROHIBITED: {timing_result['reason']}")
            p.gravity_score *= 0.1 # Severely reduce gravity if prohibited

        if timing_result.get("friction_signal"):
            p.timing_signals.append(timing_result["friction_signal"])

        for t in timing_result.get("triggers", []): p.timing_signals.append(f"TIMING TRIGGER: {t}")
        for w in timing_result.get("warnings", []): p.timing_signals.append(f"WARNING: {w}")
