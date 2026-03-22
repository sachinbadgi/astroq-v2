import sqlite3
import os
import json

old_db_path = r"d:\astroq-mar26\backend\astroq.db"
new_db_path = r"d:\astroq-v2\backend\data\rules.db"

con_old = sqlite3.connect(old_db_path)
con_new = sqlite3.connect(new_db_path)

con_new.execute('DELETE FROM deterministic_rules')

old_rules = con_old.execute("SELECT rule_id, domain, description, condition_json, verdict, magnitude, scoring_type, source_page, success_weight FROM deterministic_rules").fetchall()

def convert_ast(node):
    if isinstance(node, list):
        if len(node) == 1:
            return convert_ast(node[0])
        else:
            return {"type": "AND", "conditions": [convert_ast(n) for n in node]}
            
    if not isinstance(node, dict):
        return node
        
    out = {}
    
    if "operator" in node:
        out["type"] = node["operator"]
        out["conditions"] = [convert_ast(n) for n in node.get("nodes", [])]
        return out
        
    # Base case: it's a leaf node
    out["type"] = node.get("type", "")
    
    if out["type"] == "placement":
        out["planet"] = node.get("planet", "")
        
        houses = node.get("house")
        if houses is not None:
            if isinstance(houses, list):
                out["houses"] = houses
            else:
                out["houses"] = [houses]
        else:
            out["houses"] = []
            
    elif out["type"] == "confrontation":
        planets = node.get("planets", [])
        if len(planets) >= 2:
            out["planet_a"] = planets[0]
            out["planet_b"] = planets[1]
        elif len(planets) == 1:
            out["planet_a"] = planets[0]
            out["planet_b"] = ""
            
    # pass through anything else unchanged in case
    for k, v in node.items():
        if k not in ["type", "operator", "nodes", "planet", "house", "planets"]:
            out[k] = v
            
    return out

new_rules = []
for row in old_rules:
    r_id, dom, desc, cond_str, verdict, mag, s_type, src, weight = row
    
    try:
        old_ast = json.loads(cond_str)
        new_ast = convert_ast(old_ast)
        new_cond_str = json.dumps(new_ast)
    except Exception:
        new_cond_str = cond_str
        
    abs_mag = abs(float(mag)) if mag is not None else 1.0
    if abs_mag <= 1.0:
        scale = "minor"
    elif abs_mag <= 2.0:
        scale = "moderate"
    elif abs_mag <= 3.0:
        scale = "major"
    else:
        scale = "extreme"
        
    s_type = s_type if s_type else "neutral"
    
    new_rules.append((
        r_id, dom, desc, new_cond_str, verdict, scale, s_type, src, weight
    ))

con_new.executemany('''
    INSERT INTO deterministic_rules (id, domain, description, condition, verdict, scale, scoring_type, source_page, success_weight)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
''', new_rules)

con_new.commit()
print(f"Successfully migrated {len(new_rules)} JSON rules from legacy DB to v2 rules.db with schema translation!")

con_old.close()
con_new.close()
