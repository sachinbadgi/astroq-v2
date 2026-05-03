import ast
import json
import os
from typing import List, Dict, Any, Set

class RuleConstraint:
    def __init__(self, planet: str, houses: List[int], chart_type: str = "annual", relationship: str = "placement"):
        self.planet = planet
        self.houses = houses
        self.chart_type = chart_type # "annual" or "natal"
        self.relationship = relationship

    def to_dict(self):
        return {
            "planet": self.planet,
            "houses": self.houses,
            "chart_type": self.chart_type,
            "relationship": self.relationship
        }

class ExtractedRule:
    def __init__(self, rule_id: str, domain: str, constraints: List[RuleConstraint], node_id: str, description: str = ""):
        self.rule_id = rule_id
        self.domain = domain
        self.constraints = constraints
        self.node_id = node_id
        self.description = description

    def to_dict(self):
        return {
            "rule_id": self.rule_id,
            "domain": self.domain,
            "node_id": self.node_id,
            "description": self.description,
            "constraints": [c.to_dict() for c in self.constraints]
        }

class RuleExtractor:
    """
    Parses lk_pattern_constants.py to extract semantic rules and their constraints.
    """
    
    PLANET_MAP = {
        "sat": "Saturn", "ket": "Ketu", "mer": "Mercury", "mon": "Moon", 
        "jup": "Jupiter", "sun": "Sun", "rah": "Rahu", "ven": "Venus", "mar": "Mars"
    }

    # Node ID Mapping
    NODE_MAPPING = {
        "VARSHPHAL_TIMING_TRIGGERS": "lk_prediction_varshphal_timing_engine_varshphaltimingengine_evaluate_varshphal_triggers",
        "EVENT_DOMAIN_CATALOGUE": "lk_prediction_varshphal_timing_engine_varshphaltimingengine_evaluate_varshphal_triggers"
    }

    def __init__(self, constants_path: str):
        self.constants_path = constants_path
        self.extracted_rules: List[ExtractedRule] = []

    def extract(self):
        if not os.path.exists(self.constants_path):
            raise FileNotFoundError(f"Constants file not found: {self.constants_path}")

        with open(self.constants_path, "r") as f:
            tree = ast.parse(f.read())

        for node in tree.body:
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                target = node.targets[0] if isinstance(node, ast.Assign) else node.target
                if isinstance(target, ast.Name):
                    if target.id == "VARSHPHAL_TIMING_TRIGGERS":
                        self._parse_timing_triggers(node.value)
                    elif target.id == "EVENT_DOMAIN_CATALOGUE":
                        self._parse_event_catalogue(node.value)
        
        return self.extracted_rules

    def _parse_timing_triggers(self, node: ast.Dict):
        node_id = self.NODE_MAPPING["VARSHPHAL_TIMING_TRIGGERS"]
        for key, value in zip(node.keys, node.values):
            if not isinstance(key, ast.Constant): continue
            domain = key.value
            if isinstance(value, ast.List):
                for rule_node in value.elts:
                    if isinstance(rule_node, ast.Dict):
                        self._parse_single_rule(domain, rule_node, node_id)

    def _parse_event_catalogue(self, node: ast.List):
        node_id = self.NODE_MAPPING["EVENT_DOMAIN_CATALOGUE"]
        for item in node.elts:
            if isinstance(item, ast.Dict):
                data = {}
                for k, v in zip(item.keys, item.values):
                    if isinstance(k, ast.Constant):
                        data[k.value] = self._get_value(v)
                
                domain = data.get("domain", "unknown")
                primary_houses = data.get("primary_houses", [])
                key_planets = data.get("key_planets", [])
                
                if primary_houses and key_planets:
                    constraints = []
                    for planet in key_planets:
                        constraints.append(RuleConstraint(planet, primary_houses, "annual", "placement"))
                    
                    self.extracted_rules.append(ExtractedRule(
                        rule_id=f"domain_primary_{domain}",
                        domain=domain,
                        constraints=constraints,
                        node_id=node_id,
                        description=f"Primary occupancy for {domain}"
                    ))

    def _parse_single_rule(self, domain: str, rule_node: ast.Dict, node_id: str):
        rule_data = {}
        for k, v in zip(rule_node.keys, rule_node.values):
            if isinstance(k, ast.Constant):
                val = self._get_value(v)
                rule_data[k.value] = val

        desc = rule_data.get("desc", "unknown")
        constraints = []

        for key, val in rule_data.items():
            if key in ["desc", "polarity", "outcome", "target", "is_blocked", "is_premature", "sustenance_factor"]:
                continue
            
            chart_type = "natal" if key.startswith("natal_") else "annual"
            sub_key = key.replace("natal_", "").replace("annual_", "")

            # Fix boolean values to range(1, 13)
            houses = val
            if isinstance(val, bool):
                houses = list(range(1, 13)) if val else []

            if sub_key in self.PLANET_MAP:
                planet = self.PLANET_MAP[sub_key]
                if isinstance(houses, list):
                    constraints.append(RuleConstraint(planet, houses, chart_type, "placement"))
                elif isinstance(houses, int):
                    constraints.append(RuleConstraint(planet, [houses], chart_type, "placement"))
            
            elif "_conjoined" in sub_key:
                planets_abbr = sub_key.replace("_conjoined", "").split("_")
                planets = [self.PLANET_MAP.get(p) for p in planets_abbr if self.PLANET_MAP.get(p)]
                target_houses = houses if isinstance(houses, list) else list(range(1, 13))
                for p in planets:
                    constraints.append(RuleConstraint(p, target_houses, chart_type, "conjoined"))

            elif "_alone" in sub_key:
                p_abbr = sub_key.replace("_alone", "")
                planet = self.PLANET_MAP.get(p_abbr)
                if planet:
                    constraints.append(RuleConstraint(planet, houses, chart_type, "alone"))

            elif "_return" in sub_key:
                planets_abbr = sub_key.replace("_return", "").split("_")
                planets = [self.PLANET_MAP.get(p) for p in planets_abbr if self.PLANET_MAP.get(p)]
                for p in planets:
                    constraints.append(RuleConstraint(p, list(range(1, 13)), "annual", "return"))

            elif "_" in sub_key:
                planets_abbr = sub_key.split("_")
                planets = [self.PLANET_MAP.get(p) for p in planets_abbr if self.PLANET_MAP.get(p)]
                if planets:
                    # SPECIAL CASE: ven_mer is an OR condition, we only need ONE to satisfy it
                    if sub_key == "ven_mer":
                        constraints.append(RuleConstraint(planets[0], houses, chart_type, "placement"))
                    else:
                        for p in planets:
                            if isinstance(houses, list):
                                constraints.append(RuleConstraint(p, houses, chart_type, "placement"))

        if constraints:
            self.extracted_rules.append(ExtractedRule(
                rule_id=desc,
                domain=domain,
                constraints=constraints,
                node_id=node_id,
                description=desc
            ))

    def _get_value(self, node):
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.List):
            return [self._get_value(e) for e in node.elts]
        elif isinstance(node, ast.Name):
            if node.id == "True": return True
            if node.id == "False": return False
        return None

    def export_to_json(self, output_path: str):
        data = [r.to_dict() for r in self.extracted_rules]
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

if __name__ == "__main__":
    constants_path = "backend/astroq/lk_prediction/lk_pattern_constants.py"
    output_path = "backend/tests/graphify_test/coverage_map.json"
    
    extractor = RuleExtractor(constants_path)
    rules = extractor.extract()
    extractor.export_to_json(output_path)
    print(f"Extracted {len(rules)} rules to {output_path}")
