from typing import Dict, Any, List
from ..base import GrammarModule, GrammarHit
from ...lk_constants import RIN_RULES

class DebtModule:
    """
    Detects and applies Lal Kitab Debts (Rin).
    Applies a penalty multiplier to triggering planets.
    """
    name = "Debt"
    phase = 3

    def __init__(self, config: Any):
        self._cfg = config
        self.w_rin = config.get("strength.rin_penalty_factor", fallback=0.85)

    def detect(self, chart: Dict[str, Any]) -> List[GrammarHit]:
        hits = []
        planets = chart.get("planets_in_houses", {})
        if not planets:
            return hits

        for name, plist, hlist in RIN_RULES:
            triggering_planets = []
            for p in plist:
                house = planets.get(p, {}).get("house")
                if house in hlist:
                    triggering_planets.append(p)
            
            if triggering_planets:
                hits.append(GrammarHit("RIN_DEBT", f"{name} detected via {', '.join(triggering_planets)}", triggering_planets, metadata={"debt_name": name}))

        # Store for chart-wide metadata
        chart["lal_kitab_debts"] = [{"debt_name": h.metadata["debt_name"], "active": True} for h in hits]
        return hits

    def audit(self, chart: Dict[str, Any], enriched: Dict[str, Any], hits: List[GrammarHit]) -> None:
        for p_name, ep in enriched.items():
            planet_hits = [h for h in hits if p_name in h.affected_planets]
            if not planet_hits:
                continue

            ep["rin_debts"] = [h.metadata["debt_name"] for h in planet_hits]
            
            total = ep.get("strength_total", 0.0)
            bd = ep.get("strength_breakdown", {})
            
            # Apply penalty once if any debt exists for this planet
            delta = -abs(total) * (1.0 - self.w_rin)
            bd["rin"] = delta
            ep["strength_total"] = total + delta
