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
        self._natal_rule_signatures: set[tuple] = set()
        
        # Maps (planet, event_type/rule) to last year's probability for momentum
        self._prediction_history: dict[str, float] = {}

    def load_natal_baseline(self, chart: ChartData) -> None:
        """Process natal chart and cache baseline strengths and rule signatures."""
        if chart.get("chart_type", "Birth") != "Birth":
            pass # Usually enforcing but can be flexible
            
        strengths = self.strength_engine.calculate_chart_strengths(chart)
        enriched = dict(strengths)
        self.grammar_analyser.apply_grammar_rules(chart, enriched)
        
        # Rules Context for Natal Baseline
        planets_data = self._build_rules_context(enriched, chart)
        birth_hits = self.rules_engine.evaluate_chart({"planets_in_houses": planets_data})
        
        self._natal_rule_signatures = set()
        for h in birth_hits:
            # signature: (rule_id, target_planets, target_houses)
            sig = (h.rule_id, tuple(sorted(h.primary_target_planets)), tuple(sorted(h.target_houses)))
            self._natal_rule_signatures.add(sig)

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
        natal_chart = self._natal_chart_meta if is_annual else None
        raw_strengths = self.strength_engine.calculate_chart_strengths(chart, natal_chart=natal_chart)
        
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
        planets_data = self._build_rules_context(enriched, chart)
        rule_hits = self.rules_engine.evaluate_chart({"planets_in_houses": planets_data})
        
        # Filtering: Remove natal promise hits for annual timing
        if is_annual and self._natal_rule_signatures:
            timing_hits = []
            for h in rule_hits:
                sig = (h.rule_id, tuple(sorted(h.primary_target_planets)), tuple(sorted(h.target_houses)))
                if sig not in self._natal_rule_signatures:
                    timing_hits.append(h)
            rule_hits = timing_hits

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

    def generate_domain_scores(
        self, chart: ChartData, focus_domains: list[str] | None = None
    ) -> dict[str, float]:
        """
        Calculates domain-level scores using the 'Steve Jobs Audit' logic.
        Isolates dynamic annual signals from natal promises and returns max scores per domain.
        """
        is_annual = chart.get("chart_type", "Birth") == "Yearly"
        age = chart.get("chart_period", 0)
        
        # 1. Base Strengths & Grammar (Standard)
        natal_chart = self._natal_chart_meta if is_annual else None
        raw_strengths = self.strength_engine.calculate_chart_strengths(chart, natal_chart=natal_chart)
        if is_annual and self._natal_baseline:
            raw_strengths = self.strength_engine.merge_natal_annual(
                natal=self._natal_baseline, annual=raw_strengths
            )
        
        enriched = dict(raw_strengths)
        self.grammar_analyser.apply_grammar_rules(chart, enriched)
        planets_data = self._build_rules_context(enriched, chart)
        
        # 2. Rule Hits
        # We wrap the enriched planets back into a chart-like dict for the RulesEngine
        chart_for_rules = chart.copy()
        chart_for_rules["planets_in_houses"] = planets_data
        rule_hits = self.rules_engine.evaluate_chart(chart_for_rules)
        
        # 3. Filter Natal Signatures
        if is_annual and self._natal_rule_signatures:
            timing_hits = []
            for h in rule_hits:
                sig = (h.rule_id, tuple(sorted(h.primary_target_planets)), tuple(sorted(h.target_houses)))
                if sig not in self._natal_rule_signatures:
                    timing_hits.append(h)
            rule_hits = timing_hits
            
        # 4. Group by Planet/House for Enriched Events
        # We start with the actual rule hits
        planet_hits = {}
        for h in rule_hits:
            p_name = h.primary_target_planets[0] if h.primary_target_planets else "General"
            h_num = h.target_houses[0] if h.target_houses else 0
            key = (p_name, h_num)
            if key not in planet_hits:
                planet_hits[key] = {
                    "planet": p_name, "house": h_num, "rule_hits": [], 
                    "annual_magnitude": 0.0, "final_probability": 0.0
                }
            planet_hits[key]["rule_hits"].append(h)
            planet_hits[key]["annual_magnitude"] += h.magnitude

        # FALLBACK: If a planet has significant strength but no rules hit, include it as a signal
        for planet, ep in enriched.items():
            h_num = ep.get("house", 0)
            key = (planet, h_num)
            if key not in planet_hits:
                # Same threshold as generate_predictions: abs(strength) >= 2.0
                strength = ep.get("strength_total", 0.0)
                if abs(strength) >= 2.0:
                    planet_hits[key] = {
                        "planet": planet, "house": h_num, "rule_hits": [],
                        "annual_magnitude": strength / 10.0, # Small base signal
                        "final_probability": 0.0
                    }

        # 5. Convert to Classifiable Events using Simple Sigmoid
        raw_events = []
        for key, data in planet_hits.items():
            mag = data["annual_magnitude"]
            # Use the new simple probability method
            data["final_probability"] = self.prob_engine.calculate_simple_probability(mag, k=1.2)
            # CRITICAL: Re-add rule_hits to data so classifier can find domains!
            # (Matches generate_predictions logic)
            raw_events.append(data)
            
        classified = self.classifier.classify_events(raw_events, age=age)
        
        # 6. Aggregate by Domain
        domain_scores = {}
        for ce in classified:
            # If no domains were mapped, event will have [] which fails the loop
            for d in ce.domains:
                if focus_domains and d not in focus_domains:
                    continue
                # Use absolute magnitude for peak detection parity, 
                # but return probability for score tracking
                if d not in domain_scores or ce.probability > domain_scores[d]:
                    domain_scores[d] = ce.probability
                    
        return domain_scores

    def generate_llm_payload(
        self, natal_chart: ChartData, annual_charts: dict[int, ChartData]
    ) -> dict[str, Any]:
        """
        Generates a structured payload specifically for an LLM (Gemini) to correlate
        natal promises with annual fulfillments.
        """
        # 1. Reset and load natal baseline
        self.load_natal_baseline(natal_chart)
        natal_scores = self.generate_domain_scores(natal_chart)
        
        # Capture natal rule descriptions for context
        natal_rules = []
        planets_data = self._build_rules_context(self._natal_baseline, natal_chart)
        birth_hits = self.rules_engine.evaluate_chart({"planets_in_houses": planets_data})
        for h in birth_hits:
            natal_rules.append({
                "rule": h.description,
                "planets": h.primary_target_planets,
                "domain": h.domain
            })

        # 2. Process annual charts
        timeline = []
        for age, chart in sorted(annual_charts.items()):
            domain_scores = self.generate_domain_scores(chart)
            
            # Find which rules hit this year (dynamic only)
            annual_rules = []
            is_annual = chart.get("chart_type", "Birth") == "Yearly"
            
            # Re-run rule engine for this chart with filtering
            natal_chart = self._natal_chart_meta if is_annual else None
            raw_strengths = self.strength_engine.calculate_chart_strengths(chart, natal_chart=natal_chart)
            if is_annual and self._natal_baseline:
                raw_strengths = self.strength_engine.merge_natal_annual(natal=self._natal_baseline, annual=raw_strengths)
            enriched = dict(raw_strengths)
            self.grammar_analyser.apply_grammar_rules(chart, enriched)
            planets_data = self._build_rules_context(enriched, chart)
            chart_for_rules = chart.copy()
            chart_for_rules["planets_in_houses"] = planets_data
            all_hits = self.rules_engine.evaluate_chart(chart_for_rules)
            
            timing_hits = []
            if self._natal_rule_signatures:
                for h in all_hits:
                    sig = (h.rule_id, tuple(sorted(h.primary_target_planets)), tuple(sorted(h.target_houses)))
                    if sig not in self._natal_rule_signatures:
                        timing_hits.append(h)
            
            for h in timing_hits:
                annual_rules.append({
                    "rule": h.description,
                    "planets": h.primary_target_planets,
                    "domain": h.domain,
                    "magnitude": h.magnitude
                })

            timeline.append({
                "age": age,
                "year_of_life": age + 1,
                "start_date": chart.get("period_start"),
                "end_date": chart.get("period_end"),
                "domain_scores": domain_scores,
                "planets_in_houses": {
                    p: {
                        "house": d["house"],
                        "states": d.get("states", [])
                    } for p, d in planets_data.items()
                },
                "achanak_chot_triggers": chart.get("achanak_chot_triggers", []),
                "dynamic_rule_activations": annual_rules
            })

        return {
            "natal_promise_baseline": {
                "domain_scores": natal_scores,
                "planets_in_houses": {p: d["house"] for p, d in self._natal_baseline.items()},
                "key_rule_signatures": natal_rules
            },
            "annual_fulfillment_timeline": timeline
        }

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
