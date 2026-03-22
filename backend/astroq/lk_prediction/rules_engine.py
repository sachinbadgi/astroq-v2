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
            # For testing without full config
            self.boost_scaling = 0.04
            self.penalty_scaling = 0.15
        else:
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
                default_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
                self.db_path = os.path.abspath(os.path.join(default_dir, "rules.db"))
            finally:
                if 'con' in locals():
                    con.close()

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

        # Fetch all rules
        con = sqlite3.connect(self.db_path)
        try:
            # We assume the table is deterministic_rules
            cur = con.execute("SELECT * FROM deterministic_rules")
            columns = [c[0] for c in cur.description]
            rules = [dict(zip(columns, row)) for row in cur.fetchall()]
        except sqlite3.OperationalError:
            # Table doesn't exist (e.g. empty or uninitialized DB)
            return []
        finally:
            con.close()

        for rule in rules:
            try:
                cond_tree = json.loads(rule.get("condition", "{}"))
            except json.JSONDecodeError:
                continue

            match, specificity, targets, target_houses = self._evaluate_node(cond_tree, planets_data)

            if match:
                scoring_type = rule.get("scoring_type", "neutral")
                base = self.boost_scaling if scoring_type == "boost" else self.penalty_scaling
                mag = apply_scale_to_magnitude(rule.get("scale", "minor"), base)

                hit = RuleHit(
                    rule_id=rule.get("id", ""),
                    domain=rule.get("domain", ""),
                    description=rule.get("description", ""),
                    verdict=rule.get("verdict", ""),
                    magnitude=mag,
                    scoring_type=scoring_type,
                    primary_target_planets=list(targets),
                    target_houses=list(target_houses),
                    source_page=rule.get("source_page", ""),
                    specificity=specificity,
                    success_weight=rule.get("success_weight", 0.0),
                )
                hits.append(hit)

        # Sort descending by specificity
        hits.sort(key=lambda h: h.specificity, reverse=True)
        return hits

    def _evaluate_node(self, node: dict, pd: dict) -> tuple[bool, int, set[str], set[int]]:
        """
        Recursive evaluator.
        Returns (is_match, specificity, target_planets, target_houses)
        """
        if not node or not isinstance(node, dict):
            return False, 0, set(), set()
            
        n_type = node.get("type", "")

        if n_type == "AND":
            spec_total = 0
            targets = set()
            houses = set()
            for sub in node.get("conditions", []):
                match, spec, targ, hs = self._evaluate_node(sub, pd)
                if not match:
                    return False, 0, set(), set()
                spec_total += spec
                targets.update(targ)
                houses.update(hs)
            return True, spec_total, targets, houses

        elif n_type == "OR":
            for sub in node.get("conditions", []):
                match, spec, targ, hs = self._evaluate_node(sub, pd)
                if match:
                    # Specificity in OR is just the max of passing
                    return True, spec, targ, hs
            return False, 0, set(), set()

        elif n_type == "NOT":
            match, _, _, _ = self._evaluate_node(node.get("condition", {}), pd)
            if match:
                return False, 0, set(), set()
            # If NOT passes, it has a base specificity of 1
            return True, 1, set(), set()

        elif n_type == "placement":
            planet = node.get("planet", "")
            target_h = node.get("houses", [])
            data = pd.get(planet)
            if data and data.get("house") in target_h:
                return True, 1, {planet}, {data.get("house")}
            return False, 0, set(), set()

        elif n_type == "confrontation":
            p_a = node.get("planet_a", "")
            p_b = node.get("planet_b", "")
            
            # Check if p_a aspects p_b or vice versa with "100 Percent"
            data_a = pd.get(p_a, {})
            data_b = pd.get(p_b, {})
            house_b = data_b.get("house")
            house_a = data_a.get("house")

            # Check if A -> B
            for asp in data_a.get("aspects", []):
                if asp.get("aspect_type") == "100 Percent" and (asp.get("house") == house_b or asp.get("aspecting_planet") == p_b):
                    return True, 1, {p_a, p_b}, {house_a, house_b} if house_a and house_b else set()

            # Check if B -> A
            for asp in data_b.get("aspects", []):
                if asp.get("aspect_type") == "100 Percent" and (asp.get("house") == house_a or asp.get("aspecting_planet") == p_a):
                    return True, 1, {p_a, p_b}, {house_a, house_b} if house_a and house_b else set()

            return False, 0, set(), set()

        return False, 0, set(), set()
