from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

from .astro_chart import AstroChart
from .data_contracts import ChartData, EnrichedChart


class ChartEnricher:
    """
    The central orchestrator for chart data preparation.
    Encapsulates the 4-phase enrichment sequence:

      1. Masnui Detection (EntanglementModule)
      2. House Status population (AstroChart)
      3. Strength Calculation (StrengthEngine)
      4. Grammar Audit (GrammarRegistry — all 6 modules)

    Exposes internal phases as named methods so each can be tested
    in isolation with constructed inputs.
    """

    def __init__(self, grammar_registry, strength_engine):
        self.registry = grammar_registry
        self.strengths = strength_engine

        # Pre-resolve the EntanglementModule for step-1 Masnui detection.
        from .grammar.modules.entanglement_module import EntanglementModule
        self._entanglement = self.registry.get_module(EntanglementModule)

    # -- public entry point -------------------------------------------------

    def enrich(self, chart: ChartData, natal: Optional[ChartData] = None) -> EnrichedChart:
        """Run all 4 enrichment phases. Returns a typed EnrichedChart."""
        # Phase 1: Masnui virtual planets
        masnuis = self._detect_masnui(chart)

        # Phase 2: House-level status (needs Masnui planets placed)
        house_status = self._compute_house_status(chart, masnuis)

        # Phase 3: Per-planet strengths (aspects + dignity + scapegoat)
        enriched_strengths = self._compute_strengths(chart, natal, house_status)

        # Phase 4: Grammar audit (all 6 modules mutate enriched_strengths)
        grammar_hits = self._run_grammar_audit(chart, enriched_strengths)

        return self._assemble(chart, masnuis, house_status, enriched_strengths, grammar_hits)

    # -- internal phases (independently callable for testing) ----------------

    def _detect_masnui(self, chart: Dict) -> list:
        if self._entanglement:
            self._entanglement.detect(chart)
        return chart.get("masnui_grahas_formed", [])

    def _compute_house_status(self, chart: Dict, masnuis: list) -> dict:
        chart["masnui_grahas_formed"] = masnuis
        astro_chart = AstroChart(chart)
        chart["house_status"] = astro_chart.house_status
        return astro_chart.house_status

    def _compute_strengths(self, chart: Dict, natal: Optional[Dict], house_status: dict) -> dict:
        return self.strengths.calculate_chart_strengths(chart, natal)

    def _run_grammar_audit(self, chart: Dict, enriched: dict) -> dict:
        return self.registry.apply_all(chart, enriched)

    def _assemble(self, chart: Dict, masnuis: list, house_status: dict,
                  strengths: dict, grammar_hits: dict) -> EnrichedChart:
        return EnrichedChart(
            source=chart,
            masnui_planets=list(masnuis),
            house_status=dict(house_status),
            planet_strengths=strengths,
            structural_type=chart.get("structural_type", ""),
            dharmi_kundli_status=chart.get("dharmi_kundli_status", "Inactive"),
            mangal_badh_status=chart.get("mangal_badh_status", "Inactive"),
            debts=list(chart.get("lal_kitab_debts", [])),
            grammar_hits=dict(grammar_hits),
        )
