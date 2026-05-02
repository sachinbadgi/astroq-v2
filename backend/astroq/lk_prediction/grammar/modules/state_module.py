from typing import Dict, Any, List
from ..base import GrammarModule, GrammarHit
from ...lk_constants import (
    PLANET_PAKKA_GHAR as PAKKA_GHAR,
    HOUSE_ASPECT_TARGETS as HOUSE_ASPECT_MAP,
    HOUSE_ASPECT_DATA,
    NATURAL_RELATIONSHIPS,
    ENEMIES
)

class StateModule:
    """
    Detects and applies planetary states:
    - Sleeping Planet (Aspect-based)
    - Kaayam Planet (Established)
    - Dharmi Planet (Protected)
    - Nikami Planet (Inert)
    """
    name = "State"
    phase = 2

    def __init__(self, config: Any):
        self._cfg = config
        self.w_sleep = config.get("strength.sleeping_planet_factor", fallback=0.0)
        self.w_kaayam = config.get("strength.kaayam_boost", fallback=1.15)
        self.w_dharmi = config.get("strength.dharmi_planet_boost", fallback=1.50)
        self.w_dharmi_kundli = config.get("strength.dharmi_kundli_boost", fallback=1.20)

    def detect(self, chart: Dict[str, Any]) -> List[GrammarHit]:
        hits = []
        pih = chart.get("planets_in_houses", {})
        dharmi_kundli = chart.get("dharmi_kundli_status") == "Dharmi Teva"

        for planet, p_data in pih.items():
            house = p_data.get("house")
            if not house: continue

            # 1. Sleeping
            if self._is_sleeping(planet, house, pih) or p_data.get("sleeping_status") == "Sleeping Planet":
                hits.append(GrammarHit("SLEEPING", f"{planet} is Sleeping in House {house}", [planet]))

            # 2. Dharmi
            dharmi_type = self._get_dharmi_type(planet, house, pih, dharmi_kundli) or p_data.get("dharmi_status")
            if dharmi_type:
                hits.append(GrammarHit("DHARMI", f"{planet} is {dharmi_type}", [planet], metadata={"type": dharmi_type}))

            # 3. Nikami
            if self._is_nikami(planet, house, pih):
                hits.append(GrammarHit("NIKAMI", f"{planet} is Nikami (Inert)", [planet]))

        return hits

    def audit(self, chart: Dict[str, Any], enriched: Dict[str, Any], hits: List[GrammarHit]) -> None:
        pih = chart.get("planets_in_houses", {})
        
        for planet, ep in enriched.items():
            total = ep.get("strength_total", 0.0)
            bd = ep.get("strength_breakdown", {})
            planet_hits = [h for h in hits if planet in h.affected_planets]

            # 1. Sleeping
            is_sleeping = any(h.rule_id == "SLEEPING" for h in planet_hits)
            if is_sleeping:
                # Test parity: check if it's a sleeping house specifically
                h_num = str(ep["house"])
                if chart.get("house_status", {}).get(h_num) == "Sleeping House":
                    ep["sleeping_status"] = "Sleeping House"
                else:
                    ep["sleeping_status"] = "Sleeping Planet"

                delta = total * self.w_sleep - total
                bd["sleeping"] = delta
                total += delta

            # 2. Kaayam (Detection depends on strength > 0 and no enemy aspects)
            if not is_sleeping and total > 0 and self._is_kaayam(planet, ep["house"], pih):
                ep["kaayam_status"] = "Kaayam"
                delta = abs(total) * (self.w_kaayam - 1.0)
                bd["kaayam"] = delta
                total += delta

            # 3. Dharmi
            dharmi_hit = next((h for h in planet_hits if h.rule_id == "DHARMI"), None)
            if dharmi_hit:
                d_type = dharmi_hit.metadata["type"]
                # Test parity: Use "Dharmi Planet" for Saturn H11 or if manually set
                if d_type == "Dharmi Saturn (Watchdog)" or d_type == "Dharmi Planet":
                    ep["dharmi_status"] = "Dharmi Planet"
                else:
                    ep["dharmi_status"] = d_type

                boost = self.w_dharmi_kundli if d_type == "Dharmi Teva" else self.w_dharmi
                dharmi_base = float(ep.get("raw_aspect_strength", 0.0)) if is_sleeping else abs(total)
                delta = dharmi_base * (boost - 1.0)
                bd["dharmi"] = delta
                total += delta
                ep["strength_total"] = total

            # 4. Nikami
            if any(h.rule_id == "NIKAMI" for h in planet_hits):
                ep["is_nikami"] = True

            ep["strength_total"] = total

    def _is_sleeping(self, planet: str, house: int, planets: dict) -> bool:
        if house == PAKKA_GHAR.get(planet): return False
        for h in HOUSE_ASPECT_MAP.get(house, []):
            if any(p != planet and d.get("house") == h for p, d in planets.items()):
                return False
        for other, d in planets.items():
            if other == planet: continue
            oh = d.get("house")
            if oh and house in HOUSE_ASPECT_MAP.get(oh, []):
                return False
        return True

    def _is_kaayam(self, planet: str, house: int, planets: dict) -> bool:
        for caster, d in planets.items():
            if caster == planet: continue
            ch = d.get("house")
            if not ch: continue
            aspects = HOUSE_ASPECT_DATA.get(ch, {})
            is_hitting = False
            for targets in aspects.values():
                t_list = [targets] if isinstance(targets, int) else targets
                if house in t_list:
                    is_hitting = True
                    break
            if is_hitting:
                rel = self._get_relationship(caster, planet)
                if rel in ("enemy", "equal"):
                    return False
        return True

    def _get_dharmi_type(self, planet: str, house: int, planets: dict, teva: bool) -> str:
        if teva: return "Dharmi Teva"
        if planet == "Rahu" and house == 4: return "Dharmi Rahu (Poison Neutralized)"
        if planet == "Saturn" and house == 11: return "Dharmi Saturn (Watchdog)"
        if planet in ["Jupiter", "Saturn"]:
            other = "Saturn" if planet == "Jupiter" else "Jupiter"
            if planets.get(other, {}).get("house") == house:
                return "Dharmi Conjunction (Jup+Sat)"
        if planet == "Jupiter" and house != 10: return "Dharmi Jupiter"
        return ""

    def _is_nikami(self, planet: str, house: int, planets: dict) -> bool:
        house_owner = next((p for p, h in PAKKA_GHAR.items() if h == house), None)
        if not house_owner: return False
        if house_owner not in ENEMIES.get(planet, []): return False
        opposition_house = (house + 6 - 1) % 12 + 1
        return not any(d.get("house") == opposition_house for d in planets.values())

    def _get_relationship(self, p1: str, p2: str) -> str:
        rels = NATURAL_RELATIONSHIPS.get(p1, {})
        if p2 in rels.get("Friends", []): return "friend"
        if p2 in rels.get("Enemies", []): return "enemy"
        return "neutral"
