from typing import Dict, Any, List, Optional
from ..base import GrammarModule, GrammarHit
from ...lk_constants import HOUSE_ASPECT_TARGETS as HOUSE_ASPECT_MAP

class MangalBadhModule:
    """
    Detects and applies Mangal Badh (Bad Mars) conditions.
    Contains 13 increment rules and 4 decrement rules (Goswami 1952).
    """
    name = "MangalBadh"
    phase = 3

    def __init__(self, config: Any):
        self._cfg = config
        self.w_mangal_divisor = config.get("strength.mangal_badh_divisor", fallback=16.0)

    def detect(self, chart: Dict[str, Any]) -> List[GrammarHit]:
        hits = []
        planets = chart.get("planets_in_houses", {})
        if "Mars" not in planets:
            return hits

        def h(p: str) -> Optional[int]:
            return planets.get(p, {}).get("house")

        def conjunct(pa: str, pb: str) -> bool:
            ha, hb = h(pa), h(pb)
            return bool(ha and hb and ha == hb)

        def in_house(p: str, house: int) -> bool:
            return h(p) == house

        def in_houses(p: str, houses: List[int]) -> bool:
            return h(p) in houses

        def aspects(p1: str, p2: str) -> bool:
            ha, hb = h(p1), h(p2)
            if not ha or not hb: return False
            return hb in HOUSE_ASPECT_MAP.get(ha, [])

        counter = 0
        # Increments
        if conjunct("Sun", "Saturn"): counter += 1
        if h("Sun") and not aspects("Sun", "Mars"): counter += 1
        if h("Moon") and not aspects("Moon", "Mars"): counter += 1
        if in_house("Mercury", 6) and in_house("Ketu", 6): counter += 1
        if conjunct("Mars", "Mercury") or conjunct("Mars", "Ketu"): counter += 1
        if in_house("Ketu", 1): counter += 1
        if in_house("Ketu", 8): counter += 1
        if in_house("Mars", 3): counter += 1
        if in_house("Venus", 9): counter += 1
        if in_houses("Sun", [6, 7, 10, 12]): counter += 1
        if in_house("Mars", 6): counter += 1
        if in_houses("Mercury", [1, 3, 8]): counter += 1
        if in_houses("Rahu", [5, 9]): counter += 1

        # Decrements
        if conjunct("Sun", "Mercury"): counter -= 1
        if in_house("Mars", 8) and in_house("Mercury", 8): counter -= 1
        if in_house("Sun", 3) and in_house("Mercury", 3): counter -= 1
        if in_houses("Moon", [1, 2, 3, 4, 8, 9]): counter -= 1

        counter = max(0, counter)
        chart["mangal_badh_count"] = counter
        chart["mangal_badh_status"] = "Active" if counter > 0 else "Inactive"

        if counter > 0:
            hits.append(GrammarHit("MANGAL_BADH", f"Mangal Badh Active (Counter: {counter})", ["Mars"], magnitude=counter))

        return hits

    def audit(self, chart: Dict[str, Any], enriched: Dict[str, Any], hits: List[GrammarHit]) -> None:
        if not hits or "Mars" not in enriched:
            return

        hit = hits[0]
        counter = hit.magnitude
        ep = enriched["Mars"]
        bd = ep.get("strength_breakdown", {})
        total = ep.get("strength_total", 0.0)

        # target_final = mars_base - mars_base * (1.0 + counter / divisor)
        # = - mars_base * counter / divisor
        mars_base = abs(float(ep.get("raw_aspect_strength", abs(total))))
        target_final = mars_base - mars_base * (1.0 + counter / self.w_mangal_divisor)
        
        delta = target_final - total
        bd["mangal_badh"] = delta
        ep["strength_total"] = target_final
