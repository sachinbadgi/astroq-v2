from typing import Any, Dict, List, Tuple, Optional
from .lk_pattern_constants import (
    VARSHPHAL_TIMING_TRIGGERS,
    VARSHPHAL_AGE_GATES,
    VARSHPHAL_SPECIAL_LOGIC,
    CYCLE_DOMAIN_KARAKAS,
    EVENT_DOMAIN_CATALOGUE,
)
from .state_ledger import StateLedger
from .data_contracts import LKPrediction
from .astrological_context import UnifiedAstrologicalContext
from .doubtful_timing_engine import DoubtfulTimingEngine
from .lk_constants import TIMING_DOMAIN_MAP, KARAKA_DOMAIN_MAP, PLANET_EFFECTIVE_AGES, get_35_year_ruler

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
        self.test_mode = False
        self.doubtful_engine = DoubtfulTimingEngine()
        from .pattern_matcher import PatternMatcher
        from .dignity_engine import DignityEngine
        self.matcher = PatternMatcher()
        self.dignity_engine = DignityEngine()

    def check_cycle_domain_gate(self, context: UnifiedAstrologicalContext, age: int, domain: str) -> Tuple[bool, float]:
        """
        Returns (is_suppressed, cycle_modifier).

        Lal Kitab 35-Year Cycle Gate:
        - Suppresses domains whose karaka planets have not yet reached maturity age.
          e.g. Marriage (Venus=25, Moon=24) is suppressed before age 24.
        - Applies a cycle modifier to effective_count:
            Cycle 1 (1-35): 1.0x baseline
            Cycle 2 (36-70): 1.2x (promises consolidate in middle life)
            Cycle 3 (71+): 0.4x (most domains attenuate in old age)
        - Boosts by 1.3x if the current 35-yr sub-period ruler IS a karaka for this domain.

        Note: cycle modifiers are trial-and-error starting values configurable via model_defaults.json.
        """
        from .tracer import trace_hit
        trace_hit("lk_prediction_varshphal_timing_engine_varshphaltimingengine_check_cycle_domain_gate")
        karakas = CYCLE_DOMAIN_KARAKAS.get(domain, [])
        if karakas:
            maturity_ages = [PLANET_EFFECTIVE_AGES[p] for p in karakas if p in PLANET_EFFECTIVE_AGES]
            if maturity_ages and all(age < m for m in maturity_ages):
                return True, 0.0  # domain karaka not yet matured — suppress

        cycle = (age - 1) // 35 + 1  # 1 = 1–35, 2 = 36–70, 3 = 71+
        ruler = get_35_year_ruler(age)

        # Configurable trial-and-error modifiers
        cycle_1_mod = 1.0
        cycle_2_mod = 1.2
        cycle_3_mod = 0.4
        bonus_mod   = 1.3

        if getattr(context, 'config', None):
            cycle_1_mod = float(context.config.get("timing.cycle_1_modifier", fallback=1.0))
            cycle_2_mod = float(context.config.get("timing.cycle_2_modifier", fallback=1.2))
            cycle_3_mod = float(context.config.get("timing.cycle_3_modifier", fallback=0.4))
            bonus_mod   = float(context.config.get("timing.cycle_sub_period_bonus", fallback=1.3))

        modifier = cycle_1_mod if cycle == 1 else cycle_2_mod if cycle == 2 else cycle_3_mod

        # Sub-period ruler bonus
        if ruler in karakas:
            modifier *= bonus_mod

        return False, modifier

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
            
        # Dynamically determine the fate type (GRAHA_PHAL vs RASHI_PHAL)
        # to ensure the correct thresholds are applied.
        fate_type = "RASHI_PHAL"
        try:
            from .natal_fate_view import NatalFateView
            fate_view = NatalFateView()
            fate_type = fate_view.get_domain_fate(context, engine_domain)
        except Exception as e:
            pass # fallback to RASHI_PHAL

        return self.get_timing_confidence(
            context=context, 
            domain=engine_domain, 
            fate_type=fate_type, 
            age=context.age
        )


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
        Evaluate a given year for deterministic Rashi Phal triggers.

        Intervention 1 (Double-Confirmation Gate):
        A volatile planet waking up is necessary but NOT sufficient. The planet
        must also be in its Pakka Ghar in the annual chart — a dignity signal that
        separates genuine event years from ordinary transit noise.
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
            if context.is_awake(planet):
                # Filter 1: The "Dead Zone" Houses (Statistical Noise)
                if house in [4, 5, 10]:
                    continue

                # ── Dignity Ladder Gate ──────────────────────────────────────────
                dignity_score = self.dignity_engine.get_dignity_ladder_score(planet, house, context)
                
                # Hard suppression for debilitated planets
                if dignity_score < 0:
                    continue

                state = context.get_complex_state(planet)
                triggers.append({
                    "desc": f"[RASHI PHAL DIGNITY LADDER +{dignity_score}] Doubtful {planet} woke up with dignity in H{house}",
                    "sustenance_factor": getattr(state, 'sustenance_factor', 1.0),
                    "dignity_score": dignity_score,
                    "is_blocked": False,
                    "is_premature": not context.check_maturity_age(planet)
                })
        return triggers

    def evaluate_varshphal_triggers(self, context: UnifiedAstrologicalContext, domain: str) -> List[Dict[str, Any]]:
        """
        Evaluates the specific geometric triggers for a given domain.
        Returns a list of matched trigger rules.
        """
        from .tracer import trace_hit
        trace_hit("lk_prediction_varshphal_timing_engine_varshphaltimingengine_evaluate_varshphal_triggers")
        
        domain_triggers = self.triggers.get(domain, [])
        
        # In test_mode, we always include the catalogue fallbacks to ensure
        # we can verify reachability for all extracted domain rules.
        if not domain_triggers or self.test_mode:
            catalogue_triggers = self._get_catalogue_triggers(domain)
            # Avoid duplicates if we already have them
            existing_descs = {t.get("desc") for t in domain_triggers}
            for ct in catalogue_triggers:
                if ct.get("desc") not in existing_descs:
                    domain_triggers.append(ct)
            
            if catalogue_triggers and not domain_triggers:
                trace_hit("lk_prediction_varshphal_timing_engine_varshphaltimingengine_evaluate_catalogue_fallback")
        
        if not domain_triggers:
            return []
            
        natal_pos = {p: context.get_natal_house(p) for p in self.PLANET_MAP.values()}
        natal_pos = {k: v for k, v in natal_pos.items() if v is not None}
        annual_pos = {p: context.get_house(p) for p in self.PLANET_MAP.values()}
        annual_pos = {k: v for k, v in annual_pos.items() if v is not None}
        age = context.age
        
        matches = []
        
        for rule in domain_triggers:
            if self.matcher.matches(rule, context):
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

                        if not state.is_awake and not self.test_mode:
                            # ── Takkar Paradox Exemption ───────────────────────────
                            # On the 1-8 opposition axis (Takkar), dormancy does NOT block.
                            # The planet is struck precisely because it is weak.
                            from .aspect_engine import AspectEngine as _AE
                            _asp_eng = _AE()
                            _planet_houses = {k: {"house": v} for k, v in annual_pos.items()}
                            _aspects = _asp_eng.calculate_planet_aspects(p, h, _planet_houses)
                            is_takkar_axis = any(a.get("axis_type") == "TAKKAR" for a in _aspects)
                            # ────────────────────────────────────────────────────
                            if not is_takkar_axis and not self.test_mode:
                                is_blocked = True
                                matched_rule["desc"] = f"[SUPPRESSED: DORMANT] {matched_rule.get('desc')}"
                                break
                            else:
                                matched_rule["desc"] = f"[TAKKAR OVERRIDE: dormancy exempted] {matched_rule.get('desc')}"

                        # 180-Degree enemy block
                        if context.has_180_degree_block(p) and not self.test_mode:
                            is_blocked = True
                            matched_rule["desc"] = f"[SUPPRESSED: 180-DEG ENEMY] {matched_rule.get('desc')}"
                            break

                        # Apply sustenance factor (Leakage Principle)
                        # We take the minimum sustenance among involved planets for safety
                        sustenance_factor = min(sustenance_factor, state.sustenance_factor)

                        if state.is_startled:
                            matched_rule["desc"] = f"[STARTLED] {matched_rule.get('desc')}"

                for p in primary_planets:
                    if not context.check_maturity_age(p) and not self.test_mode:
                        is_premature = True
                        matched_rule["desc"] = f"[PREMATURE: {p} < Maturity] {matched_rule.get('desc')}"

                # ── Intervention 5: Aspect Suppression Hard-Block ─────────────────
                # If the planet's signed aspect total is deeply negative
                # (confrontation-dominated), suppress the trigger regardless of
                # geometric match. This blocks years that look structurally identical
                # but are qualitatively driven by hostile aspect energy.
                if not is_blocked:
                    asp_threshold = -2.0  # configurable default
                    if getattr(context, 'config', None):
                        try:
                            asp_threshold = float(
                                context.config.get("timing.aspect_suppression_threshold", fallback=-2.0)
                            )
                        except (TypeError, ValueError):
                            asp_threshold = -2.0

                    from .aspect_engine import AspectEngine
                    asp_engine = AspectEngine()
                    planet_house_dict = {k: {"house": v} for k, v in annual_pos.items()}
                    for p in primary_planets:
                        h = annual_pos.get(p)
                        if not h:
                            continue
                        aspects = asp_engine.calculate_planet_aspects(p, h, planet_house_dict)
                        asp_total = asp_engine.calculate_total_aspect_strength(aspects)
                        if asp_total < asp_threshold and not self.test_mode:
                            is_blocked = True
                            matched_rule["desc"] = (
                                f"[SUPPRESSED: ASP CONFLICT {asp_total:.1f}] {matched_rule.get('desc')}"
                            )
                            break
                # ─────────────────────────────────────────────────────────────────

                matched_rule["is_blocked"] = is_blocked
                matched_rule["is_premature"] = is_premature
                matched_rule["sustenance_factor"] = sustenance_factor
                matches.append(matched_rule)

        return matches

    def _get_catalogue_triggers(self, domain: str) -> List[Dict[str, Any]]:
        """
        Generates synthetic rules from EVENT_DOMAIN_CATALOGUE for reachability.
        """
        entry = next((e for e in EVENT_DOMAIN_CATALOGUE if e.get("domain") == domain), None)
        if not entry:
            return []
        
        primary_houses = entry.get("primary_houses", [])
        key_planets = entry.get("key_planets", [])
        
        # We generate a "primary occupancy" rule for each key planet
        rules = []
        for planet in key_planets:
            # Map planet name to abbreviation (e.g. "Sun" -> "sun")
            abbr = next((k for k, v in self.PLANET_MAP.items() if v == planet), None)
            if not abbr: continue
            
            rules.append({
                "desc": f"domain_primary_{domain}", # Must match rule_id in extractor
                f"annual_{abbr}": primary_houses,
                "outcome": f"Positive {domain} activation via {planet} in primary house",
                "polarity": 1
            })
        return rules

    def _compute_fidelity_multiplier(
        self,
        context: UnifiedAstrologicalContext,
        domain: str,
        fate_type: str,
        valid_triggers: List[Dict[str, Any]],
    ) -> float:
        """
        Mirrors FidelityGate logic at the timing-engine level.
        Returns a multiplier applied to effective_count.

        GRAHA_PHAL: conditional dampening for debilitation (×0.50) or all-dormant (×0.30).
        RASHI_PHAL: ×0.25 if 2-6 axis is active and no domain karaka planet is involved.
        """
        is_fixed = (fate_type == "GRAHA_PHAL")
        annual_pos = {
            p: context.get_house(p)
            for p in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
        }
        annual_pos = {k: v for k, v in annual_pos.items() if v is not None}

        if is_fixed:
            from .lk_constants import PLANET_DEBILITATION

            mult = 1.0

            # ── Dampen if any planet debilitated in annual chart ─────
            for planet, house in annual_pos.items():
                if house in PLANET_DEBILITATION.get(planet, []):
                    mult *= 0.50
                    break

            # ── Heavy dampen if all planets dormant ──────────────────
            if annual_pos:
                all_dormant = all(not context.is_awake(p) for p in annual_pos)
                if all_dormant:
                    mult *= 0.30

            return mult

        else:
            # ── RASHI_PHAL / HYBRID ────────────────────────────────────
            mult = 1.0

            # 2-6 axis domain-karaka gate: ×0.25 if no karaka planet involved
            trigger_descs = " ".join(t.get("desc", "") for t in valid_triggers)
            has_2_6 = ("2-6" in trigger_descs)
            if has_2_6:
                from .lk_pattern_constants import CYCLE_DOMAIN_KARAKAS
                karakas = CYCLE_DOMAIN_KARAKAS.get(domain, [])
                if karakas:
                    karaka_involved = any(k in annual_pos for k in karakas)
                    if not karaka_involved:
                        mult *= 0.90  # Soften karaka requirement further

            return mult

    def get_timing_confidence(self, context: UnifiedAstrologicalContext, domain: str, fate_type: str = "RASHI_PHAL", age: int = None) -> Dict[str, Any]:
        """
        Main entry point. Assembles age gates, special destruction, and Varshphal triggers.
        Returns a confidence score and metadata.

        Intervention 2: Confidence thresholds are configurable per fate type via
        model_defaults.json (timing.rashi_phal_medium_threshold etc.).
        Intervention 3: Maturity age window and boost magnitude are configurable.
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

        # ── 35-Year Cycle Domain Gate ─────────────────────────────────────────
        cycle_suppressed, cycle_modifier = self.check_cycle_domain_gate(context, age or 0, domain)
        if cycle_suppressed:
            return {
                "confidence": "Low",
                "prohibited": False,
                "reason": f"Domain '{domain}' suppressed: no karaka planet has reached maturity yet at age {age}.",
                "triggers": [],
                "warnings": [f"35-Year Cycle Gate: domain karaka not yet mature at age {age}"]
            }
        # ─────────────────────────────────────────────────────────────────────

        warnings = self.evaluate_special_destruction(context)
        geometric_triggers = self.evaluate_varshphal_triggers(context, domain)
        rashi_phal_triggers = self.evaluate_rashi_phal_triggers(context, domain)

        triggers = geometric_triggers + rashi_phal_triggers

        valid_triggers = [t for t in triggers if not t.get("is_blocked")]

        # Calculate Effective Trigger Count based on Dignity and Sustenance
        # Default dignity is 1.0 for geometric triggers.
        effective_count = sum(t.get("dignity_score", 1.0) * t.get("sustenance_factor", 1.0) for t in valid_triggers)

        # ── Intervention 3: Configurable Maturity Age Window & Boost ─────────
        is_fixed = (fate_type == "GRAHA_PHAL")
        maturity_boost = 0
        if age is not None:
            from .lk_pattern_constants import MATURITY_AGE_PATTERN
            maturity_ages = MATURITY_AGE_PATTERN.get("maturity_ages", {})

            mat_window        = 2
            mat_boost_fixed   = 0.8
            mat_boost_doubtful= 0.3
            if getattr(context, 'config', None):
                try:
                    mat_window        = int(context.config.get("timing.maturity_age_window",     fallback=2))
                    mat_boost_fixed   = float(context.config.get("timing.maturity_boost_fixed",  fallback=0.8))
                    mat_boost_doubtful= float(context.config.get("timing.maturity_boost_doubtful",fallback=0.3))
                except (TypeError, ValueError):
                    pass

            for planet, m_age in maturity_ages.items():
                if is_fixed:
                    if abs(age - m_age) <= mat_window:
                        maturity_boost = mat_boost_fixed
                        break
                else:
                    if age == m_age:
                        maturity_boost = mat_boost_doubtful
                        break
        # ─────────────────────────────────────────────────────────────────────

        effective_count += maturity_boost

        # Apply 35-year cycle modifier to effective trigger count
        effective_count *= cycle_modifier

        # ── FidelityGate-equivalent gating ──────────────────────────────────────
        # Mirrors FidelityGate logic operating at the RuleHit level,
        # applied here so both the fuzzer metrics and the main pipeline benefit.
        effective_count *= self._compute_fidelity_multiplier(
            context, domain, fate_type, valid_triggers
        )

        has_leakage = any(t.get("sustenance_factor", 1.0) < 1.0 for t in valid_triggers)
        rp_med  = 0.8
        rp_high = 1.5
        gp_med  = 0.6
        gp_high = 1.5
        if getattr(context, 'config', None):
            try:
                rp_med  = float(context.config.get("timing.rashi_phal_medium_threshold", fallback=1.2))
                rp_high = float(context.config.get("timing.rashi_phal_high_threshold",   fallback=2.0))
                gp_med  = float(context.config.get("timing.graha_phal_medium_threshold", fallback=0.6))
                gp_high = float(context.config.get("timing.graha_phal_high_threshold",   fallback=1.5))
            except (TypeError, ValueError):
                pass

        med_thresh  = gp_med  if is_fixed else rp_med
        high_thresh = gp_high if is_fixed else rp_high
        confidence = "Low"
        if effective_count >= high_thresh:
            confidence = "High"
        elif effective_count >= med_thresh:
            confidence = "Medium"
        # ─────────────────────────────────────────────────────────────────────

        # The Leakage Principle: Hard cap at Medium if sustenance is missing
        if has_leakage and confidence == "High":
            confidence = "Medium"

        # ── SYSTEM FRICTION (LEDGER TRAUMA) ───────────────────────────────────
        friction_signal = None
        if context.ledger:
            net_multiplier = sum(context.ledger.get_leakage_multiplier(p) for p in context.ledger.planets) / 9.0
            if net_multiplier < 0.5:
                # System Friction: Demote instead of forcing Low
                friction_signal = f"SYSTEM FRICTION: High cumulative trauma (Net: {net_multiplier:.2f})"
                if confidence == "High":
                    confidence = "Medium"
                elif confidence == "Medium":
                    confidence = "Low"
        # ─────────────────────────────────────────────────────────────────────

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
        }  # end get_timing_confidence
