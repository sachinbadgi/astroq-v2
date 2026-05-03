"""
Module 9: Simplified Lal Kitab Prediction Pipeline

Core orchestrator that:
1. Ingests astronomical chart data.
2. Enriches it with Lal Kitab Grammar and planetary Strengths.
3. Evaluates all canonical rules in the database.
4. Translates results into NotebookLM-ready payloads.
"""

import copy
import logging
from typing import Dict, List, Any, Optional

from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.grammar_analyser import GrammarAnalyser
from astroq.lk_prediction.strength_engine import StrengthEngine
from astroq.lk_prediction.rules_engine import RulesEngine
from astroq.lk_prediction.contextual_assembler import ContextualAssembler
from astroq.lk_prediction.data_contracts import ChartData, LKPrediction
from astroq.lk_prediction.lifecycle_engine import LifecycleEngine
from astroq.lk_prediction.chart_enricher import ChartEnricher
from astroq.lk_prediction.astrological_context import UnifiedAstrologicalContext
from astroq.lk_prediction.synthesis_reporter import SynthesisReporter
from astroq.lk_prediction.state_ledger import StateLedger
from astroq.lk_prediction.fidelity_shield import FidelityShield
from .tracer import trace_hit

from astroq.lk_prediction.narrative_engine import NarrativeEngine
from astroq.lk_prediction.remedy_engine import RemedyEngine
from astroq.lk_prediction.varshphal_timing_engine import VarshphalTimingEngine

logger = logging.getLogger(__name__)

class LKPredictionPipeline:
    """The central orchestrator for core Lal Kitab logic. Now a thin wrapper around PredictionRunner."""

    def __init__(self, config: ModelConfig):
        self.cfg = config
        from .prediction_runner import PredictionRunner
        self.runner = PredictionRunner(config)
        self.natal_chart: Optional[ChartData] = None

    def load_natal_baseline(self, natal_chart: ChartData):
        """Sets the birth chart background."""
        self.natal_chart = copy.deepcopy(natal_chart)

    def generate_predictions(self, chart: ChartData, focus_domains: Optional[List[str]] = None) -> Any:
        trace_hit("lk_prediction_pipeline_lkpredictionpipeline_generate_predictions")
        """Runs the core prediction loop using PredictionRunner."""
        if chart.get("chart_type") == "Yearly" and not self.natal_chart:
            raise ValueError("Annual analysis requires a loaded natal baseline.")

        # Re-using the runner's internal pipeline logic for single charts
        preds, ctx = self.runner._generate_single_chart_predictions(
            chart, 
            self.natal_chart, 
            StateLedger() # Default ledger for single-chart ad-hoc requests
        )

        # Domain Filtering
        if focus_domains:
            focus_lower = [d.lower() for d in focus_domains]
            preds = [
                p for p in preds 
                if p.domain.lower() in focus_lower 
                or any(d.lower() in focus_lower for d in getattr(p, "domains", []))
                or any(item.lower() in focus_lower for item in p.affected_items)
            ]

        return preds, ctx

    def generate_full_payload(self, name: str, dob: str, charts: List[ChartData]) -> Dict[str, Any]:
        trace_hit("lk_prediction_pipeline_lkpredictionpipeline_generate_full_payload")
        """Delegates lifecycle analysis and persistence to PredictionRunner."""
        return self.runner.run_full_lifecycle(name, dob, charts)

