"""
Module 8: Pipeline Integration.

The main orchestrator. Glues together StrengthEngine, GrammarAnalyser,
RulesEngine, ProbabilityEngine, EventClassifier, and PredictionTranslator.
Maintains state for historical charts to enable momentum peak detection.
"""

from __future__ import annotations

from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.data_contracts import ChartData, EnrichedPlanet, LKPrediction
from astroq.lk_prediction.event_classifier import EventClassifier
from astroq.lk_prediction.grammar_analyser import GrammarAnalyser
from astroq.lk_prediction.prediction_translator import PredictionTranslator
from astroq.lk_prediction.probability_engine import ProbabilityEngine
from astroq.lk_prediction.rules_engine import RulesEngine
from astroq.lk_prediction.strength_engine import StrengthEngine
from astroq.lk_prediction.remedy_engine import RemedyEngine
from astroq.lk_prediction.items_resolver import LKItemsResolver

class LKPredictionPipeline:
    """Main entrypoint for Lal Kitab Prediction Engine."""

    def __init__(self, config: ModelConfig) -> None:
        self.cfg = config
        
        # Instantiate engines
        self.strength_engine = StrengthEngine(config)
        self.grammar_analyser = GrammarAnalyser(config)
        self.rules_engine = RulesEngine(config)
        self.prob_engine = ProbabilityEngine(config)
        self.classifier = EventClassifier(config)
        self.remedy_engine = RemedyEngine(config, LKItemsResolver())
        self.translator = PredictionTranslator(config, remedy_engine=self.remedy_engine)
        
        # State
        self._natal_baseline: dict[str, EnrichedPlanet] | None = None
        self._natal_chart_meta: dict | None = None
        
        # Maps (planet, event_type/rule) to last year's probability for momentum
        self._prediction_history: dict[str, float] = {}

    def load_natal_baseline(self, chart: ChartData) -> None:
        """Process natal chart and cache baseline strengths."""
        if chart.get("chart_type", "Birth") != "Birth":
            pass # Usually enforcing but can be flexible
            
        strengths = self.strength_engine.calculate_chart_strengths(chart)
        enriched = dict(strengths)
        self.grammar_analyser.apply_grammar_rules(chart, enriched)
        
        self._natal_baseline = enriched
        self._natal_chart_meta = chart

    def generate_predictions(
        self, chart: ChartData, focus_domains: list[str] | None = None
    ) -> list[LKPrediction]:
        """
        Process a chart (Natal or Annual) through the full pipeline.
        Stateful: call sequentially by year for accurate momentum peaks.
        
        Parameters
        ----------
        chart : ChartData
            The chart to process.
        focus_domains : list[str] | None
            Optional list of domains to filter (e.g., ["Career", "Health"]).
            If None, returns all.
            
        Returns
        -------
        list[LKPrediction]
            The translated final predictions.
        """
        is_annual = chart.get("chart_type", "Birth") == "Yearly"
        age = chart.get("chart_period", 0)
        
        if is_annual and not self._natal_baseline:
            raise ValueError("Cannot process yearly chart without a loaded natal baseline.")
            
        # 1. Base Strengths
        raw_strengths = self.strength_engine.calculate_chart_strengths(chart)
        
        # 2. Additive Merge for Annual Maps
        if is_annual and self._natal_baseline:
            merged = self.strength_engine.merge_natal_annual(
                natal=self._natal_baseline, annual=raw_strengths
            )
            raw_strengths = merged
            
        # 3. Grammar Analyser
        enriched = dict(raw_strengths)
        self.grammar_analyser.apply_grammar_rules(chart, enriched)
        
        # Format for Rules Engine: Rules require dict with `house`, `aspects`, `states` etc.
        # But RulesEngine looks for planets_data. We can map `enriched` to a dict format.
        planets_data = self._build_rules_context(enriched, chart)
        
        # 4. Rules Engine Evaluation
        # evaluate_chart expects the full chart, but RulesEngine implementation uses:
        # chart.get("planets_in_houses") inside evaluate_chart.
        # So we must wrap planets_data in a dictionary.
        rule_hits = self.rules_engine.evaluate_chart({"planets_in_houses": planets_data})
        
        # Group hits by planet (primary target)
        hits_by_planet = {}
        for hit in rule_hits:
            for p in hit.primary_target_planets:
                if p not in hits_by_planet:
                    hits_by_planet[p] = []
                hits_by_planet[p].append(hit)
                
        # 5. Prepare Event Triggers for Probability Engine
        events_to_eval = []
        for planet, ep in enriched.items():
            # Summarise magnitudes from rules
            p_hits = hits_by_planet.get(planet, [])
            
            # If no rules fired and config implies ignore empty -> skip
            # Or we let base strength define magnitude.
            annual_mag = sum(h.magnitude for h in p_hits)
            if not p_hits and annual_mag == 0.0:
                 # Minimal fallback if we want base strength to cause events?
                 # Lal Kitab relies heavily on deterministic rules to trigger events.
                 if abs(ep.get("strength_total", 0.0)) < 2.0:
                     continue
                 annual_mag = ep.get("strength_total", 0.0) / 10.0 # Small base
            
            natal_score = 0.0
            if self._natal_baseline and planet in self._natal_baseline:
                natal_score = self._natal_baseline[planet].get("strength_total", 0.0)
            elif not is_annual:
                natal_score = ep.get("strength_total", 0.0)

            # Look up history
            hist_key = f"{planet}_{age}" # unique enough for simple mock pipeline
            prob_t_minus_1 = self._prediction_history.get(f"{planet}_prev")
            
            ev_dict = {
                "planet": planet,
                "house": ep.get("house", 0),
                "magnitude": annual_mag,
                "annual_magnitude": annual_mag, # duplicate for alias
                "natal_score": natal_score,
                "prob_t_minus_1": prob_t_minus_1,
                "rule_hits": p_hits
            }
            events_to_eval.append(ev_dict)

        # 6. Evaluate Probabilities
        prob_results = self.prob_engine.batch_evaluate(events_to_eval, age)
        
        # Update history state
        for res in prob_results:
            p = res.get("planet")
            fpr = res.get("final_probability", 0.0)
            self._prediction_history[f"{p}_prev"] = fpr
            
        # 7. Classification
        classified = self.classifier.classify_events(prob_results, age=age)
        
        # 8. Domain Filter
        if focus_domains:
            lower_focus = [d.lower() for d in focus_domains]
            filtered = []
            for ce in classified:
                # If any of the event domains match the focus domains
                if any(d.lower() in lower_focus for d in ce.domains):
                    filtered.append(ce)
            classified = filtered

        # 9. Translation
        if self._natal_chart_meta:
            wrap_natal = self._natal_chart_meta.copy()
            wrap_natal["planets_in_houses"] = self._natal_baseline
        else:
            wrap_natal = {"planets_in_houses": self._natal_baseline} if self._natal_baseline else None
            
        wrap_annual = {"planets_in_houses": enriched}
        
        final_predictions = self.translator.translate(
            classified,
            enriched_natal=wrap_natal,
            enriched_annual=wrap_annual
        )
        
        return final_predictions

    def _build_rules_context(
        self, enriched: dict[str, EnrichedPlanet], chart: ChartData
    ) -> dict[str, Any]:
        """Convert EnrichedPlanet -> standard dictionary format for JSON RulesEngine."""
        out = {}
        for planet, ep in enriched.items():
            # Original chart stuff
            original_p = chart.get("planets_in_houses", {}).get(planet, {})
            
            p_dict = {
                "house": ep.get("house", 0),
                "aspects": original_p.get("aspects", []),
                "states": original_p.get("states", []),
                # Merge enriched states
                "sleeping_status": ep.get("sleeping_status", "Awake"),
                "dharmi_status": ep.get("dharmi_status", "None"),
                "strength_total": ep.get("strength_total", 0.0)
            }
            out[planet] = p_dict
        return out
