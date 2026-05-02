from typing import Dict, Any, List
from ..base import GrammarModule, GrammarHit

class StructuralModule:
    """
    Detects chart-wide structural conditions:
    - Nagrik/Nashtik classification (Upper/Lower half focus)
    - Andhi Kundli (Blind Horoscope)
    """
    name = "Structural"
    phase = 1

    def detect(self, chart: Dict[str, Any]) -> List[GrammarHit]:
        hits = []
        pih = chart.get("planets_in_houses", {})
        occupied_houses = {d.get("house") for d in pih.values() if d.get("house")}
        
        # 1. Nagrik/Nashtik
        upper_half = {1, 2, 3, 4, 5, 6}
        lower_half = {7, 8, 9, 10, 11, 12}
        
        structural_type = "Mixed"
        if occupied_houses:
            if occupied_houses.issubset(upper_half):
                structural_type = "Nagrik (Active/Self)"
            elif occupied_houses.issubset(lower_half):
                structural_type = "Nashtik (Passive/Social)"
        
        chart["structural_type"] = structural_type
        hits.append(GrammarHit("STRUCTURAL_TYPE", f"Chart classified as {structural_type}"))

        # 2. Andhi Kundli
        h = lambda p: pih.get(p, {}).get("house")
        andhi_status = "Inactive"
        if h("Sun") == 4 and h("Saturn") == 7:
            andhi_status = "Active (Sun 4, Sat 7)"
        else:
            malefics_in_10 = [p for p in ["Saturn", "Rahu", "Ketu"] if h(p) == 10]
            if len(malefics_in_10) >= 2:
                andhi_status = "Active (Malefics cluster in 10)"
        
        chart["andhi_kundli_status"] = andhi_status
        if andhi_status != "Inactive":
            hits.append(GrammarHit("ANDHI_KUNDLI", f"Blind Horoscope detected: {andhi_status}"))

        # 3. Dharmi Teva
        if h("Jupiter") and h("Saturn") and h("Jupiter") == h("Saturn"):
            chart["dharmi_kundli_status"] = "Dharmi Teva"
            hits.append(GrammarHit("DHARMI_KUNDLI", "Pious Horoscope (Dharmi Teva) detected", ["Jupiter", "Saturn"]))
        else:
            chart["dharmi_kundli_status"] = "Inactive"

        return hits

    def audit(self, chart: Dict[str, Any], enriched: Dict[str, Any], hits: List[GrammarHit]) -> None:
        # Structural classification doesn't apply direct strength modifiers
        # but provides context for other modules.
        pass
