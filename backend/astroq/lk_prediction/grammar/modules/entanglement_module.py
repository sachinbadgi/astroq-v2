from typing import Dict, Any, List
from ..base import GrammarModule, GrammarHit
from ...lk_constants import MASNUI_FORMATION_RULES, MASNUI_TO_STANDARD

class EntanglementModule:
    """
    Handles Masnui (Artificial) Planet formation and Parent Feedback loops.
    """
    name = "Entanglement"
    phase = 4

    def __init__(self, config: Any):
        self._cfg = config
        self.w_masnui_feedback = config.get("strength.masnui_parent_feedback", fallback=0.30)

    def detect(self, chart: Dict[str, Any]) -> List[GrammarHit]:
        hits = []
        planets_data = chart.get("planets_in_houses", {})
        if not planets_data:
            return hits

        # Group occupants by house
        house_occupants: Dict[int, List[str]] = {i: [] for i in range(1, 13)}
        for p_name, p_info in planets_data.items():
            h = p_info.get("house")
            if h and 1 <= h <= 12:
                house_occupants[h].append(p_name)

        for h_num, occupants in house_occupants.items():
            if not occupants: continue
            occupants_lc = {o.lower() for o in occupants}
            
            for required_set, result_name in MASNUI_FORMATION_RULES:
                if required_set.issubset(occupants_lc):
                    # Map back to original case
                    components = [p for p in occupants if p.lower() in required_set]
                    hits.append(GrammarHit(
                        "MASNUI_FORMATION", 
                        f"{result_name} formed in H{h_num} by {', '.join(components)}",
                        components,
                        metadata={"masnui_name": result_name, "house": h_num, "components": components}
                    ))
        
        chart["masnui_grahas_formed"] = [
            {"formed_in_house": h.metadata["house"], "masnui_graha_name": h.metadata["masnui_name"], "components": h.metadata["components"]}
            for h in hits
        ]
        return hits

    def audit(self, chart: Dict[str, Any], enriched: Dict[str, Any], hits: List[GrammarHit]) -> None:
        if not hits: return

        planets_data = chart.setdefault("planets_in_houses", {})
        
        for hit in hits:
            m_name = hit.metadata["masnui_name"]
            # Internal unique name
            v_name = m_name.replace("Artificial", "Masnui")
            if v_name in enriched: v_name = f"{v_name} (Formed)"
            
            h_num = hit.metadata["house"]
            components = hit.metadata["components"]
            
            # Base Masnui strength is typically high (5.0 canonical)
            base_total = 5.0
            
            # 1. Register in chart
            planets_data[v_name] = {
                "house": h_num,
                "is_masnui": True,
                "formed_by": components,
            }
            
            # 2. Register in enriched
            ep = {
                "house": h_num, 
                "strength_total": base_total, 
                "is_masnui": True,
                "strength_breakdown": {"masnui_foundation": base_total},
                "states": ["Masnui"]
            }
            enriched[v_name] = ep
            
            # 3. Feedback to parents
            for comp in components:
                if comp in enriched:
                    feedback = base_total * self.w_masnui_feedback
                    enriched[comp]["strength_total"] += feedback
                    enriched[comp]["is_masnui_parent"] = True
                    bd = enriched[comp].setdefault("strength_breakdown", {})
                    bd["masnui_feedback"] = bd.get("masnui_feedback", 0.0) + feedback
                    enriched[comp].setdefault("states", [])
                    enriched[comp]["states"].append(f"Masnui Feedback (+{feedback:.1f})")
                    
        # Note: Aspects for Masnui planets should be handled by the orchestrator 
        # or a dedicated interaction module after all planets (including virtual ones) are created.
