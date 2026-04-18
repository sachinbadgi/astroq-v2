"""
Phase 4: LSE Orchestrator (AutoResearch 2.0)

Core iteration loop for back-testing and personalising models.
"""

from __future__ import annotations
import copy
import logging
from pprint import pformat
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from astroq.lk_prediction.pipeline import LKPredictionPipeline
from astroq.lk_prediction.lse_validator import ValidatorAgent
from astroq.lk_prediction.lse_researcher import ResearcherAgent, Hypothesis
from astroq.lk_prediction.data_contracts import (
    ChartData,
    LifeEventLog,
    LSESolveResult,
    ChartDNA,
    LSEPrediction,
    LKPrediction,
)

if TYPE_CHECKING:
    from astroq.lk_prediction.config import ModelConfig


class LSEOrchestrator:
    """
    Orchestrates the back-testing loop (LSE loop).
    """

    def __init__(self, config: ModelConfig):
        self.cfg = config
        self.validator = ValidatorAgent()
        self.researcher = ResearcherAgent(config)

    def solve_chart(
        self,
        birth_chart: ChartData,
        annual_charts: dict[int, ChartData],
        life_event_log: LifeEventLog,
        figure_id: str,
        max_iterations: int = 20
    ) -> LSESolveResult:
        """
        Personalise the prediction model for a specific figure using back-testing.
        """
        # DEC-005: Zero life events -> skip LSE loop
        if not life_event_log:
            final_lk = self._run_pipeline(birth_chart, annual_charts, figure_id)
            dna = ChartDNA(
                figure_id=figure_id,
                back_test_hit_rate=0.0,
                mean_offset_years=0.0,
                iterations_run=0
            )
            return LSESolveResult(
                chart_dna=dna,
                future_predictions=[LSEPrediction.from_lk_prediction(p, dna) for p in final_lk],
                iterations_run=0,
                converged=False
            )

        best_dna: Optional[ChartDNA] = None
        best_hit_rate = -1.0
        best_predictions: list[LKPrediction] = []
        best_gap_report = None
        
        current_overrides: dict[str, Any] = {}
        iterations = 0
        converged = False
        baseline_predictions: list[LKPrediction] = []
        last_grammar_overrides: dict[str, Any] = {}

        while iterations < max_iterations:
            # 1. Run pipeline ONLY if grammar overrides changed or it's the first run
            current_grammars = {k: v for k, v in current_overrides.items() if k.startswith("grammar.")}
            
            if iterations == 0 or current_grammars != last_grammar_overrides:
                # Apply grammar overrides to config
                for key, val in current_grammars.items():
                    self.cfg.set_override(key, val, figure=figure_id, source="lse_iteration")
                
                baseline_predictions = self._run_pipeline(birth_chart, annual_charts, figure_id)
                last_grammar_overrides = copy.deepcopy(current_grammars)
            
            # Apply delay overrides to a copy of baseline predictions for validation
            from dataclasses import replace
            predictions = [replace(p) for p in baseline_predictions]
            for p in predictions:
                for planet in p.source_planets:
                    # Look for alignments or delay constants for this planet
                    for k, v in current_overrides.items():
                        if k.startswith("align.") and planet.lower() in k.lower():
                            # Snap to canonical age
                            p.peak_age = int(v)
                            break
                        if k.startswith("delay.") and planet.lower() in k.lower():
                            p.peak_age += float(v)
                            break

            # 2. Validate
            gap_report = self.validator.compare_to_events(predictions, life_event_log)
            hit_rate = self.validator.compute_hit_rate(gap_report)
            
            # Track best DNA
            if hit_rate > best_hit_rate:
                best_hit_rate = hit_rate
                best_predictions = baseline_predictions
                best_gap_report = gap_report
                
                # Determine current constants from overrides
                delays = {k: v for k, v in current_overrides.items() if k.startswith("delay.")}
                aligns = {k: v for k, v in current_overrides.items() if k.startswith("align.")}
                grammars = {k: v for k, v in current_overrides.items() if k.startswith("grammar.")}
                
                best_dna = ChartDNA(
                    figure_id=figure_id,
                    back_test_hit_rate=hit_rate,
                    mean_offset_years=self.validator.compute_mean_offset(gap_report),
                    iterations_run=iterations,
                    delay_constants=delays,
                    milestone_alignments=aligns,
                    grammar_overrides=grammars,
                    config_overrides=copy.deepcopy(current_overrides)
                )

            # 3. Check convergence
            if hit_rate >= 0.95:
                converged = True
                break

            # 4. Generate next hypothesis
            hypotheses = self.researcher.generate_hypotheses(
                gap_report, birth_chart, life_event_log=life_event_log
            )
            ranked = self.researcher.rank_hypotheses(hypotheses)
            print(f"Iterations: {iterations}, Ranked: {ranked}")
            
            # Choose the next hypothesis that we haven't tried yet
            # In this simple loop, we just take the first one
            if not ranked:
                break
                
            next_hyp = ranked[0]
            # Simple heuristic: if we already have this override, skip or try next
            # (Real impl would be more sophisticated)
            current_overrides[next_hyp["key"]] = next_hyp["value"]
            
            iterations += 1

        # Final cleanup: clear iteration overrides and set the BEST onepermanently
        self.cfg.reset_overrides(figure=figure_id)
        if best_dna:
            for k, v in best_dna.config_overrides.items():
                self.cfg.set_override(k, v, figure=figure_id, source="lse_final")
            
            # Compute confidence score
            verified_ratio = sum(1 for e in life_event_log if e.get("is_verified")) / len(life_event_log)
            best_dna.compute_confidence(verified_ratio)

        # Wrap predictions as LSEPredictions
        final_preds: list[LSEPrediction] = []
        for lk in best_predictions:
            # Find delay constant matching this prediction's source if possible
            # Simplified: just use the sum of delay constants or relevant ones
            # In a real impl, we'd map planet -> delay
            delay = 0.0
            if best_dna:
                # Apply delays surgically: matching planet name in rationale key
                for p_name in lk.source_planets:
                    # Rationale keys are like 'delay.sun_h1'
                    for k, v in best_dna.delay_constants.items():
                        if p_name.lower() in k.lower():
                             # If multiple keys for same planet (e.g. Mercury house mismatch),
                             # we use the first matching one found.
                             delay = v
                             break
                    if delay > 0: break # Found a delay for one of our source planets
            
            final_preds.append(LSEPrediction.from_lk_prediction(lk, best_dna, delay=delay))

        return LSESolveResult(
            chart_dna=best_dna,
            future_predictions=final_preds,
            iterations_run=iterations,
            converged=converged,
            gap_report=best_gap_report
        )


    def _run_pipeline(
        self, birth_chart: ChartData, annual_charts: dict[int, ChartData], figure_id: str
    ) -> list[LKPrediction]:
        """Helper to run the pipeline for a set of charts."""
        pipeline = LKPredictionPipeline(self.cfg)
        pipeline.load_natal_baseline(birth_chart)
        
        all_preds = []
        # Support both natal-only and annual-sequence runs
        # Sort annuals by age
        for age in sorted(annual_charts.keys()):
            annual = annual_charts[age]
            preds = pipeline.generate_predictions(annual)
            all_preds.extend(preds)
            
        return all_preds
