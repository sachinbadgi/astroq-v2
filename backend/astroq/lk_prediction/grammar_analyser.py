"""
Module 3: Grammar Analyser.

Detects 15 Lal Kitab grammar conditions and applies their respective strength
modifiers. Updates the `EnrichedPlanet` dicts in-place.
"""

from __future__ import annotations

import math
from typing import Any

from astroq.lk_prediction.config import ModelConfig


class GrammarAnalyser:
    """
    Applies Lal Kitab grammar rules to enriched planets.

    Parameters
    ----------
    config : ModelConfig
        Centralised configuration instance.
    """

    def __init__(self, config: ModelConfig) -> None:
        self._cfg = config
        self._cache_weights()

    def _cache_weights(self) -> None:
        c = self._cfg
        self.w_sleep = c.get("strength.sleeping_planet_factor", fallback=0.0)
        self.w_kaayam = c.get("strength.kaayam_boost", fallback=1.15)
        self.w_dharmi = c.get("strength.dharmi_planet_boost", fallback=1.50)
        self.w_dharmi_kundli = c.get("strength.dharmi_kundli_boost", fallback=1.20)
        self.w_sathi = c.get("strength.sathi_boost_per_companion", fallback=1.00)
        self.w_bilmukabil = c.get("strength.bilmukabil_penalty_per_hostile", fallback=1.50)
        self.w_mangal = c.get("strength.mangal_badh_divisor", fallback=5.0)
        self.w_masnui = c.get("strength.masnui_parent_feedback", fallback=0.30)
        self.w_dhoka = c.get("strength.dhoka_graha_factor", fallback=0.70)
        self.w_achanak = c.get("strength.achanak_chot_penalty", fallback=2.00)
        self.w_rin = c.get("strength.rin_penalty_factor", fallback=0.85)
        self.w_35yr = c.get("strength.cycle_35yr_boost", fallback=1.25)
        self.w_spoiler = c.get("strength.spoiler_factor", fallback=0.50)

    def apply_grammar_rules(
        self, chart: dict[str, Any], enriched: dict[str, Any]
    ) -> None:
        """
        Run the grammar detection and adjustment pipeline.

        Mutates *enriched* in-place.
        """
        if not enriched:
            return

        planets_data = chart.get("planets_in_houses", {})
        house_status = chart.get("house_status", {})
        chart_type = chart.get("chart_type", "Birth")
        chart_period = chart.get("chart_period", 0)

        # --- Phase 10: Invoke Native Detectors ---
        chart["masnui_grahas_formed"] = self.detect_masnui(chart)
        chart["dhoka_graha_triggers"] = self.detect_dhoka(chart)
        chart["achanak_chot_triggers"] = self.detect_achanak_chot_triggers(chart)
        chart["lal_kitab_debts"] = self.detect_rin(chart)
        chart["lal_kitab_dispositions"] = self.detect_dispositions(chart)
        chart["dharmi_kundli_status"] = "Dharmi Teva" if self.detect_dharmi_kundli(chart) else "Normal"
        mangal_badh_counter = self.detect_mangal_badh(chart)
        chart["mangal_badh_status"] = "Active" if mangal_badh_counter > 0 else "Inactive"
        chart["mangal_badh_count"] = mangal_badh_counter
            
        # Context for the local loop
        dharmi_kundli = chart.get("dharmi_kundli_status") == "Dharmi Teva"
        mangal_badh_active = chart.get("mangal_badh_status") == "Active"

        masnui_parents = set()
        for m in chart.get("masnui_grahas_formed", []):
            masnui_parents.update(m.get("components", []))

        # Rename to match what's used in detectors
        dhoka_grahas = {d.get("planet") for d in chart.get("dhoka_graha_triggers", [])}
        achanak_targets = set()
        for a in chart.get("achanak_chot_triggers", []):
            achanak_targets.update(a.get("planets", []))

        rin_list = chart.get("lal_kitab_debts", [])
        disposition_list = chart.get("lal_kitab_dispositions", [])

        ruler_35 = self._get_35_year_ruler(chart_period) if chart_type == "Yearly" else None

        # Pass 1: Local flags
        for planet, ep in enriched.items():
            pd = planets_data.get(planet, {})
            self._init_grammar_fields(ep)

            # 1. Sleeping
            if pd.get("sleeping_status", ""):
                ep["sleeping_status"] = pd.get("sleeping_status")
            elif house_status.get(str(ep["house"])) == "Sleeping House":
                ep["sleeping_status"] = "Sleeping House"

            # 2. Kaayam
            states = pd.get("states", [])
            if "Kaayam" in states:
                ep["kaayam_status"] = "Kaayam"

            # 3. Dharmi
            if dharmi_kundli:
                ep["dharmi_status"] = "Dharmi Teva"
            elif pd.get("dharmi_status") == "Dharmi Planet":
                ep["dharmi_status"] = "Dharmi Planet"

            # 4. Sathi & 5. Bil Mukabil
            self._find_companions_and_hostiles(planet, ep, planets_data)

            # 6. Mangal Badh applies specifically to Mars (and others if specified)
            if mangal_badh_active and planet == "Mars":
                # Implementation detail: usually Mars takes the hit
                pass 

            # 7-12. Direct assignments (adjustments done in _apply_adjustments)
            ep["is_masnui_parent"] = planet in masnui_parents
            ep["dhoka_graha"] = planet in dhoka_grahas
            ep["achanak_chot_active"] = planet in achanak_targets
            ep["rin_debts"] = rin_list # Applies to all if not empty
            
            # Map dispositions to planet
            ep["dispositions_active"] = [d for d in disposition_list if planet in d.get("affected_planets", [])]

        # Pass 2: Calculate adjustments
        for planet, ep in enriched.items():
            self._apply_adjustments(
                planet, ep, mangal_badh_active, ruler_35
            )

    def _init_grammar_fields(self, ep: dict[str, Any]) -> None:
        ep.setdefault("sleeping_status", "")
        ep.setdefault("kaayam_status", "")
        ep.setdefault("dharmi_status", "")
        ep.setdefault("sathi_companions", [])
        ep.setdefault("bilmukabil_hostile_to", [])
        ep.setdefault("is_masnui_parent", False)
        ep.setdefault("dhoka_graha", False)
        ep.setdefault("achanak_chot_active", False)
        ep.setdefault("rin_debts", [])
        ep.setdefault("dispositions_active", [])
        
        bd = ep.setdefault("strength_breakdown", {})
        for key in ["sleeping", "disposition", "dharmi", "sathi", "bilmukabil", 
                    "mangal_badh", "masnui_feedback", "dhoka", "achanak_chot", "rin", "cycle_35yr"]:
            bd.setdefault(key, 0.0)

    def _find_companions_and_hostiles(
        self, planet: str, ep: dict[str, Any], planets_data: dict[str, Any]
    ) -> None:
        house = ep["house"]
        pd = planets_data.get(planet, {})

        # Sathi
        for other, opd in planets_data.items():
            if other != planet and opd.get("house") == house:
                ep["sathi_companions"].append(other)

        # Bil Mukabil (100% aspect + enemy)
        aspects = pd.get("aspects", [])
        for asp in aspects:
            if asp.get("aspect_type") == "100 Percent" and asp.get("relationship") == "enemy":
                ep["bilmukabil_hostile_to"].append(asp.get("aspecting_planet"))

    def _apply_adjustments(
        self, planet: str, ep: dict[str, Any], mangal_active: bool, ruler_35: str | None
    ) -> None:
        total = float(ep.get("strength_total", 0.0))
        bd = ep["strength_breakdown"]
        
        # We process multiplicative penalties/boosts by calculating the delta
        # and adding it to total, so `breakdown_sum == total`.
        
        # 1. Sleeping
        if ep["sleeping_status"]:
            delta = total * self.w_sleep - total
            bd["sleeping"] += delta
            total += delta

        # 2. Kaayam
        if ep["kaayam_status"] == "Kaayam":
            delta = abs(total) * (self.w_kaayam - 1.0)
            bd["disposition"] += delta
            total += delta

        # 3. Dharmi
        if ep["dharmi_status"]:
            boost = self.w_dharmi_kundli if ep["dharmi_status"] == "Dharmi Teva" else self.w_dharmi
            delta = abs(total) * (boost - 1.0)
            bd["dharmi"] += delta
            total += delta

        # 4. Sathi
        if ep["sathi_companions"]:
            # e.g., +1.0 offset per companion
            delta = len(ep["sathi_companions"]) * self.w_sathi
            bd["sathi"] += delta
            total += delta

        # 5. Bil Mukabil
        if ep["bilmukabil_hostile_to"]:
            delta = -abs(total) * (1.0 - (1.0 / self.w_bilmukabil))
            bd["bilmukabil"] += delta
            total += delta

        # 6. Mangal Badh
        if mangal_active and planet == "Mars":
            # Penalise Mars heavily
            delta = -(abs(total) - (abs(total) / self.w_mangal))
            bd["mangal_badh"] += delta
            total += delta

        # 7. Masnui Feedback
        if ep["is_masnui_parent"]:
            delta = abs(total) * self.w_masnui
            bd["masnui_feedback"] += delta
            total += delta

        # 8. Dhoka
        if ep["dhoka_graha"]:
            delta = -abs(total) * (1.0 - self.w_dhoka)
            bd["dhoka"] += delta
            total += delta

        # 9. Achanak Chot
        if ep["achanak_chot_active"]:
            delta = -self.w_achanak
            bd["achanak_chot"] += delta
            total += delta

        # 10. Rin
        if ep.get("rin_debts"):
            # Apply penalty once if any debt exists
            delta = -abs(total) * (1.0 - self.w_rin)
            bd["rin"] += delta
            total += delta

        # 11. Dispositions
        for disp in ep.get("dispositions_active", []):
            is_neg = disp.get("effect") == "Destructive" or "Conflict" in disp.get("rule_name", "")
            factor = (1.0 - self.w_spoiler) if is_neg else (self.w_kaayam - 1.0) # reuse weights if specific not found
            delta = -abs(total) * (1.0 - self.w_spoiler) if is_neg else abs(total) * (self.w_kaayam - 1.0)
            bd["disposition"] += delta
            total += delta

        # 12. 35 Year Cycle
        if ruler_35 == planet:
            delta = abs(total) * (self.w_35yr - 1.0)
            bd["cycle_35yr"] += delta
            total += delta

        ep["strength_total"] = total

        ep["strength_total"] = total
        
    def detect_sleeping(self, planet: str, planets: dict) -> bool:
        """Sleeping if not in Pakka Ghar and casting no aspects."""
        PAKKA_GHAR = {"Sun": 1, "Moon": 4, "Mars": 3, "Mercury": 7, "Jupiter": 2, "Venus": 7, "Saturn": 10, "Rahu": 12, "Ketu": 6}
        p_data = planets.get(planet)
        if not p_data: return False
        
        in_pakka = p_data.get("house") == PAKKA_GHAR.get(planet)
        has_aspects = len(p_data.get("aspects", [])) > 0
        return not in_pakka and not has_aspects

    def detect_kaayam(self, planet: str, planets: dict) -> bool:
        """Kaayam if base strength > 5 and NO enemy aspects received."""
        p_data = planets.get(planet)
        if not p_data: return False
        
        if p_data.get("strength_total", 0.0) <= 5.0:
            return False
            
        target_house = p_data.get("house")
        for caster, c_data in planets.items():
            if caster == planet: continue
            for asp in c_data.get("aspects", []):
                if asp.get("aspecting_house") == target_house and asp.get("relationship") == "enemy":
                    return False
        return True

    def detect_dharmi_kundli(self, chart: dict) -> bool:
        """Dharmi Teva if Saturn and Jupiter are conjunct."""
        planets = chart.get("planets_in_houses", {})
        sat = planets.get("Saturn", {}).get("house")
        jup = planets.get("Jupiter", {}).get("house")
        return bool(sat and jup and sat == jup)

    def detect_sathi(self, p1: str, p2: str, planets: dict) -> bool:
        """Sathi if mutual exchange of houses (Exaltation/Pakka). For now, basic mutual exchange checking."""
        p1_h = planets.get(p1, {}).get("house")
        p2_h = planets.get(p2, {}).get("house")
        
        # In a real implementation we check detailed sign/pakka ghar.
        # This covers the basic mutual exchange of natural significance.
        EXALT = {"Sun": 1, "Moon": 2, "Mars": 10, "Mercury": 6, "Jupiter": 4, "Venus": 12, "Saturn": 7, "Rahu": 3, "Ketu": 9}
        PAKKA = {"Sun": 1, "Moon": 4, "Mars": 3, "Mercury": 7, "Jupiter": 2, "Venus": 7, "Saturn": 10, "Rahu": 12, "Ketu": 6}
        
        p1_owns = {EXALT.get(p1), PAKKA.get(p1)}
        p2_owns = {EXALT.get(p2), PAKKA.get(p2)}
        
        return p2_h in p1_owns and p1_h in p2_owns

    def detect_bilmukabil(self, p1: str, p2: str, planets: dict) -> bool:
        """Hostile confrontation checking."""
        d1 = planets.get(p1, {})
        d2 = planets.get(p2, {})
        h1, h2 = d1.get("house"), d2.get("house")
        if not h1 or not h2: return False
        
        for asp in d1.get("aspects", []):
            if asp.get("aspecting_house") == h2 and asp.get("relationship") == "enemy":
                for asp2 in d2.get("aspects", []):
                    if asp2.get("aspecting_house") == h1 and asp2.get("relationship") == "enemy":
                        return True
        return False

    def detect_mangal_badh(self, chart: dict) -> int:
        counter = 0
        planets = chart.get("planets_in_houses", {})
        if "Mars" not in planets: return 0
        
        h = lambda p: planets.get(p, {}).get("house")
        together = lambda p1, p2: h(p1) and h(p1) == h(p2)
        
        if together("Sun", "Saturn"): counter += 1
        if not any(a.get("aspecting_planet") == "Sun" for a in planets.get("Mars", {}).get("aspects", [])): 
            counter += 1
        if together("Mercury", "Venus"): counter += 1
        if h("Ketu") in [1, 8]: counter += 1
        
        return max(0, counter)

    def detect_masnui(self, chart: dict) -> list[dict]:
        """Detect Masnui (Artificial) planets formed by specific conjunctions in the same house."""
        res = []
        planets_data = chart.get("planets_in_houses", {})
        if not planets_data: return res
        
        # Build house occupancy map (House -> Set of lowercased planet names)
        house_occupants = {i: set() for i in range(1, 13)}
        for p_name, p_info in planets_data.items():
            h = p_info.get("house")
            if h and 1 <= h <= 12:
                house_occupants[h].add(p_name.lower())
                
        # 13 definitive rules from reference system
        rules = [
            ({"sun", "venus"}, "Artificial Jupiter"),
            ({"mercury", "venus"}, "Artificial Sun"),
            ({"sun", "jupiter"}, "Artificial Moon"),
            ({"rahu", "ketu"}, "Artificial Venus (Note: Unusual Conjunction)"),
            ({"sun", "mercury"}, "Artificial Mars (Auspicious)"),
            ({"sun", "saturn"}, "Artificial Mars (Malefic)"),
            ({"sun", "saturn"}, "Artificial Rahu (Debilitated Rahu)"),
            ({"jupiter", "rahu"}, "Artificial Mercury"),
            ({"venus", "jupiter"}, "Artificial Saturn (Like Ketu)"),
            ({"mars", "mercury"}, "Artificial Saturn (Like Rahu)"),
            ({"saturn", "mars"}, "Artificial Rahu (Exalted Rahu)"),
            ({"venus", "saturn"}, "Artificial Ketu (Exalted Ketu)"),
            ({"moon", "saturn"}, "Artificial Ketu (Debilitated Ketu)")
        ]
        
        for h_num, occupants in house_occupants.items():
            if not occupants: continue
            
            for required_set, result_name in rules:
                if required_set == occupants:
                    # Exact match for the house occupants
                    res.append({
                        "formed_in_house": h_num,
                        "masnui_graha_name": result_name,
                        "components": [p.capitalize() for p in occupants]
                    })
        return res

    def detect_dhoka(self, chart: dict) -> list[dict]:
        """Detect Dhoka Graha (Planet of Deceit) based on 4 types of triggers."""
        res = []
        planets = chart.get("planets_in_houses", {})
        if not planets: return res
        
        c_type = chart.get("chart_type", "Birth")
        
        # Helper to get planet in specific house
        def get_in_house(h):
            in_h = [p for p, d in planets.items() if d.get("house") == h]
            return in_h[0] if len(in_h) == 1 else None
            
        # Type 2: Birth H10 Planet
        if c_type == "Birth":
            h10_planet = get_in_house(10)
            if h10_planet:
                res.append({"type": 2, "planet": h10_planet, "effect": "Birth H10 Dhoka"})
                
        # Annual chart specific types
        elif c_type == "Yearly":
            age = chart.get("chart_period", 0)
            
            # Type 1: Age based sequence
            h8_ref = get_in_house(8) or "Mars"
            h9_ref = get_in_house(9) or "Jupiter"
            h12_ref = get_in_house(12) or "Jupiter"
            base_sequence = ["Sun", "Moon", "Ketu", "Mars", "Mercury", "Saturn", "Rahu", h8_ref, h9_ref, "Jupiter", "Venus", h12_ref]
            
            if age > 0:
                col_index = (age - 1) % 12
                res.append({"type": 1, "planet": base_sequence[col_index], "effect": "Age Sequence"})
                
            # Type 4: Annual H10 Planet
            h10_annuals = [p for p, d in planets.items() if d.get("house") == 10]
            for p in h10_annuals:
                # Determine Umda/Manda based on H2/H8 occupation
                h2_occ = any(d.get("house") == 2 for d in planets.values())
                h8_occ = any(d.get("house") == 8 for d in planets.values())
                
                # Simplified Manda/Umda determination for now, full needs natural relationships
                effect = "Manda" if h8_occ else ("Umda" if h2_occ else "Depends on Saturn")
                res.append({"type": 4, "planet": p, "effect": effect})
                
            # Type 3: 10th from planet based on birth pairs
            mock_birth = chart.get("_mock_birth_chart", chart) # Fallback to self if no birth provided
            b_planets = mock_birth.get("planets_in_houses", {})
            birth_pairs = {2: 11, 5: 2, 3: 12, 4: 1}
            
            for p_A in h10_annuals:
                birth_h = b_planets.get(p_A, {}).get("house")
                if birth_h in birth_pairs:
                    target_h = birth_pairs[birth_h]
                    targets = [p_B for p_B, d in b_planets.items() if d.get("house") == target_h]
                    for p_B in targets:
                        res.append({
                            "type": 3, 
                            "giver": p_A, 
                            "receiver": p_B, 
                            "effect": "Dhoka Trigger"
                        })
                        
        return res

    def detect_achanak_chot_triggers(self, chart: dict) -> list[dict]:
        """Detect Achanak Chot (Sudden Strike) based on house pairs and annual aspects."""
        res = []
        if chart.get("chart_type") != "Yearly": return res
        
        mock_birth = chart.get("_mock_birth_chart", chart)
        b_planets = mock_birth.get("planets_in_houses", {})
        a_planets = chart.get("planets_in_houses", {})
        
        pairs = [{1, 3}, {2, 4}, {4, 6}, {5, 7}, {7, 9}, {8, 10}, {10, 12}, {1, 11}]
        sig_aspects = {"100 Percent", "50 Percent", "25 Percent"}
        
        # Find potential pairs in birth chart
        potentials = []
        b_names = list(b_planets.keys())
        for i in range(len(b_names)):
            for j in range(i + 1, len(b_names)):
                p1, p2 = b_names[i], b_names[j]
                h1, h2 = b_planets[p1].get("house"), b_planets[p2].get("house")
                if h1 and h2 and h1 != h2 and {h1, h2} in pairs:
                    potentials.append((p1, p2, h1, h2))
                    
        # Check if they aspect each other in annual chart
        for p1, p2, h1, h2 in potentials:
            p1_a = a_planets.get(p1, {})
            p2_a = a_planets.get(p2, {})
            
            triggered = False
            for asp in p1_a.get("aspects", []):
                if asp.get("aspecting_planet") == p2 and asp.get("aspect_type") in sig_aspects:
                    triggered = True
            if not triggered:
                for asp in p2_a.get("aspects", []):
                    if asp.get("aspecting_planet") == p1 and asp.get("aspect_type") in sig_aspects:
                        triggered = True
                        
            if triggered:
                res.append({
                    "planets": [p1, p2],
                    "birth_chart_houses": [h1, h2]
                })
                
        return res

    def detect_rin(self, chart: dict) -> list[str]:
        """Detect 9 standard Lal Kitab Debts (Rin) based on planet-house occupancy."""
        res = []
        planets = chart.get("planets_in_houses", {})
        if not planets: return res
        
        # Helper to check if any planet from set is in any house from set
        def check(plist, hlist):
            for p in plist:
                h = planets.get(p, {}).get("house")
                if h in hlist: return True
            return False

        rules = [
            ("Ancestral Debt (Pitra Rin)", ["Venus", "Mercury", "Rahu"], [2, 5, 9, 12]),
            ("Self Debt (Swayam Rin)", ["Venus", "Rahu"], [5]),
            ("Maternal Debt (Matri Rin)", ["Ketu"], [4]),
            ("Family/Wife/Woman Debt (Stri Rin)", ["Sun", "Rahu", "Ketu"], [2, 7]),
            ("Relative/Brother Debt (Bhai-Bandhu Rin)", ["Mercury", "Ketu"], [1, 8]),
            ("Daughter/Sister Debt (Behen/Beti Rin)", ["Moon"], [3, 6]),
            ("Oppression/Atrocious Debt (Zulm Rin)", ["Sun", "Moon", "Mars"], [10, 11]),
            ("Debt of the Unborn (Ajanma Rin)", ["Venus", "Sun", "Rahu"], [12]),
            ("Negative Speech Debt (Manda Bol Rin)", ["Moon", "Mars", "Ketu"], [6])
        ]

        for name, plist, hlist in rules:
            if check(plist, hlist):
                res.append(name)
        return res

    def detect_dispositions(self, chart: dict) -> list[dict]:
        """Detect 13+ specialized Lal Kitab disposition (spoiling/boosting) rules."""
        res = []
        planets_data = chart.get("planets_in_houses", {})
        if not planets_data: return res
        
        def h(p): return planets_data.get(p, {}).get("house")
        def has_aspect(p1, p2):
             return any(a.get("aspecting_planet") == p2 for a in planets_data.get(p1, {}).get("aspects", []))

        # 1. Sun-Saturn Conflict affecting Venus
        h_sun, h_sat = h("Sun"), h("Saturn")
        if h_sun and h_sat and (has_aspect("Sun", "Saturn") or has_aspect("Saturn", "Sun")):
            res.append({
                "rule_name": f"Sun(H{h_sun})-Saturn(H{h_sat}) Conflict",
                "affected_planets": ["Venus"],
                "effect": "Destructive"
            })
        
        # 2. Mars-Ketu Scapegoat (Sun H6 + Mars H10)
        if h("Sun") == 6 and h("Mars") == 10:
            res.append({
                "rule_name": "Sun(H6)-Mars(H10) Scapegoat",
                "affected_planets": ["Ketu"],
                "effect": "Destructive"
            })

        # 3. Mercury destructive aspects
        h_merc = h("Mercury")
        if h_merc == 3:
            res.append({
                "rule_name": "Mercury(H3) Destructive",
                "affected_planets": ["Jupiter", "Saturn"],
                "effect": "Destructive"
            })
        elif h_merc == 12:
            res.append({
                "rule_name": "Mercury(H12) Destructive",
                "affected_planets": ["Ketu"],
                "effect": "Destructive"
            })

        # 4. Jupiter-Rahu Destruction
        h_jup, h_rahu = h("Jupiter"), h("Rahu")
        if h_jup and h_rahu and (h_jup == h_rahu or has_aspect("Jupiter", "Rahu") or has_aspect("Rahu", "Jupiter")):
            res.append({
                "rule_name": "Jupiter-Rahu Suppression",
                "affected_planets": ["Jupiter"],
                "effect": "Destructive"
            })

        return res

    def _get_35_year_ruler(self, age: int) -> str:
        """Calculate the 35 year cycle ruler for a given age (0-indexed year)."""
        # Lal Kitab 35 year cycle layout:
        # Saturn (1-6), Rahu (7-12), Ketu (13-15), Jupiter (16-21),
        # Sun (22-23), Moon (24), Venus (25-27), Mars (28-33), Mercury (34-35)
        # We match age (which is 1-based year, e.g., age 1 is 1st year)
        # Standard astroq maps: chart_period 0 = Birth. chart_period N = Nth year.
        
        if age <= 0:
            return ""
            
        period = (age - 1) % 35 + 1
        
        if 1 <= period <= 6: return "Saturn"
        if 7 <= period <= 12: return "Rahu"
        if 13 <= period <= 15: return "Ketu"
        if 16 <= period <= 21: return "Jupiter"
        if 22 <= period <= 23: return "Sun"
        if period == 24: return "Moon"
        if 25 <= period <= 27: return "Venus"
        if 28 <= period <= 33: return "Mars"
        if 34 <= period <= 35: return "Mercury"
        
        return ""
