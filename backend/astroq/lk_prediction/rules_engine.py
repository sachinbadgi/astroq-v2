"""
Module 4: Rules Engine.

Evaluates deterministic Lal Kitab rules against a parsed chart.
Rules are evaluated from an SQLite database containing JSON condition
trees (AND, OR, NOT, placement, conjunction, confrontation).
"""

from __future__ import annotations

import json
import logging
import sqlite3
import os
import traceback
from typing import Any

logger = logging.getLogger(__name__)

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
from astroq.lk_prediction.dignity_engine import DignityEngine
from astroq.lk_prediction.astrological_context import UnifiedAstrologicalContext
from astroq.lk_prediction.aspect_fidelity_evaluator import AspectFidelityEvaluator





class SqliteRuleRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def load_rules(self) -> list[dict]:
        con = sqlite3.connect(self.db_path)
        try:
            cur = con.execute("SELECT * FROM deterministic_rules")
            columns = [c[0] for c in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]
        except sqlite3.OperationalError:
            return []
        finally:
            con.close()

class RulesEngine:
    """
    Loads rules from a repository and evaluates them.

    Parameters
    ----------
    cfg_or_db_path : ModelConfig | str
        Either a ModelConfig instance or a path to the SQLite DB directly.
    repository : Object with a load_rules() -> list[dict] method
        Optional injected repository. If not provided, defaults to SqliteRuleRepository.
    """

    def __init__(self, cfg_or_db_path: ModelConfig | str, repository=None) -> None:
        if isinstance(cfg_or_db_path, str):
            self.db_path = cfg_or_db_path
            self.config = None
            self.boost_scaling = 0.04
            self.penalty_scaling = 0.15
        else:
            self.config = cfg_or_db_path
            self.db_path = cfg_or_db_path._db_path
            self.boost_scaling = cfg_or_db_path.get("rules.boost_scaling", fallback=0.04)
            self.penalty_scaling = cfg_or_db_path.get("rules.penalty_scaling", fallback=0.15)
            
            if not os.path.exists(self.db_path):
                default_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'data'))
                self.db_path = os.path.abspath(os.path.join(default_dir, "rules.db"))
            else:
                con = None
                try:
                    con = sqlite3.connect(self.db_path)
                    con.execute("SELECT 1 FROM deterministic_rules LIMIT 1")
                except sqlite3.OperationalError:
                    default_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'data'))
                    self.db_path = os.path.abspath(os.path.join(default_dir, "rules.db"))
                finally:
                    if con:
                        con.close()
        
        self.repository = repository or SqliteRuleRepository(self.db_path)
        # Cache rules once during init
        self._rules_cache = self.repository.load_rules()

    # ------------------------------------------------------------------
    # Dignity Modifier
    # ------------------------------------------------------------------


    def evaluate_chart(self, context: UnifiedAstrologicalContext | dict[str, Any]) -> list[RuleHit]:
        """
        Evaluate all rules in the database against the provided context.
        Accepts either a UnifiedAstrologicalContext or a raw chart dict
        (backward-compatible). Returns a list of matching RuleHit objects,
        sorted by specificity.
        """
        # Backward-compat: auto-wrap raw dicts
        if isinstance(context, dict):
            from astroq.lk_prediction.data_contracts import EnrichedChart
            context = UnifiedAstrologicalContext(enriched=EnrichedChart(source=context))

        hits: list[RuleHit] = []
        if not context.chart.planets:
            return hits

        for rule in self._rules_cache:
            rid = rule.get("rule_id") or rule.get("id", "")
            cond_str = rule.get("condition_json") or rule.get("condition", "{}")
            
            try:
                cond_tree = json.loads(cond_str)
                match, specificity, targets, target_houses = self._evaluate_node(cond_tree, context)
                
                if match:
                    # Parse targets and houses if they are strings in DB
                    primary_targets = list(targets)
                    if not primary_targets and rule.get("primary_target_planets"):
                        pt = rule.get("primary_target_planets")
                        primary_targets = json.loads(pt) if pt.startswith("[") else pt.split(",")

                    # Create RuleHit with raw data
                    hit = RuleHit(
                        rule_id=rid,
                        domain=rule.get("domain", ""),
                        description=rule.get("description", ""),
                        verdict=rule.get("verdict", ""),
                        magnitude=rule.get("magnitude"), # Raw magnitude, could be None
                        scoring_type=rule.get("scoring_type", "neutral"),
                        primary_target_planets=primary_targets,
                        target_houses=list(target_houses),
                        source_page=rule.get("source_page", ""),
                        specificity=specificity,
                        success_weight=rule.get("success_weight", 0.0),
                        afflicts_living=bool(rule.get("afflicts_living", False)),
                    )
                    
                    # Derive axis label from primary planet's aspect data
                    if len(hit.target_houses) >= 2:
                        hit.axis = AspectFidelityEvaluator.axis_from_houses(
                            hit.target_houses[0], hit.target_houses[1]
                        )
                    elif len(hit.target_houses) == 1 and primary_targets:
                        src_planet = primary_targets[0]
                        src_house = context.get_house(src_planet)
                        if src_house:
                            hit.axis = AspectFidelityEvaluator.axis_from_houses(
                                hit.target_houses[0], src_house
                            )
                    
                    hit.magnitude = context.calculate_rule_magnitude(hit)
                    
                    if abs(hit.magnitude) > 0.001:
                        hits.append(hit)

            except Exception as e:
                logger.error(f"Error evaluating rule {rid}: {e}")
                continue

        # Sort descending by specificity
        hits.sort(key=lambda h: h.specificity, reverse=True)
        return hits

    def _evaluate_node(self, node: dict, context: UnifiedAstrologicalContext) -> tuple[bool, int, set[str], set[int]]:
        """
        Recursive evaluator.
        Returns (is_match, specificity, target_planets, target_houses)
        """
        if not node or not isinstance(node, dict):
            return False, 0, set(), set()
            
        n_type = node.get("type", "")
        from .condition_evaluator import ConditionEvaluator as CE

        if n_type == "AND":
            spec_total = 0
            targets = set()
            houses = set()
            for sub in node.get("conditions", []):
                match, spec, targ, hs = self._evaluate_node(sub, context)
                if not match:
                    return False, 0, set(), set()
                spec_total += spec
                targets.update(targ)
                houses.update(hs)
            return True, spec_total, targets, houses

        elif n_type == "OR":
            for sub in node.get("conditions", []):
                match, spec, targ, hs = self._evaluate_node(sub, context)
                if match:
                    return True, spec, targ, hs
            return False, 0, set(), set()

        elif n_type == "NOT":
            match, _, _, _ = self._evaluate_node(node.get("condition", {}), context)
            if match:
                return False, 0, set(), set()
            return True, 1, set(), set()

        elif n_type == "current_age":
            if context.age == node.get("age"):
                return True, 1, set(), set()
            return False, 0, set(), set()

        elif n_type == "house_status":
            target_h = int(node.get("house", "1"))
            target_state = node.get("state", "occupied")
            occupied = (target_state == "occupied")
            
            if CE.evaluate_house_occupied(context, target_h, occupied):
                return True, 1, set(), {target_h}
            return False, 0, set(), set()

        elif n_type == "placement":
            planet = node.get("planet", "")
            target_houses = node.get("houses", [])
            
            if CE.evaluate_placement(context, planet, target_houses):
                actual_house = context.get_house(planet)
                return True, 1, {planet}, {actual_house} if actual_house else set()
            
            return False, 0, set(), set()

        elif n_type == "confrontation":
            p_a = node.get("planet_a", "")
            p_b = node.get("planet_b", "")
            
            if CE.evaluate_confrontation(context, p_a, p_b):
                h_a = context.get_house(p_a)
                h_b = context.get_house(p_b)
                return True, 1, {p_a, p_b}, {h_a, h_b}
            
            return False, 0, set(), set()

        return False, 0, set(), set()


        return False, 0, set(), set()
