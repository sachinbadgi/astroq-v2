"""
Module 4: Rules Engine.

Evaluates deterministic Lal Kitab rules against a parsed chart.
Rules are evaluated from an SQLite database containing JSON condition
trees (AND, OR, NOT, placement, conjunction, confrontation).
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.data_contracts import RuleHit
from astroq.lk_prediction.lk_constants import (
    PLANET_PAKKA_GHAR,
    PLANET_EXALTATION,
    PLANET_DEBILITATION,
    VARSHPHAL_YEAR_MATRIX,
    ENEMIES,
    get_35_year_ruler,
)


def apply_scale_to_magnitude(scale: str, base_scaling: float) -> float:
    """
    Scale multipliers mapping:
    minor -> x1
    moderate -> x2
    major -> x3
    extreme / deterministic -> x4
    """
    sc = scale.lower()
    if sc == "minor": return base_scaling * 1.0
    if sc == "moderate": return base_scaling * 2.0
    if sc == "major": return base_scaling * 3.0
    if sc in ("extreme", "deterministic"): return base_scaling * 4.0
    return base_scaling * 1.0


class RulesEngine:
    """
    Loads rules from a SQLite database and evaluates them.

    Parameters
    ----------
    config_or_db_path : ModelConfig | str
        Either a ModelConfig instance or a path to the SQLite DB directly.
    """

    def __init__(self, cfg_or_db_path: ModelConfig | str) -> None:
        if isinstance(cfg_or_db_path, str):
            self.db_path = cfg_or_db_path
            self.config = None
            # For testing without full config
            self.boost_scaling = 0.04
            self.penalty_scaling = 0.15
        else:
            self.config = cfg_or_db_path
            self.db_path = cfg_or_db_path._db_path
            self.boost_scaling = cfg_or_db_path.get("rules.boost_scaling", fallback=0.04)
            self.penalty_scaling = cfg_or_db_path.get("rules.penalty_scaling", fallback=0.15)
            
            # Check if deterministic_rules table exists in this DB (e.g. for tests)
            # If not, use the global rules.db
            import sqlite3
            import os
            try:
                con = sqlite3.connect(self.db_path)
                con.execute("SELECT 1 FROM deterministic_rules LIMIT 1")
            except sqlite3.OperationalError:
                default_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'data'))
                self.db_path = os.path.abspath(os.path.join(default_dir, "rules.db"))
            finally:
                if 'con' in locals():
                    con.close()
        
        # Cache rules once during init
        self._rules_cache = self._load_rules()

    def _load_rules(self) -> list[dict]:
        """Load all rules from SQLite once."""
        con = sqlite3.connect(self.db_path)
        try:
            # We assume the table is deterministic_rules
            cur = con.execute("SELECT * FROM deterministic_rules")
            columns = [c[0] for c in cur.description]
            res = [dict(zip(columns, row)) for row in cur.fetchall()]
            if res:
                print(f"  RulesEngine: loaded {len(res)} rules. Columns: {columns}", flush=True)
            return res
        except sqlite3.OperationalError:
            # Table doesn't exist (e.g. empty or uninitialized DB)
            return []
        finally:
            con.close()

    # ------------------------------------------------------------------
    # Dignity Modifier
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_dignity_modifier(
        planet: str,
        natal_house: int,
        age: int,
    ) -> float:
        """
        Compute an annual dignity multiplier for a planet based on where it
        lands in the Varshphal rotation at a given age.

        The annual house is derived from:
            VARSHPHAL_YEAR_MATRIX[age][natal_house]

        Then compared against:
            PLANET_PAKKA_GHAR   → 1.25  (home, fully empowered)
            PLANET_EXALTATION   → 1.15  (peak form)
            PLANET_DEBILITATION → 0.75  (weakened, struggling)
            ENEMIES houses      → 0.85  (enemy territory, friction)
            Otherwise           → 1.0   (neutral)

        Returns 1.0 if any input is missing or planet is not in the matrix.
        """
        year_map = VARSHPHAL_YEAR_MATRIX.get(age)
        if not year_map or not natal_house:
            return 1.0

        annual_house = year_map.get(natal_house)
        if not annual_house:
            return 1.0

        # Pakka Ghar — strongest positive signal
        if PLANET_PAKKA_GHAR.get(planet) == annual_house:
            return 1.25

        # Exaltation — peak performance
        if annual_house in PLANET_EXALTATION.get(planet, []):
            return 1.15

        # Debilitation — planet struggling
        if annual_house in PLANET_DEBILITATION.get(planet, []):
            return 0.75

        # Enemy territory — identify which planet owns that house (Fixed House Lords)
        # and check if they are an enemy of this planet.
        # Approximate: check if the annual house is in an enemy's Pakka Ghar territory.
        for enemy in ENEMIES.get(planet, []):
            if PLANET_PAKKA_GHAR.get(enemy) == annual_house:
                return 0.85

        return 1.0

    def evaluate_chart(self, chart: dict[str, Any]) -> list[RuleHit]:
        """
        Evaluate all rules in the database against *chart*.

        Returns a list of matching RuleHit objects, sorted by specificity
        (highest first).
        """
        hits: list[RuleHit] = []
        planets_data = chart.get("planets_in_houses", {})
        if not planets_data:
            return hits

        for rule in self._rules_cache:
            # Flexible key mapping for different DB schemas
            rid = rule.get("rule_id") or rule.get("id", "")
            cond_str = rule.get("condition_json") or rule.get("condition", "{}")
            
            try:
                cond_tree = json.loads(cond_str)
            except json.JSONDecodeError:
                continue

            match, specificity, targets, target_houses = self._evaluate_node(cond_tree, planets_data, chart)
            
            if match:
                scoring_type = rule.get("scoring_type", "neutral")
                # Use magnitude from DB if available, else use scale-based scaling
                mag = rule.get("magnitude")
                
                # CHECK OVERRIDES: If researcher has muted this rule, skip or adjust
                if hasattr(self, 'config') and self.config:
                    override_key = f"weight.{rid}"
                    w = self.config.get(override_key)
                    if w is not None:
                        if float(w) <= 0.01:
                            continue # Muted False Positive
                        mag = (mag if mag is not None else 1.0) * float(w)

                if mag is None:
                    base = self.boost_scaling if scoring_type == "boost" else self.penalty_scaling
                    mag = apply_scale_to_magnitude(rule.get("scale", "minor"), base)

                # ── ANNUAL DIGNITY MODIFIER ──────────────────────────────────
                # For Yearly charts, scale magnitude by how well each triggering
                # planet is dignified in that specific annual position.
                # Natal (Birth) charts always get modifier=1.0 (no change).
                age = chart.get("chart_period", 0)
                natal_positions = chart.get("_natal_positions", {})
                if natal_positions and age and targets:
                    # Average modifier across all planets that triggered this rule
                    planet_modifiers = []
                    for p in targets:
                        # Strip "Masnui " prefix if present — use base planet name for lookup
                        base_name = p.replace("Masnui ", "") if p.startswith("Masnui ") else p
                        natal_h = natal_positions.get(base_name)
                        if natal_h:
                            planet_modifiers.append(
                                self._compute_dignity_modifier(base_name, natal_h, age)
                            )
                    if planet_modifiers:
                        avg_modifier = sum(planet_modifiers) / len(planet_modifiers)
                        mag = mag * avg_modifier
                # ────────────────────────────────────────────────────────────

                # ── 35-YEAR CYCLE RULER MODIFIER ─────────────────────────────
                # If the current period ruler is one of the rule's triggering
                # planets → boost (ruler is "in charge" and delivering this rule).
                # If the period ruler is an enemy of the triggering planets
                # → friction (rulership working against the rule's planets).
                if age and targets:
                    cycle_ruler = get_35_year_ruler(age)
                    base_names = {
                        (p.replace("Masnui ", "") if p.startswith("Masnui ") else p)
                        for p in targets
                    }
                    if cycle_ruler in base_names:
                        mag *= 1.20   # period ruler is delivering this rule
                    elif any(cycle_ruler in ENEMIES.get(p, []) for p in base_names):
                        mag *= 0.85   # period ruler is hostile to this rule's planets
                # ─────────────────────────────────────────────────────────────

                # Parse targets and houses if they are strings in DB
                primary_targets = targets
                if not primary_targets and rule.get("primary_target_planets"):
                    pt = rule.get("primary_target_planets")
                    primary_targets = json.loads(pt) if pt.startswith("[") else pt.split(",")

                hit = RuleHit(
                    rule_id=rid,
                    domain=rule.get("domain", ""),
                    description=rule.get("description", ""),
                    verdict=rule.get("verdict", ""),
                    magnitude=mag,
                    scoring_type=scoring_type,
                    primary_target_planets=list(primary_targets),
                    target_houses=list(target_houses),
                    source_page=rule.get("source_page", ""),
                    specificity=specificity,
                    success_weight=rule.get("success_weight", 0.0),
                )
                hits.append(hit)

        # Sort descending by specificity
        hits.sort(key=lambda h: h.specificity, reverse=True)
        return hits

    def _evaluate_node(self, node: dict, pd: dict, chart: dict) -> tuple[bool, int, set[str], set[int]]:
        """
        Recursive evaluator.
        Returns (is_match, specificity, target_planets, target_houses)
        """
        if not node or not isinstance(node, dict):
            return False, 0, set(), set()
            
        n_type = node.get("type", "")
        # Get global age from chart
        current_age = chart.get("chart_period", 0)

        if n_type == "AND":
            spec_total = 0
            targets = set()
            houses = set()
            for sub in node.get("conditions", []):
                match, spec, targ, hs = self._evaluate_node(sub, pd, chart)
                if not match:
                    return False, 0, set(), set()
                spec_total += spec
                targets.update(targ)
                houses.update(hs)
            return True, spec_total, targets, houses

        elif n_type == "OR":
            for sub in node.get("conditions", []):
                match, spec, targ, hs = self._evaluate_node(sub, pd, chart)
                if match:
                    # Specificity in OR is just the max of passing
                    return True, spec, targ, hs
            return False, 0, set(), set()

        elif n_type == "NOT":
            match, _, _, _ = self._evaluate_node(node.get("condition", {}), pd, chart)
            if match:
                return False, 0, set(), set()
            # If NOT passes, it has a base specificity of 1
            return True, 1, set(), set()

        elif n_type == "current_age":
            target_age = node.get("age")
            if current_age == target_age:
                return True, 1, set(), set()
            return False, 0, set(), set()

        elif n_type == "house_status":
            target_h = str(node.get("house", "1"))
            target_state = node.get("state", "occupied")
            
            # Check house_status dict in chart
            status_map = chart.get("house_status") or {}
            actual_state = status_map.get(target_h, "Empty House").lower()
            
            is_match = False
            if target_state == "occupied" and "Occupied" in actual_state.title():
                is_match = True
            elif target_state == "empty" and "Empty" in actual_state.title():
                is_match = True
                
            if is_match:
                return True, 1, set(), {int(target_h)}
            return False, 0, set(), set()

        elif n_type == "placement":
            planet = node.get("planet", "")
            target_h = node.get("houses", [])
            
            # Check for exact match or Masnui version
            data = pd.get(planet)
            if not data:
                masnui_name = f"Masnui {planet}"
                data = pd.get(masnui_name)
                if data:
                    planet = masnui_name # For target reporting
            
            if data and data.get("house") in target_h:
                return True, 1, {planet}, {data.get("house")}
            
            return False, 0, set(), set()

        elif n_type == "confrontation":
            p_a = node.get("planet_a", "")
            p_b = node.get("planet_b", "")
            
            # Helper to find data (handles Masnui)
            def _find_p_data(name):
                d = pd.get(name)
                if d: return name, d
                m_name = f"Masnui {name}"
                return (m_name, pd.get(m_name)) if m_name in pd else (name, None)

            real_a_name, data_a = _find_p_data(p_a)
            real_b_name, data_b = _find_p_data(p_b)
            
            if not data_a or not data_b:
                return False, 0, set(), set()
                
            house_b = data_b.get("house")
            house_a = data_a.get("house")

            # Check if A -> B
            for asp in data_a.get("aspects", []):
                if asp.get("aspect_type") == "100 Percent" and (asp.get("target") == real_b_name or asp.get("target_house") == house_b):
                    return True, 1, {real_a_name, real_b_name}, {house_a, house_b} if house_a and house_b else set()

            # Check if B -> A
            for asp in data_b.get("aspects", []):
                if asp.get("aspect_type") == "100 Percent" and (asp.get("target") == real_a_name or asp.get("target_house") == house_a):
                    return True, 1, {real_a_name, real_b_name}, {house_a, house_b} if house_a and house_b else set()

            return False, 0, set(), set()

        return False, 0, set(), set()
