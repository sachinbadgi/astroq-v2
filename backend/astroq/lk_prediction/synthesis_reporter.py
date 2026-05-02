import logging
from typing import Dict, List, Any
from .data_contracts import ChartData, LKPrediction

logger = logging.getLogger(__name__)

class SynthesisReporter:
    """
    DEEP MODULE: Handles the translation of astrological predictions into 
    clean, narrative reports for LLMs (Gemini/NotebookLM).
    """

    @staticmethod
    def generate_full_payload(
        name: str, 
        dob: str, 
        natal_report: Dict[str, Any], 
        timeline: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Final assembly of the multi-year forensic payload."""
        return {
            "metadata": {
                "name": name, 
                "dob": dob, 
                "engine": "2.5-deep-module-optimized"
            },
            "natal_profile": natal_report,
            "annual_timeline": timeline
        }

    @staticmethod
    def format_chart_section(
        chart: ChartData, 
        predictions: List[LKPrediction]
    ) -> Dict[str, Any]:
        """Formats a single chart's predictions and logic into a report section."""
        
        # 1. Extract logic markers
        logic = []
        if chart.get("mangal_badh_status") == "Active": 
            logic.append("Mangal Badh: Active (Afflicted Mars)")
        if chart.get("dharmi_kundli_status") == "Dharmi Teva": 
            logic.append("Dharmi Teva: Active (Protected Chart)")
            
        for debt in chart.get("lal_kitab_debts", []):
            if debt.get("active"): 
                logic.append(f"Karmic Debt: {debt['debt_name']}")
                
        for masnui in chart.get("masnui_grahas_formed", []):
            logic.append(f"Masnui Formation: {masnui['masnui_graha_name']} in House {masnui['formed_in_house']}")

        # 2. Extract aspects
        aspects = []
        for p, p_data in chart.get("planets_in_houses", {}).items():
            for asp in p_data.get("aspects", []):
                strength_val = f"(Strength: {asp['aspect_strength']:.2f})" if "aspect_strength" in asp else ""
                aspects.append(f"{p} casts {asp['aspect_type']} on {asp['target']} in House {asp['target_house']} {strength_val}")

        # 3. Compact Positions
        positions = {
            p: d.get("house", 0) 
            for p, d in chart.get("planets_in_houses", {}).items() 
            if p != "Asc"
        }

        # 4. Format Prediction Strings
        formatted_preds = []
        for p in predictions:
            if not p.prediction_text: continue
            
            text = f"[{p.timing_confidence.upper()}] {p.prediction_text}" if p.timing_confidence else p.prediction_text
            
            if p.timing_signals:
                text += " " + " ".join(p.timing_signals)
            
            if p.remedy_hints:
                text += " | REMEDY: " + " ".join(p.remedy_hints)
                
            formatted_preds.append(text)

        return {
            "chart": positions,
            "logic": sorted(list(set(logic))),
            "significant_aspects": aspects[:15], # Prevent token bloat
            "predictions": formatted_preds
        }
