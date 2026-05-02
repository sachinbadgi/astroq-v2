import json
import os
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class NarrativeEngine:
    """
    DEEP MODULE: Encapsulates all prose generation and interpretation logic.
    Hides the complexity of:
    1. Vocabulary mapping (Forensic vs Layman).
    2. House-based domain context.
    3. Strength-based tiering.
    """

    def __init__(self):
        self._vocab = self._load_vocabulary()

    def _load_vocabulary(self) -> Dict:
        path = os.path.join(os.path.dirname(__file__), "synthesis_vocabulary.json")
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
        return {"vocabulary": {}, "forensic_connectors": {}, "domain_layman_mapping": {}}

    def assemble_narrative(self, hit_description: str, domain: str, target_houses: List[int], magnitude: float, state_modifier: str) -> str:
        """Generates the final interpretative text for a prediction."""
        strength_tier = self._get_strength_tier(abs(magnitude))
        
        lookup_modifier = state_modifier
        if lookup_modifier == "Startled Malefic": lookup_modifier = "Startled"
        
        prose_key = f"{lookup_modifier}:{strength_tier}:{domain}"
        layman_result = self._vocab["vocabulary"].get(prose_key)
        if not layman_result:
            layman_result = self._vocab["vocabulary"].get(f"{lookup_modifier}:{strength_tier}:General", "")
        
        connector = " → " if layman_result else ""
        
        house_context = ""
        if target_houses:
            house_key = f"H{target_houses[0]}"
            house_label = self._vocab["domain_layman_mapping"].get(house_key, "the current life domain")
            house_context = f" affecting {house_label}"
        
        return f"Forensic Audit: {hit_description}{connector}{layman_result}{house_context}."

    def _get_strength_tier(self, magnitude: float) -> str:
        if magnitude >= 1.5: return "High"
        if magnitude >= 0.8: return "Medium"
        return "Low"
