import json
import os
import logging
import copy
from datetime import datetime
from typing import Dict, List, Any, Optional

from .config import ModelConfig
from .chart_enricher import ChartEnricher
from .astrological_context import UnifiedAstrologicalContext
from .rules_engine import RulesEngine
from .fidelity_shield import FidelityShield
from .contextual_assembler import ContextualAssembler
from .lifecycle_engine import LifecycleEngine
from .synthesis_reporter import SynthesisReporter
from .state_ledger import StateLedger
from .narrative_engine import NarrativeEngine
from .remedy_engine import RemedyEngine
from .varshphal_timing_engine import VarshphalTimingEngine

logger = logging.getLogger(__name__)

class PredictionRunner:
    """
    DEEP MODULE: The central engine for end-to-end Lal Kitab analysis.
    Hides the entire preparation, evaluation, and assembly pipeline.
    Provides persistence of results to disk automatically.
    """

    def __init__(self, config: ModelConfig):
        self.cfg = config
        
        # Instantiate dependencies
        from .grammar_analyser import GrammarAnalyser
        from .strength_engine import StrengthEngine
        
        grammar_analyser = GrammarAnalyser(config)
        strengths = StrengthEngine(config)
        
        self.enricher = ChartEnricher(grammar_analyser.registry, strengths)
        self.rules_engine = RulesEngine(config)
        self.fidelity_gate = FidelityShield()
        
        self.assembler = ContextualAssembler(
            narrative_engine=NarrativeEngine(),
            remedy_engine=RemedyEngine(),
            timing_engine=VarshphalTimingEngine()
        )
        self.lifecycle = LifecycleEngine()
        
        self.output_dir = os.path.join(os.path.dirname(__file__), "..", "..", "output")
        os.makedirs(self.output_dir, exist_ok=True)

    def run_full_lifecycle(self, name: str, dob: str, charts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Executes a 75-year longitudinal analysis and persists the result.
        """
        natal = next((c for c in charts if c.get("chart_type") == "Birth"), charts[0])
        
        # 1. Pre-calculate lifecycle history (StateLedger timeline)
        ledger_history = self.lifecycle.run_75yr_analysis(natal)
        
        # 2. Generate Natal Baseline
        natal_preds, natal_ctx = self._generate_single_chart_predictions(natal, None, StateLedger())
        natal_report = SynthesisReporter.format_chart_section(natal, natal_preds, natal_ctx)

        # 3. Generate Annual Timeline
        timeline = []
        for age in range(1, 76):
            annual = next((c for c in charts if c.get("chart_period") == age), None)
            if not annual:
                continue
                
            try:
                ledger = ledger_history.get(age, StateLedger())
                preds, ctx = self._generate_single_chart_predictions(annual, natal, ledger)
                section = SynthesisReporter.format_chart_section(annual, preds, ctx)
                
                timeline.append({
                    "age": age,
                    "year_of_life": age,
                    "from": annual.get("period_start", ""),
                    "to": annual.get("period_end", ""),
                    **section
                })
            except Exception as e:
                logger.error(f"Error evaluating age {age}: {e}")
                continue

        # 4. Final Synthesis
        full_payload = SynthesisReporter.generate_full_payload(name, dob, natal_report, timeline)
        
        # 5. Persistence
        self._persist_result(name, full_payload)
        
        return full_payload

    def _generate_single_chart_predictions(
        self, 
        chart: Dict[str, Any], 
        natal_chart: Optional[Dict[str, Any]], 
        ledger: StateLedger
    ) -> tuple:
        """Internal pipeline phase."""
        # 1. Enrichment
        enriched = self.enricher.enrich(chart, natal_chart)

        # 2. Context Hydration
        context = UnifiedAstrologicalContext(
            enriched=enriched,
            natal_chart=natal_chart,
            ledger=ledger,
            config=self.cfg
        )

        # 3. Rule Evaluation
        hits = self.rules_engine.evaluate_chart(context)

        # 4. Fidelity Gating
        hits = self.fidelity_gate.evaluate_signals(hits, context)

        # 5. Assembly
        predictions = self.assembler.assemble(rule_hits=hits, context=context)

        return predictions, context

    def _persist_result(self, name: str, payload: Dict[str, Any]):
        """Saves the high-fidelity JSON to the output directory."""
        filename = f"{name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            with open(filepath, "w") as f:
                json.dump(payload, f, indent=2)
            logger.info(f"Persisted analysis for {name} to {filepath}")
        except Exception as e:
            logger.error(f"Failed to persist result for {name}: {e}")
