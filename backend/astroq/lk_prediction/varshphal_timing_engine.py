from typing import Any, Dict, List, Tuple, Optional
from .lk_pattern_constants import (
    VARSHPHAL_TIMING_TRIGGERS,
    VARSHPHAL_AGE_GATES,
    VARSHPHAL_SPECIAL_LOGIC
)
from .state_ledger import StateLedger
from .data_contracts import LKPrediction
from .astrological_context import UnifiedAstrologicalContext
from .doubtful_timing_engine import DoubtfulTimingEngine
from .lk_constants import TIMING_DOMAIN_MAP, KARAKA_DOMAIN_MAP

class VarshphalTimingEngine:
    """
    Evaluates the explicit Goswami and Lal Diary Annual Chart (Varshphal) event triggers.
    Provides precise timing signals by comparing Natal and Annual planetary geometries.
    """
    
    PLANET_MAP = {
        "Sat": "Saturn", "Ket": "Ketu", "Mer": "Mercury", "Mon": "Moon", 
        "Jup": "Jupiter", "Sun": "Sun", "Rah": "Rahu", "Ven": "Venus", "Mar": "Mars"
    }


    def __init__(self):
        self.triggers = VARSHPHAL_TIMING_TRIGGERS
        self.age_gates = VARSHPHAL_AGE_GATES
        self.special_logic = VARSHPHAL_SPECIAL_LOGIC
        self.doubtful_engine = DoubtfulTimingEngine()

    def resolve_timing_for_prediction(
        self, 
        p: LKPrediction, 
        context: UnifiedAstrologicalContext
    ) -> Dict[str, Any]:
        """
        DEEP MODULE: The primary interface for predictions to resolve their timing.
        Hides domain mapping and confidence calculation complexity.
        """
        d_lower = p.domain.lower()
        engine_domain = next((v for k, v in TIMING_DOMAIN_MAP.items() if k in d_lower), None)
        
        if not engine_domain:
            return {
                "confidence": "Low",
                "prohibited": False,
                "reason": "Unknown domain for timing analysis.",
                "triggers": [],
                "warnings": []
            }
            
        return self.get_timing_confidence(context, engine_domain)


    def check_age_gates(self, context: UnifiedAstrologicalContext, domain: str) -> Tuple[bool, str]:
        """
        Checks if the given age is prohibited for the specified domain based on Natal placements.
        Returns (is_prohibited, reason).
        """
        gates = self.age_gates.get(domain, [])
        if not gates:
            return False, ""
            
        natal_pos = {p: context.get_natal_house(p) for p in self.PLANET_MAP.values()}
        # remove Nones
        natal_pos = {k: v for k, v in natal_pos.items() if v is not None}
        age = context.age
        
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

    def evaluate_special_destruction(self, context: UnifiedAstrologicalContext) -> List[str]:
        """
        Evaluates the Sequential Impact Rule (Nisht Grah) from Lal Diary.
        """
        warnings = []
        natal_pos = {p: context.get_natal_house(p) for p in self.PLANET_MAP.values()}
        natal_pos = {k: v for k, v in natal_pos.items() if v is not None}
        annual_pos = {p: context.get_house(p) for p in self.PLANET_MAP.values()}
        annual_pos = {k: v for k, v in annual_pos.items() if v is not None}
        
        rule = self.special_logic.get("sequential_impact_rule", {})
        n_house = rule.get("natal_house")
        a_houses = rule.get("annual_houses", [])
        
        for p, n_h in natal_pos.items():
            if n_h == n_house:
                a_h = annual_pos.get(p)
                if a_h in a_houses:
                    warnings.append(f"Sequential Impact Rule triggered: {p} moved from Natal H8 to Annual H{a_h}. Negates positive effects of this house.")
                    
        return warnings

    def evaluate_rashi_phal_triggers(self, context: UnifiedAstrologicalContext, domain: str) -> List[Dict[str, Any]]:
        """
        Evaluate a given year for deterministic Rashi Phal triggers based purely on thermodynamic state changes.
        Accepts context (UnifiedAstrologicalContext) or a dict for backward compatibility.
        """
        triggers = []

        doubtful_promises = self.doubtful_engine._identify_doubtful_natal_promises(context)
        if not doubtful_promises:
            return triggers

        volatile_planets = set()
        for p in doubtful_promises:
            for planet in p.get("planets", []):
                volatile_planets.add(planet)

        # 2. Check the thermodynamic state (Activation) in the Annual Chart
        annual_pos = {p: context.get_house(p) for p in self.PLANET_MAP.values()}
        annual_pos = {k: v for k, v in annual_pos.items() if v is not None}

        for planet in volatile_planets:
            house = annual_pos.get(planet)
            if not house:
                continue
            # Filter by domain using strict Karaka mapping
            domains = KARAKA_DOMAIN_MAP.get(planet, [])
            if domain not in domains and domain not in [TIMING_DOMAIN_MAP.get(d) for d in domains]:
                continue
            # THE TRIGGER: Planetary Activation (Wake-Up)
            is_awake = context.is_awake(planet)
            if is_awake:
                # Filter 1: The "Dead Zone" Houses (Statistical Noise)
                if house in [4, 5, 10]:
                    continue
                state = context.get_complex_state(planet) if hasattr(context, 'get_complex_state') else type('dummy', (), {'is_startled': False, 'sustenance_factor': 1.0})()
                triggers.append({
                    "desc": f"[RASHI PHAL WAKE-UP] Doubtful {planet} lost dormancy and woke up in H{house}",
                    "sustenance_factor": getattr(state, 'sustenance_factor', 1.0),
                    "is_blocked": False,
                    "is_premature": not (context.check_maturity_age(planet) if hasattr(context, 'check_maturity_age') else False)
                })
        return triggers

    def evaluate_varshphal_triggers(self, context: UnifiedAstrologicalContext, domain: str) -> List[Dict[str, Any]]:
        """
        Evaluates the specific geometric triggers for a given domain.
        Returns a list of matched trigger rules.
        """
        domain_triggers = self.triggers.get(domain, [])
        if not domain_triggers:
            return []
            
        natal_pos = {p: context.get_natal_house(p) for p in self.PLANET_MAP.values()}
        natal_pos = {k: v for k, v in natal_pos.items() if v is not None}
        annual_pos = {p: context.get_house(p) for p in self.PLANET_MAP.values()}
        annual_pos = {k: v for k, v in annual_pos.items() if v is not None}
        age = context.age
        
        matches = []
        
        for rule in domain_triggers:
            match = True
            
            # ── DYNAMIC KEY EVALUATION ──────────────────────────────────────
            for key, val in rule.items():
                if key in ["desc", "polarity", "outcome", "target"]:
                    continue
                
                is_natal = key.startswith("natal_")
                is_annual = key.startswith("annual_")
                
                if not (is_natal or is_annual):
                    if key == "ven_mer_return":
                        v_return = (annual_pos.get("Venus") == natal_pos.get("Venus"))
                        m_return = (annual_pos.get("Mercury") == natal_pos.get("Mercury"))
                        if (v_return or m_return) != val: match = False
                    continue

                pos = natal_pos if is_natal else annual_pos
                sub_key = key.replace("natal_", "").replace("annual_", "")
                
                # Handle complex combined keys
                if sub_key == "ven_mer":
                    if pos.get("Venus") not in val and pos.get("Mercury") not in val: match = False
                elif sub_key == "jup_mon":
                    if isinstance(val, bool):
                        if (pos.get("Jupiter") == pos.get("Moon")) != val: match = False
                    else:
                        if pos.get("Jupiter") not in val or pos.get("Moon") not in val: match = False
                elif sub_key == "sun_sat":
                    if (pos.get("Sun") == pos.get("Saturn")) != val: match = False
                elif sub_key == "mer_mon":
                    if pos.get("Mercury") not in val or pos.get("Moon") not in val: match = False
                elif sub_key == "jup_sat":
                    if pos.get("Jupiter") not in val or pos.get("Saturn") not in val: match = False
                elif sub_key == "ven_mer_conjoined":
                    if (pos.get("Venus") == pos.get("Mercury")) != val: match = False
                elif sub_key == "mon_ven_conjoined":
                    if (pos.get("Moon") == pos.get("Venus")) != val: match = False
                elif sub_key == "2_7_blank":
                    occupied = list(pos.values())
                    if (2 not in occupied and 7 not in occupied) != val: match = False
                elif sub_key == "8_empty":
                    if (8 not in pos.values()) != val: match = False
                elif sub_key == "mer_alone":
                    h = pos.get("Mercury")
                    if h not in val: match = False
                    elif sum(1 for p, house in pos.items() if house == h) > 1: match = False
                elif sub_key == "sun_mon_mer_conjoined":
                    h = pos.get("Mercury")
                    if h not in val: match = False
                    elif pos.get("Sun") != h or pos.get("Moon") != h: match = False
                elif sub_key == "enemies_in_2_7":
                    enemies = [pos.get("Sun"), pos.get("Moon"), pos.get("Rahu")]
                    has_enemies = any(e in [2, 7] for e in enemies)
                    if has_enemies != val: match = False
                elif sub_key == "ket_sat_rah":
                    k = pos.get("Ketu"); s = pos.get("Saturn"); r = pos.get("Rahu")
                    if k not in val or (s not in val and r not in val): match = False
                elif sub_key == "rah_mon_sun":
                    if pos.get("Rahu") not in val and pos.get("Moon") not in val and pos.get("Sun") not in val: match = False
                else:
                    # Standard single planet house check
                    abbr = sub_key.capitalize()
                    p_name = self.PLANET_MAP.get(abbr)
                    if p_name:
                        if isinstance(val, bool):
                            if (p_name in pos) != val: match = False
                        elif pos.get(p_name) not in val: match = False
            # ────────────────────────────────────────────────────────────────
            
            if match:
                # C-1 FIX: Work on a shallow copy so the shared module-level constant
                # VARSHPHAL_TIMING_TRIGGERS is never mutated between calls.
                matched_rule = dict(rule)

                # Extract primary planets involved
                primary_planets = set()
                for key in rule.keys():
                    if key.startswith("natal_") or key.startswith("annual_"):
                        for part in key.split("_"):
                            abbr = part.capitalize()
                            if abbr in self.PLANET_MAP:
                                primary_planets.add(self.PLANET_MAP[abbr])
                    elif key == "ven_mer_return":
                        primary_planets.update(["Venus", "Mercury"])

                is_blocked = False
                is_premature = False
                sustenance_factor = 1.0
                complex_states = {}

                for p in primary_planets:
                    h = annual_pos.get(p)
                    if h:
                        # Use UnifiedAstrologicalContext for complex state
                        state = context.get_complex_state(p)
                        complex_states[p] = state

                        if not state.is_awake:
                            is_blocked = True
                            matched_rule["desc"] = f"[SUPPRESSED: DORMANT] {matched_rule.get('desc')}"
                            break

                        # 180-Degree enemy block
                        if context.has_180_degree_block(p):
                            is_blocked = True
                            matched_rule["desc"] = f"[SUPPRESSED: 180-DEG ENEMY] {matched_rule.get('desc')}"
                            break

                        # Apply sustenance factor (Leakage Principle)
                        # We take the minimum sustenance among involved planets for safety
                        sustenance_factor = min(sustenance_factor, state.sustenance_factor)

                        if state.is_startled:
                            matched_rule["desc"] = f"[STARTLED] {matched_rule.get('desc')}"

                for p in primary_planets:
                    if not context.check_maturity_age(p):
                        is_premature = True
                        matched_rule["desc"] = f"[PREMATURE: {p} < Maturity] {matched_rule.get('desc')}"

                matched_rule["is_blocked"] = is_blocked
                matched_rule["is_premature"] = is_premature
                matched_rule["sustenance_factor"] = sustenance_factor
                matches.append(matched_rule)
                
        return matches

    def get_timing_confidence(self, context: UnifiedAstrologicalContext, domain: str) -> Dict[str, Any]:
        """
        Main entry point. Assembles age gates, special destruction, and Varshphal triggers.
        Returns a confidence score and metadata.
        """
        is_prohibited, reason = self.check_age_gates(context, domain)
        if is_prohibited:
            return {
                "confidence": "None",
                "prohibited": True,
                "reason": reason,
                "triggers": [],
                "warnings": []
            }
            
        warnings = self.evaluate_special_destruction(context)
        geometric_triggers = self.evaluate_varshphal_triggers(context, domain)
        rashi_phal_triggers = self.evaluate_rashi_phal_triggers(context, domain)
        
        triggers = geometric_triggers + rashi_phal_triggers
        
        valid_triggers = [t for t in triggers if not t.get("is_blocked")]
        
        # Calculate Effective Trigger Count based on Sustenance Factor
        # A trigger with 0.6 sustenance only counts as 0.6 of a trigger.
        effective_count = sum(t.get("sustenance_factor", 1.0) for t in valid_triggers)
        has_leakage = any(t.get("sustenance_factor", 1.0) < 1.0 for t in valid_triggers)
        
        confidence = "Low"
        if effective_count >= 1.5:
            confidence = "High"
        elif effective_count >= 0.8:
            confidence = "Medium"
        else:
            confidence = "Low"
            
        # The Leakage Principle: Hard cap at Medium if sustenance is missing
        if has_leakage and confidence == "High":
            confidence = "Medium"
            
        # ── SYSTEM FRICTION (LEADGER TRAUMA) ─────────────────────────────
        # If the cumulative trauma in the ledger is high, reduce confidence.
        friction_signal = None
        if context.ledger:
            # Average leakage across all 9 planets
            net_multiplier = sum(context.ledger.get_leakage_multiplier(p) for p in context.ledger.planets) / 9.0
            if net_multiplier < 0.5:
                confidence = "Low"
                friction_signal = f"SYSTEM FRICTION: High cumulative trauma (Net: {net_multiplier:.2f})"
        # ─────────────────────────────────────────────────────────────
            
        # Add sustenance warnings
        for t in valid_triggers:
            sf = t.get("sustenance_factor", 1.0)
            if sf < 1.0:
                warnings.append(f"Result Leakage (H2 Blank/Afflicted): {t['desc']} (Sustenance: {sf})")
                
        # Add premature warnings
        for t in valid_triggers:
            if t.get("is_premature"):
                warnings.append(f"Premature Activation Trap: {t['desc']}")
            
        if friction_signal:
            warnings.append(friction_signal)
            
        return {
            "confidence": confidence,
            "prohibited": False,
            "reason": f"Age gates passed. Effective Trigger Score: {effective_count:.2f}" + (f" | {friction_signal}" if friction_signal else ""),
            "triggers": [t["desc"] for t in valid_triggers],
            "warnings": warnings,
            "raw_matches": valid_triggers,
            "friction_signal": friction_signal
        }
