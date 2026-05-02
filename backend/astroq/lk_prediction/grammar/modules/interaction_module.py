from typing import Dict, Any, List, Set, Optional
from ..base import GrammarModule, GrammarHit
from ...lk_constants import (
    NATURAL_RELATIONSHIPS,
    FOUNDATIONAL_HOUSES,
    HOUSE_ASPECT_TARGETS as HOUSE_ASPECT_MAP,
    HOUSE_ASPECT_DATA,
    SUDDEN_STRIKE_HOUSE_PAIRS,
    DISPOSITION_RULES,
    PLANET_PAKKA_GHAR,
    PLANET_EXALTATION,
    PLANET_DEBILITATION,
    get_35_year_ruler
)

class InteractionModule:
    """
    Handles multi-planet interactions:
    - Sathi (Companions / House Exchange)
    - BilMukabil (Hostiles)
    - Dhoka (Deceit) and Achanak Chot (Sudden Strike)
    - Dispositions (Spoiling/Boosting)
    - 35-Year Cycle Ruler
    """
    name = "Interaction"
    phase = 1

    def __init__(self, config: Any):
        self._cfg = config
        self.w_sathi = config.get("strength.sathi_boost_per_companion", fallback=1.00)
        self.w_bilmukabil = config.get("strength.bilmukabil_penalty_per_hostile", fallback=1.50)
        self.w_dhoka = config.get("strength.dhoka_graha_factor", fallback=0.70)
        self.w_achanak = config.get("strength.achanak_chot_penalty", fallback=2.00)
        self.w_35yr = config.get("strength.cycle_35yr_boost", fallback=1.25)
        self.w_spoiler = config.get("strength.spoiler_factor", fallback=0.50)

    def detect(self, chart: Dict[str, Any]) -> List[GrammarHit]:
        hits = []
        planets = chart.get("planets_in_houses", {})
        age = chart.get("chart_period", 0)
        c_type = chart.get("chart_type", "Birth")

        # 1. Sathi & BilMukabil
        for p1 in planets:
            # Sathi (Exchange)
            for p2 in planets:
                if p1 == p2: continue
                if self._detect_exchange(p1, p2, planets):
                    hits.append(GrammarHit("SATHI_EXCHANGE", f"{p1} and {p2} in House Exchange", [p1, p2]))

            # BilMukabil
            for p2 in planets:
                if p1 == p2: continue
                if self._detect_bilmukabil(p1, p2, planets):
                    hits.append(GrammarHit("BILMUKABIL", f"{p1} and {p2} in BilMukabil", [p1, p2]))

        # 2. Dhoka
        dhoka_hits = self._detect_dhoka(chart)
        hits.extend(dhoka_hits)

        # 3. Achanak Chot
        achanak_hits = self._detect_achanak_chot(chart)
        hits.extend(achanak_hits)

        # 4. Dispositions (Informational detection)
        disp_hits = self._detect_dispositions(planets)
        hits.extend(disp_hits)

        # 5. Same-House Companions (Sathi)
        house_occupants: Dict[int, List[str]] = {}
        for p, d in planets.items():
            h_num = d.get("house")
            if h_num:
                house_occupants.setdefault(h_num, []).append(p)
        
        for occupants in house_occupants.values():
            if len(occupants) > 1:
                hits.append(GrammarHit("SATHI_EXCHANGE", f"Companions in same house: {', '.join(occupants)}", occupants))

        # 6. 35-Year Ruler
        if c_type == "Yearly" and age > 0:
            ruler = get_35_year_ruler(age)
            if ruler:
                hits.append(GrammarHit("CYCLE_35YR", f"{ruler} is 35-Year Cycle Ruler", [ruler]))

        return hits

    def audit(self, chart: Dict[str, Any], enriched: Dict[str, Any], hits: List[GrammarHit]) -> None:
        planets = chart.get("planets_in_houses", {})
        
        # 1. First Pass: Dispositions (Affect strength_total directly)
        for h in [h for h in hits if h.rule_id == "DISPOSITION"]:
            causer = h.metadata.get("causer")
            affected = h.metadata.get("affected")
            effect = h.metadata.get("effect")
            
            if not affected: continue
            
            # For manual conflicts (Sun-Saturn), there might not be a single 'causer' strength to steal
            delta = 0.0
            if causer and causer in enriched:
                causer_strength = abs(float(
                    enriched[causer].get("raw_aspect_strength") or enriched[causer].get("strength_total", 0.0)
                ))
                delta = causer_strength if effect == "Good" else -causer_strength
            else:
                # Fixed penalty for manual conflict if no causer strength logic applies
                delta = -2.0 if effect == "Bad" else 2.0

            if affected in enriched:
                enriched[affected]["strength_total"] += delta
                bd = enriched[affected].setdefault("strength_breakdown", {})
                bd["disposition"] = bd.get("disposition", 0.0) + delta
                enriched[affected].setdefault("dispositions_active", []).append(h.metadata)

        # 2. Second Pass: Multipliers
        for p_name, ep in enriched.items():
            total = ep.get("strength_total", 0.0)
            bd = ep.get("strength_breakdown", {})
            p_hits = [h for h in hits if p_name in h.affected_planets]

            # Sathi (Boost per companion)
            sathi_hits = [h for h in p_hits if h.rule_id == "SATHI_EXCHANGE"]
            if sathi_hits:
                for sh in sathi_hits:
                    companions = [c for c in sh.affected_planets if c != p_name]
                    ep.setdefault("sathi_companions", []).extend(companions)
                
                delta = len(sathi_hits) * self.w_sathi
                bd["sathi"] = delta
                total += delta

            # BilMukabil (Penalty)
            bil_hits = [h for h in p_hits if h.rule_id == "BILMUKABIL"]
            if bil_hits:
                for bh in bil_hits:
                    hostiles = [c for c in bh.affected_planets if c != p_name]
                    ep.setdefault("bilmukabil_hostile_to", []).extend(hostiles)
                
                delta = -abs(total) * (1.0 - (1.0 / self.w_bilmukabil))
                bd["bilmukabil"] = delta
                total += delta

            # Dhoka
            if any(h.rule_id == "DHOKA" for h in p_hits):
                ep["dhoka_graha"] = True
                delta = -abs(total) * (1.0 - self.w_dhoka)
                bd["dhoka"] = delta
                total += delta

            # Achanak Chot
            if any(h.rule_id == "ACHANAK_CHOT" for h in p_hits):
                ep["achanak_chot_active"] = True
                delta = -self.w_achanak
                bd["achanak_chot"] = delta
                total += delta

            # 35yr Cycle
            if any(h.rule_id == "CYCLE_35YR" for h in p_hits):
                delta = abs(total) * (self.w_35yr - 1.0)
                bd["cycle_35yr"] = delta
                total += delta

            ep["strength_total"] = total

    def _detect_exchange(self, p1: str, p2: str, planets: dict) -> bool:
        p1_h = planets.get(p1, {}).get("house")
        p2_h = planets.get(p2, {}).get("house")
        if not p1_h or not p2_h: return False

        def _get_owned(p: str) -> Set[int]:
            houses = {PLANET_PAKKA_GHAR.get(p)}
            ex = PLANET_EXALTATION.get(p, [])
            deb = PLANET_DEBILITATION.get(p, [])
            houses.update(ex if isinstance(ex, list) else [ex])
            houses.update(deb if isinstance(deb, list) else [deb])
            return {h for h in houses if h is not None}

        return p2_h in _get_owned(p1) and p1_h in _get_owned(p2)

    def _detect_bilmukabil(self, p1: str, p2: str, planets: dict) -> bool:
        # Step 1: Friends
        if p2 not in NATURAL_RELATIONSHIPS.get(p1, {}).get("Friends", []): return False
        
        # Step 2: Significant Aspect (Priority to manual aspect list)
        h1, h2 = planets[p1].get("house"), planets[p2].get("house")
        if not h1 or not h2: return False
        
        manual_aspect = False
        for asp in planets[p1].get("aspects", []):
            if asp.get("aspecting_planet") == p2:
                manual_aspect = True
                break
        
        if not (manual_aspect or h2 in HOUSE_ASPECT_MAP.get(h1, []) or h1 in HOUSE_ASPECT_MAP.get(h2, [])):
            return False

        # Step 3: Enemy in Foundational
        enemies_p1 = NATURAL_RELATIONSHIPS.get(p1, {}).get("Enemies", [])
        enemies_p2 = NATURAL_RELATIONSHIPS.get(p2, {}).get("Enemies", [])
        for e in enemies_p1:
            if e in planets and planets[e].get("house") in FOUNDATIONAL_HOUSES.get(p2, []): return True
        for e in enemies_p2:
            if e in planets and planets[e].get("house") in FOUNDATIONAL_HOUSES.get(p1, []): return True
        return False

    def _detect_dhoka(self, chart: dict) -> List[GrammarHit]:
        res = []
        planets = chart.get("planets_in_houses", {})
        c_type = chart.get("chart_type", "Birth")
        age = chart.get("chart_period", 0)

        def get_in_h(h_num: int) -> Optional[str]:
            matches = [p for p, d in planets.items() if d.get("house") == h_num]
            return matches[0] if len(matches) == 1 else None

        if c_type == "Birth":
            h10 = get_in_h(10)
            if h10: res.append(GrammarHit("DHOKA", "Birth H10 Dhoka", [h10], metadata={"type": 2, "planet": h10, "effect": "Birth H10 Dhoka"}))
        elif c_type == "Yearly":
            # Type 1: Age Sequence (Requires Age > 0)
            if age > 0:
                h8_ref = get_in_h(8) or "Mars"
                h9_ref = get_in_h(9) or "Jupiter"
                h12_ref = get_in_h(12) or "Jupiter"
                seq = ["Sun", "Moon", "Ketu", "Mars", "Mercury", "Saturn", "Rahu", h8_ref, h9_ref, "Jupiter", "Venus", h12_ref]
                ruler = seq[(age - 1) % 12]
                res.append(GrammarHit("DHOKA", f"Age Sequence Dhoka ({ruler})", [ruler], metadata={"type": 1, "planet": ruler, "effect": "Age Sequence"}))

            # Type 4: Annual H10 (Structural, doesn't strictly need Age)
            h10_annual = get_in_h(10)
            if h10_annual:
                # Any enemy of H10 planet in H8 triggers Manda
                h10_planet = h10_annual
                enemies = NATURAL_RELATIONSHIPS.get(h10_planet, {}).get("Enemies", [])
                h8_enemy = next((p for p in enemies if get_in_h(8) == p), None)
                
                effect = "Manda" if h8_enemy else "Umda"
                res.append(GrammarHit("DHOKA", f"Annual H10 Dhoka ({h10_annual})", [h10_annual], metadata={"type": 4, "planet": h10_annual, "effect": effect}))

        return res

    def _detect_achanak_chot(self, chart: dict) -> List[GrammarHit]:
        res = []
        if chart.get("chart_type") != "Yearly": return res
        
        # Mock birth is required for Achanak Chot
        birth = chart.get("_mock_birth_chart", {})
        b_pih = birth.get("planets_in_houses", {})
        a_pih = chart.get("planets_in_houses", {})

        for pair in SUDDEN_STRIKE_HOUSE_PAIRS:
            h1, h2 = list(pair)
            p1 = next((p for p, d in b_pih.items() if d.get("house") == h1), None)
            p2 = next((p for p, d in b_pih.items() if d.get("house") == h2), None)
            
            if p1 and p2:
                # Check if they aspect in Annual (Priority to manual aspect list)
                ah1, ah2 = a_pih.get(p1, {}).get("house"), a_pih.get(p2, {}).get("house")
                
                # Check for manual aspect first
                manual_aspect = False
                for asp in a_pih.get(p1, {}).get("aspects", []):
                    if asp.get("aspecting_planet") == p2:
                        manual_aspect = True
                        break
                
                if manual_aspect or (ah1 and ah2 and (ah2 in HOUSE_ASPECT_MAP.get(ah1, []) or ah1 in HOUSE_ASPECT_MAP.get(ah2, []))):
                    res.append(GrammarHit("ACHANAK_CHOT", f"Sudden Strike between {p1} and {p2}", [p1, p2], metadata={"birth_chart_houses": [h1, h2]}))
        return res

    def _detect_dispositions(self, planets: dict) -> List[GrammarHit]:
        res = []
        # Standard Rules
        for causer, houses, affected, effect in DISPOSITION_RULES:
            h_causer = planets.get(causer, {}).get("house")
            if h_causer in houses:
                res.append(GrammarHit(
                    "DISPOSITION", 
                    f"{causer} in H{h_causer} {effect}ly affects {affected}", 
                    [affected], 
                    metadata={"causer": causer, "affected": affected, "effect": effect, "rule_name": f"{causer}(H{h_causer}) Disposition"}
                ))
        
        # Manual Checks (Legacy Parity)
        def h(p: str) -> Optional[int]: return planets.get(p, {}).get("house")
        def has_aspect(p1: str, p2: str) -> bool:
            h1, h2 = h(p1), h(p2)
            if not h1 or not h2: return False
            return h2 in HOUSE_ASPECT_MAP.get(h1, []) or h1 in HOUSE_ASPECT_MAP.get(h2, [])

        h_sun, h_sat = h("Sun"), h("Saturn")
        if h_sun and h_sat and has_aspect("Sun", "Saturn"):
            res.append(GrammarHit("DISPOSITION", "Sun-Saturn Conflict", ["Venus"], 
                metadata={"rule_name": f"Sun(H{h_sun})-Saturn(H{h_sat}) Conflict", "affected": "Venus", "effect": "Bad"}))
        
        if h("Sun") == 6 and h("Mars") == 10:
            res.append(GrammarHit("DISPOSITION", "Sun(H6)-Mars(H10) Scapegoat", ["Ketu"], 
                metadata={"rule_name": "Sun(H6)-Mars(H10) Scapegoat", "affected": "Ketu", "effect": "Bad"}))

        if h("Mercury") == 3:
            res.append(GrammarHit("DISPOSITION", "Mercury(H3) Destructive", ["Jupiter", "Saturn"], 
                metadata={"rule_name": "Mercury(H3) Destructive", "affected": "Jupiter", "effect": "Bad"}))
        elif h("Mercury") == 12:
            res.append(GrammarHit("DISPOSITION", "Mercury(H12) Destructive", ["Ketu"], 
                metadata={"rule_name": "Mercury(H12) Destructive", "affected": "Ketu", "effect": "Bad"}))

        return res
