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

from astroq.lk_prediction.narrative_engine import NarrativeEngine
from astroq.lk_prediction.remedy_engine import RemedyEngine
from astroq.lk_prediction.varshphal_timing_engine import VarshphalTimingEngine

logger = logging.getLogger(__name__)

class LKPredictionPipeline:
    """The central orchestrator for core Lal Kitab logic."""

    def __init__(self, config: ModelConfig):
        self.cfg = config
        self.grammar = GrammarAnalyser(config)
        self.strengths = StrengthEngine(config)
        self.rules = RulesEngine(config)
        
        # Instantiate dependencies for the ContextualAssembler
        self.narrative = NarrativeEngine()
        self.remedies = RemedyEngine()
        self.timing_engine = VarshphalTimingEngine()
        
        self.assembler = ContextualAssembler(
            narrative_engine=self.narrative,
            remedy_engine=self.remedies,
            timing_engine=self.timing_engine
        )
        self.lifecycle = LifecycleEngine()
        # Deep Module: ChartEnricher now handles both Grammar and Strengths coordination
        self.enricher = ChartEnricher(self.grammar, self.strengths)
        self.natal_chart: Optional[ChartData] = None
        self.ledger_history: Dict[int, Any] = {}

    def load_natal_baseline(self, natal_chart: ChartData):
        """Sets the birth chart background for annual analysis and pre-calculates lifecycle history."""
        self.natal_chart = copy.deepcopy(natal_chart)
        
        # Pre-pave the 75-year forensic lifecycle
        self.ledger_history = self.lifecycle.run_75yr_analysis(natal_chart)

    def generate_predictions(self, chart: ChartData, focus_domains: Optional[List[str]] = None) -> List[LKPrediction]:
        """Runs the core prediction loop using a Deep Module Context."""
        if chart.get("chart_type") == "Yearly" and not self.natal_chart:
            raise ValueError("Annual analysis requires a loaded natal baseline.")

        age = chart.get("chart_period", 0)
        
        # 1. Enrichment (Grammar, Strengths, Masnui)
        # DEEP MODULE: The pipeline now uses a single unified enrichment call.
        # It no longer needs to know the internal sequence of Grammar vs Strength.
        self.enricher.enrich_chart(chart, self.natal_chart)

        # 2. Hydrate Context (The Deep Module interface)
        # M-5 FIX: For Birth charts, use a fresh StateLedger so that 75-year lifecycle
        # trauma accumulated by LifecycleEngine never contaminates natal analysis.
        # Annual charts use the pre-computed ledger snapshot for that age.
        if self.natal_chart and chart.get("chart_type") == "Yearly":
            year_ledger = self.ledger_history.get(age)
        else:
            year_ledger = StateLedger()
        
        context = UnifiedAstrologicalContext(
            chart=chart, 
            natal_chart=self.natal_chart, 
            ledger=year_ledger,
            config=self.cfg
        )

        # 3. Rule Evaluation
        rule_hits = self.rules.evaluate_chart(context)
        
        # 4. Synthesis
        predictions = self.assembler.assemble(rule_hits=rule_hits, context=context)

        # 5. Domain Filtering
        if focus_domains:
            focus_lower = [d.lower() for d in focus_domains]
            predictions = [
                p for p in predictions 
                if p.domain.lower() in focus_lower 
                or any(d.lower() in focus_lower for d in getattr(p, "domains", []))
                or any(item.lower() in focus_lower for item in p.affected_items)
            ]

        return predictions

    def generate_full_payload(self, name: str, dob: str, charts: List[ChartData]) -> Dict[str, Any]:
        """Delegates report generation to the SynthesisReporter."""
        natal = next((c for c in charts if c.get("chart_type") == "Birth"), charts[0])
        self.load_natal_baseline(natal)
        
        # Generate Natal Report
        natal_preds = self.generate_predictions(natal)
        natal_report = SynthesisReporter.format_chart_section(natal, natal_preds)

        # Generate Annual Timeline
        timeline = []
        for age in range(1, 76):
            annual = next((c for c in charts if c.get("chart_period") == age), None)
            if annual:
                preds = self.generate_predictions(annual)
                section = SynthesisReporter.format_chart_section(annual, preds)
                timeline.append({
                    "age": age,
                    "year_of_life": age,
                    "from": annual.get("period_start", ""),
                    "to": annual.get("period_end", ""),
                    **section
                })
        
        return SynthesisReporter.generate_full_payload(name, dob, natal_report, timeline)
