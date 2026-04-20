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
from astroq.lk_prediction.prediction_translator import PredictionTranslator
from astroq.lk_prediction.data_contracts import ChartData, LKPrediction

logger = logging.getLogger(__name__)

class LKPredictionPipeline:
    """The central orchestrator for core Lal Kitab logic."""

    def __init__(self, config: ModelConfig):
        self.cfg = config
        self.grammar = GrammarAnalyser(config)
        self.strengths = StrengthEngine(config)
        self.rules = RulesEngine(config.get("db_path", fallback="backend/data/rules.db"))
        self.translator = PredictionTranslator(config)
        self.natal_chart: Optional[ChartData] = None

    def load_natal_baseline(self, natal_chart: ChartData):
        """Sets the birth chart background for annual analysis."""
        self.natal_chart = copy.deepcopy(natal_chart)

    def _enrich_chart_data(self, chart: ChartData):
        """Populates house_status and other runtime metadata for the RulesEngine."""
        pd = chart.get("planets_in_houses", {})
        # Initialize all 12 houses as Empty
        status = {str(i): "Empty House" for i in range(1, 13)}
        
        # Mark occupied houses from standard planets
        for p_name, p_info in pd.items():
            h = p_info.get("house")
            if h and 1 <= h <= 12:
                status[str(h)] = "Occupied"
                
        # Also mark occupied from Masnui (Artificial) planets
        for m in chart.get("masnui_grahas_formed", []):
            h = m.get("formed_in_house")
            if h:
                status[str(h)] = "Occupied"
        
        chart["house_status"] = status

    def generate_predictions(self, chart: ChartData) -> List[LKPrediction]:
        """Runs the core prediction loop for a single chart (Natal or Annual)."""
        # 1. Preliminary Enrichment: Detect Masnui planets so they count for House Status
        masnuis = self.grammar.detect_masnui(chart)
        chart["masnui_grahas_formed"] = masnuis
        
        # 2. House Status Enrichment (Critical for RulesEngine and Sleeping Houses)
        self._enrich_chart_data(chart)
        
        # 3. Strength Calculation (provides base aspects)
        enriched = self.strengths.calculate_chart_strengths(chart, self.natal_chart)
        
        # 4. Grammar: Apply remaining rules (Kaayam, Dharmi, etc.)
        self.grammar.apply_grammar_rules(chart, enriched)

        # 5. Attach enriched data to chart so callers can read grammar states
        #    (planet strength, sleeping, kaayam, dharmi, aspects, etc.)
        chart["_enriched"] = enriched

        # 5b. Inject natal positions into chart so rules engine can compute
        #     annual dignity modifiers (Pakka Ghar / Exaltation / Debilitation)
        if self.natal_chart and chart.get("chart_type") == "Yearly":
            chart["_natal_positions"] = {
                p: info.get("house")
                for p, info in self.natal_chart.get("planets_in_houses", {}).items()
                if info.get("house")
            }

        # 6. Rule Evaluation
        rule_hits = self.rules.evaluate_chart(chart)
        
        # 7. Translation
        return self.translator.translate(rule_hits, age=chart.get("chart_period", 0))

    def generate_full_payload(self, name: str, dob: str, charts: List[ChartData]) -> Dict[str, Any]:
        """Generates a clean text-first report for Gemini/NotebookLM."""
        # Find natal chart
        natal = next((c for c in charts if c.get("chart_type") == "Birth"), charts[0])
        self.load_natal_baseline(natal)
        
        def _get_report_section(c: ChartData) -> Dict[str, Any]:
            # 1. Core Logic & Enrichment
            preds = self.generate_predictions(c)
            # Find and extract grammar hits for the logic list
            logic = []
            if c.get("mangal_badh_status") == "Active": logic.append("Mangal Badh: Active (Afflicted Mars)")
            if c.get("dharmi_kundli_status") == "Dharmi Teva": logic.append("Dharmi Teva: Active (Protected Chart)")
            for debt in c.get("lal_kitab_debts", []):
                if debt.get("active"): logic.append(f"Karmic Debt: {debt['debt_name']}")
            for masnui in c.get("masnui_grahas_formed", []):
                logic.append(f"Masnui Formation: {masnui['masnui_graha_name']} in House {masnui['formed_in_house']}")

            # 2. Extract aspects
            aspects = []
            for p, p_data in c.get("planets_in_houses", {}).items():
                for asp in p_data.get("aspects", []):
                    strength_val = f"(Strength: {asp['aspect_strength']:.2f})" if "aspect_strength" in asp else ""
                    aspects.append(f"{p} casts {asp['aspect_type']} on {asp['target']} in House {asp['target_house']} {strength_val}")

            # 3. Compact Positions
            positions = {p: d.get("house", 0) for p, d in c.get("planets_in_houses", {}).items() if p != "Asc"}

            return {
                "chart": positions,
                "logic": sorted(list(set(logic))),
                "significant_aspects": aspects[:15], # Top 15 aspects to prevent bloat
                "predictions": [p.prediction_text for p in preds if p.prediction_text]
            }

        # Generate Annual Timeline
        timeline = []
        for age in range(1, 76):
            annual = next((c for c in charts if c.get("chart_period") == age), None)
            if annual:
                timeline.append({
                    "age": age,
                    "year_of_life": age,
                    "from": annual.get("period_start", ""),
                    "to": annual.get("period_end", ""),
                    **_get_report_section(annual)
                })
        
        return {
            "metadata": {"name": name, "dob": dob, "engine": "2.5-report-optimized"},
            "natal_profile": _get_report_section(natal),
            "annual_timeline": timeline
        }
