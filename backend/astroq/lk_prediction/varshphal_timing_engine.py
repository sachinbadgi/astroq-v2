from typing import Any, Dict, List, Tuple
from .lk_pattern_constants import (
    VARSHPHAL_TIMING_TRIGGERS,
    VARSHPHAL_AGE_GATES,
    VARSHPHAL_SPECIAL_LOGIC,
    MATURITY_AGE_PATTERN
)
from .lk_constants import (
    HOUSE_ASPECT_TARGETS,
    NATURAL_RELATIONSHIPS,
    PLANET_EXALTATION,
    PLANET_DEBILITATION,
    PLANET_PAKKA_GHAR,
    PUCCA_GHARS_EXTENDED
)
from .lk_pattern_constants import MALEFIC_FATE_DISTRIBUTION

class VarshphalTimingEngine:
    """
    Evaluates the explicit Goswami and Lal Diary Annual Chart (Varshphal) event triggers.
    Provides precise timing signals by comparing Natal and Annual planetary geometries.
    """
    
    def __init__(self):
        self.triggers = VARSHPHAL_TIMING_TRIGGERS
        self.age_gates = VARSHPHAL_AGE_GATES
        self.special_logic = VARSHPHAL_SPECIAL_LOGIC

    def _get_planetary_positions(self, chart_data: Dict[str, Any]) -> Dict[str, int]:
        """Helper to extract planet house positions from chart payload."""
        positions = {}
        for planet, data in chart_data.get("planets_in_houses", {}).items():
            if planet != "Lagna":
                positions[planet] = data.get("house", 0)
        return positions

    def _is_planet_dormant(self, planet: str, house: int, chart_positions: Dict[str, int]) -> bool:
        """A planet is dormant if ALL houses it aspects are completely empty.
        Note: Planets in Pakka Ghar/Pucca Ghar retain awareness via the dormancy rule;
        full override was found empirically to over-wake too many planets (increases FPR).
        """
        if not house: return False
        target_houses = HOUSE_ASPECT_TARGETS.get(house, [])
        if not target_houses: return False

        occupied_houses = list(chart_positions.values())
        for t in target_houses:
            if t in occupied_houses:
                return False
        return True

    def _has_180_degree_block(self, planet: str, house: int, chart_positions: Dict[str, int]) -> bool:
        """Checks if a natural enemy is placed exactly 180 degrees away (house + 6 mod 12)."""
        if not house: return False
        
        enemy_house = house + 6
        if enemy_house > 12: enemy_house -= 12
            
        enemies_in_opposition = [p for p, h in chart_positions.items() if h == enemy_house]
        if not enemies_in_opposition: return False
            
        planet_enemies = NATURAL_RELATIONSHIPS.get(planet, {}).get("enemies", [])
        for opp_planet in enemies_in_opposition:
            if opp_planet in planet_enemies:
                if house in PLANET_EXALTATION.get(planet, []): continue
                if enemy_house in PLANET_EXALTATION.get(opp_planet, []): continue
                return True
        return False

    def _check_maturity_age(self, planet: str, age: int) -> bool:
        """Returns True if the planet has reached its maturity age."""
        maturity_ages = MATURITY_AGE_PATTERN.get("maturity_ages", {})
        mat_age = maturity_ages.get(planet, 0)
        return age >= mat_age

    def check_age_gates(self, natal_chart: Dict[str, Any], age: int, domain: str) -> Tuple[bool, str]:
        """
        Checks if the given age is prohibited for the specified domain based on Natal placements.
        Returns (is_prohibited, reason).
        """
        gates = self.age_gates.get(domain, [])
        if not gates:
            return False, ""
            
        natal_pos = self._get_planetary_positions(natal_chart)
        
        for rule in gates:
            if "planet" in rule and "houses" in rule:
                p = rule["planet"]
                h = natal_pos.get(p)
                if h in rule["houses"]:
                    if "prohibit_before" in rule and age < rule["prohibit_before"]:
                        return True, f"Prohibited before age {rule['prohibit_before']} due to {p} in H{h}."
                    if "prohibit_between" in rule:
                        start, end = rule["prohibit_between"]
                        if start <= age <= end:
                            return True, f"Prohibited between ages {start}-{end} due to {p} in H{h}."
                    if "prohibit" in rule and rule.get("prohibit"):
                        # Check extra condition
                        if rule.get("condition") == "7_to_10_empty":
                            empty = True
                            for check_h in range(7, 11):
                                if check_h in natal_pos.values():
                                    empty = False
                            if empty:
                                return True, f"Prohibited entirely due to {p} in H{h} and 7-10 empty."
                                
            if "ages" in rule and age in rule["ages"]:
                return True, f"Prohibited at age {age}. Danger: {rule.get('outcome')}."
                
        return False, ""

    def evaluate_special_destruction(self, natal_chart: Dict[str, Any], annual_chart: Dict[str, Any]) -> List[str]:
        """
        Evaluates the Sequential Impact Rule (Nisht Grah) from Lal Diary.
        """
        warnings = []
        natal_pos = self._get_planetary_positions(natal_chart)
        annual_pos = self._get_planetary_positions(annual_chart)
        
        rule = self.special_logic.get("sequential_impact_rule", {})
        n_house = rule.get("natal_house")
        a_houses = rule.get("annual_houses", [])
        
        for p, n_h in natal_pos.items():
            if n_h == n_house:
                a_h = annual_pos.get(p)
                if a_h in a_houses:
                    warnings.append(f"Sequential Impact Rule triggered: {p} moved from Natal H8 to Annual H{a_h}. Negates positive effects of this house.")
                    
        return warnings

    def evaluate_varshphal_triggers(self, natal_chart: Dict[str, Any], annual_chart: Dict[str, Any], age: int, domain: str) -> List[Dict[str, Any]]:
        """
        Evaluates the specific geometric triggers for a given domain.
        Returns a list of matched trigger rules.
        """
        domain_triggers = self.triggers.get(domain, [])
        if not domain_triggers:
            return []
            
        natal_pos = self._get_planetary_positions(natal_chart)
        annual_pos = self._get_planetary_positions(annual_chart)
        
        matches = []
        
        for rule in domain_triggers:
            match = True
            
            # Simple planet checks (e.g. "natal_sat": [3, 5])
            for key, val in rule.items():
                if key in ["desc", "polarity", "outcome", "target"]:
                    continue
                    
                if key.startswith("natal_"):
                    planet_abbr = key.split("_")[1].capitalize() # e.g. "sat" -> "Sat"
                    # Special cases for combined logic
                    if key == "natal_ven_mer":
                        if natal_pos.get("Venus") not in val and natal_pos.get("Mercury") not in val:
                            match = False
                    elif key == "natal_jup_mon":
                        if isinstance(val, bool):
                            if (natal_pos.get("Jupiter") == natal_pos.get("Moon")) != val: match = False
                        else:
                            if natal_pos.get("Jupiter") not in val or natal_pos.get("Moon") not in val: match = False
                    elif key == "natal_sun_sat":
                        if (natal_pos.get("Sun") == natal_pos.get("Saturn")) != val: match = False
                    elif key == "natal_mer_mon":
                        if natal_pos.get("Mercury") not in val or natal_pos.get("Moon") not in val: match = False
                    elif key == "natal_jup_sat":
                        if natal_pos.get("Jupiter") not in val or natal_pos.get("Saturn") not in val: match = False
                    elif key == "natal_2_7_blank":
                        occupied = list(natal_pos.values())
                        if (2 not in occupied and 7 not in occupied) != val: match = False
                    else:
                        planet_map = {"Sat": "Saturn", "Ket": "Ketu", "Mer": "Mercury", "Mon": "Moon", "Jup": "Jupiter", "Sun": "Sun", "Rah": "Rahu"}
                        if planet_abbr in planet_map:
                            p = planet_map[planet_abbr]
                            if isinstance(val, bool):
                                if (p in natal_pos) != val: match = False
                            elif natal_pos.get(p) not in val:
                                match = False
                                
                if key.startswith("annual_"):
                    planet_abbr = key.split("_")[1].capitalize()
                    
                    if key == "annual_ven_mer":
                        if annual_pos.get("Venus") not in val and annual_pos.get("Mercury") not in val:
                            match = False
                    elif key == "annual_ven_mer_conjoined":
                        if (annual_pos.get("Venus") == annual_pos.get("Mercury")) != val: match = False
                    elif key == "annual_enemies_in_2_7":
                        enemies = [annual_pos.get("Sun"), annual_pos.get("Moon"), annual_pos.get("Rahu")]
                        has_enemies = any(e in [2, 7] for e in enemies)
                        if has_enemies != val: match = False
                    elif key == "annual_jup_ven":
                        if annual_pos.get("Jupiter") not in val and annual_pos.get("Venus") not in val: match = False
                    elif key == "annual_ket_sat_rah":
                        k = annual_pos.get("Ketu")
                        s = annual_pos.get("Saturn")
                        r = annual_pos.get("Rahu")
                        if k not in val or (s not in val and r not in val): match = False
                    elif key == "annual_jup_mon":
                        if annual_pos.get("Jupiter") not in val or annual_pos.get("Moon") not in val: match = False
                    elif key == "annual_jup_sat":
                        if annual_pos.get("Jupiter") not in val or annual_pos.get("Saturn") not in val: match = False
                    elif key == "annual_mon_ven_conjoined":
                        if (annual_pos.get("Moon") == annual_pos.get("Venus")) != val: match = False
                    elif key == "annual_mer_alone":
                        mer_house = annual_pos.get("Mercury")
                        if mer_house not in val:
                            match = False
                        else:
                            count = sum(1 for p, h in annual_pos.items() if h == mer_house)
                            if count > 1: match = False
                    elif key == "annual_sun_mon_mer_conjoined":
                        mer_h = annual_pos.get("Mercury")
                        if mer_h not in val:
                            match = False
                        elif annual_pos.get("Sun") != mer_h and annual_pos.get("Moon") != mer_h:
                            match = False
                    elif key == "annual_sun_sat":
                        if annual_pos.get("Sun") not in val or annual_pos.get("Saturn") not in val: match = False
                    elif key == "annual_rah_mon_sun":
                        if annual_pos.get("Rahu") not in val and annual_pos.get("Moon") not in val and annual_pos.get("Sun") not in val: match = False
                    elif key == "annual_8_empty":
                        if (8 not in annual_pos.values()) != val: match = False
                    else:
                        planet_map = {"Sat": "Saturn", "Ket": "Ketu", "Mer": "Mercury", "Mon": "Moon", "Jup": "Jupiter", "Sun": "Sun", "Rah": "Rahu", "Ven": "Venus", "Mar": "Mars"}
                        if planet_abbr in planet_map:
                            if annual_pos.get(planet_map[planet_abbr]) not in val:
                                match = False
                                
                if key == "ven_mer_return":
                    v_return = (annual_pos.get("Venus") == natal_pos.get("Venus"))
                    m_return = (annual_pos.get("Mercury") == natal_pos.get("Mercury"))
                    if (v_return or m_return) != val:
                        match = False
            
            if match:
                # Extract primary planets involved
                primary_planets = set()
                planet_map = {"Sat": "Saturn", "Ket": "Ketu", "Mer": "Mercury", "Mon": "Moon", "Jup": "Jupiter", "Sun": "Sun", "Rah": "Rahu", "Ven": "Venus", "Mar": "Mars"}
                for key in rule.keys():
                    if key.startswith("natal_") or key.startswith("annual_"):
                        for part in key.split("_"):
                            abbr = part.capitalize()
                            if abbr in planet_map:
                                primary_planets.add(planet_map[abbr])
                    elif key == "ven_mer_return":
                        primary_planets.update(["Venus", "Mercury"])
                        
                is_blocked = False
                is_premature = False
                
                for p in primary_planets:
                    h = annual_pos.get(p)
                    if h:
                        # Dormancy filter (with Pakka Ghar override built-in)
                        if self._is_planet_dormant(p, h, annual_pos):
                            is_blocked = True
                            rule["desc"] = f"[SUPPRESSED: DORMANT] {rule.get('desc')}"
                            break
                        # 180-Degree enemy block
                        if self._has_180_degree_block(p, h, annual_pos):
                            is_blocked = True
                            rule["desc"] = f"[SUPPRESSED: 180-DEG ENEMY] {rule.get('desc')}"
                            break
                            
                for p in primary_planets:
                    if not self._check_maturity_age(p, age):
                        is_premature = True
                        rule["desc"] = f"[PREMATURE: {p} < Maturity] {rule.get('desc')}"
                        
                rule["is_blocked"] = is_blocked
                rule["is_premature"] = is_premature
                matches.append(rule)
                
        return matches

    def get_timing_confidence(self, natal_chart: Dict[str, Any], annual_chart: Dict[str, Any], age: int, domain: str) -> Dict[str, Any]:
        """
        Main entry point. Assembles age gates, special destruction, and Varshphal triggers.
        Returns a confidence score and metadata.
        """
        is_prohibited, reason = self.check_age_gates(natal_chart, age, domain)
        if is_prohibited:
            return {
                "confidence": "None",
                "prohibited": True,
                "reason": reason,
                "triggers": [],
                "warnings": []
            }
            
        warnings = self.evaluate_special_destruction(natal_chart, annual_chart)
        triggers = self.evaluate_varshphal_triggers(natal_chart, annual_chart, age, domain)
        
        valid_triggers = [t for t in triggers if not t.get("is_blocked")]
        
        confidence = "Low"
        if len(valid_triggers) > 0:
            confidence = "High" if len(valid_triggers) > 1 else "Medium"
            
        # Add premature warnings but do NOT downgrade confidence, because premature events DO happen (they just carry a penalty)
        for t in valid_triggers:
            if t.get("is_premature"):
                warnings.append(f"Premature Activation Trap: {t['desc']}")
            
        return {
            "confidence": confidence,
            "prohibited": False,
            "reason": "Age gates passed.",
            "triggers": [t["desc"] for t in valid_triggers],
            "warnings": warnings,
            "raw_matches": valid_triggers
        }
