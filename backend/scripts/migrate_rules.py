import csv
import json
import sqlite3
import uuid
import os
import re

csv_path = r"d:\astroq-mar26\backend\data\planet_predictions_consolidated.csv"
db_path = r"d:\astroq-v2\backend\data\rules.db"

def parse_house(h_str):
    h_str = h_str.strip()
    if not h_str or h_str.lower() == 'all' or h_str.lower() == 'any':
        return list(range(1, 13))
    nums = [int(x) for x in re.findall(r'\d+', h_str)]
    return nums

def build_ast(planets_str, houses):
    planets = [p.strip() for p in planets_str.split("-") if p.strip()]
    
    if len(planets) == 1:
        return {
            "type": "placement",
            "planet": planets[0],
            "houses": houses
        }
    else:
        conditions = []
        for p in planets:
            conditions.append({
                "type": "placement",
                "planet": p,
                "houses": houses
            })
        return {
            "type": "AND",
            "conditions": conditions
        }

def migrate():
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS deterministic_rules (
            id TEXT PRIMARY KEY,
            domain TEXT NOT NULL,
            description TEXT NOT NULL,
            condition TEXT NOT NULL,
            verdict TEXT NOT NULL,
            scale TEXT NOT NULL,
            scoring_type TEXT NOT NULL,
            source_page TEXT,
            success_weight REAL DEFAULT 1.0
        )
    ''')
    cur.execute("DELETE FROM deterministic_rules")
    
    with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            planets_str = row.get("Planets", "").strip()
            if not planets_str: continue
            
            h_str = row.get("House", "")
            effects = row.get("Effects", "").strip()
            v_type = row.get("Type", "").strip()
            
            houses = parse_house(h_str)
            if not houses:
                continue
                
            ast = build_ast(planets_str, houses)
            
            v_lower = v_type.lower()
            if "malefic" in v_lower and "benefic" in v_lower:
                scoring_type = "neutral"
                scale = "moderate"
            elif "malefic" in v_lower:
                scoring_type = "penalty"
                scale = "major"
            elif "benefic" in v_lower:
                scoring_type = "boost"
                scale = "major"
            else:
                scoring_type = "neutral"
                scale = "minor"
                
            rule_id = str(uuid.uuid4())
            cur.execute('''
                INSERT INTO deterministic_rules 
                (id, domain, description, condition, verdict, scale, scoring_type, source_page, success_weight)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                rule_id,
                "General",
                effects,
                json.dumps(ast),
                v_type,
                scale,
                scoring_type,
                "CSV",
                1.0
            ))
            count += 1
            
    con.commit()
    con.close()
    print(f"Migrated {count} rules to {db_path}!")

if __name__ == '__main__':
    migrate()
