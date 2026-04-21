"""
Determine exact astrological conditions separating Transference (Biological) from Material Fate
"""
import os
import sys
import json

sys.path.append(os.path.join(os.getcwd(), "backend"))

from astroq.lk_prediction.rules_engine import RulesEngine
from astroq.lk_prediction.config import ModelConfig

DB_PATH = "backend/data/rules.db"
DEFAULTS_PATH = "backend/data/model_defaults.json"

def analyze_fate_distribution():
    cfg = ModelConfig(db_path=DB_PATH, defaults_path=DEFAULTS_PATH)
    rules_engine = RulesEngine(cfg)
    
    bio_terms = {"mother", "father", "son", "daughter", "sister", "brother", "eye", "eyesight", "teeth", "health", "disease", "body", "wife", "spouse", "child", "children", "longevity", "death"}
    mat_terms = {"wealth", "money", "profession", "business", "trade", "theft", "loss", "cash", "ruined", "poverty", "income", "poor condition", "disrepute"}
    
    bio_karakas = {"Sun", "Moon", "Jupiter", "Venus", "Mars"}
    mat_karakas = {"Saturn", "Mercury", "Rahu", "Ketu"}
    
    # Fundamental categorization in Jyotish
    bio_houses = {1, 3, 4, 5, 7, 8, 9}
    mat_houses = {2, 6, 10, 11, 12}
    
    stats = {
        "bio_hit": {"bio_planet": 0, "mat_planet": 0, "bio_house": 0, "mat_house": 0},
        "mat_hit": {"bio_planet": 0, "mat_planet": 0, "bio_house": 0, "mat_house": 0}
    }
    
    for rule in rules_engine._rules_cache:
        if rule.get("scoring_type") != "penalty": continue
            
        desc = rule.get("description", "").lower() + " " + rule.get("verdict", "").lower()
        condition_str = rule.get("condition", "[]")
        
        try:
            conds = json.loads(condition_str)
            if not isinstance(conds, list): conds = [conds]
        except:
            continue
            
        is_bio = any(term in desc for term in bio_terms)
        is_mat = any(term in desc for term in mat_terms) and not is_bio
        
        has_bp = False; has_mp = False; has_bh = False; has_mh = False
        
        for c in conds:
            if not isinstance(c, dict): continue
            p = c.get("planet")
            if p in bio_karakas: has_bp = True
            if p in mat_karakas: has_mp = True
            
            h = c.get("house")
            if isinstance(h, list):
                if any(x in bio_houses for x in h): has_bh = True
                if any(x in mat_houses for x in h): has_mh = True
            elif isinstance(h, int):
                if h in bio_houses: has_bh = True
                if h in mat_houses: has_mh = True

        if is_bio:
            if has_bp: stats["bio_hit"]["bio_planet"] += 1
            if has_mp: stats["bio_hit"]["mat_planet"] += 1
            if has_bh: stats["bio_hit"]["bio_house"] += 1
            if has_mh: stats["bio_hit"]["mat_house"] += 1
            
        if is_mat:
            if has_bp: stats["mat_hit"]["bio_planet"] += 1
            if has_mp: stats["mat_hit"]["mat_planet"] += 1
            if has_bh: stats["mat_hit"]["bio_house"] += 1
            if has_mh: stats["mat_hit"]["mat_house"] += 1

    print("=== PENALTY CLASSIFICATION MAPPING ===")
    print("When a penalty hits BIOLOGICAL (Transference Trap):")
    print(f"  Triggered by Bio Planets  (Sun, Moon, Jup, Ven, Mars) : {stats['bio_hit']['bio_planet']}")
    print(f"  Triggered by Mat Planets  (Sat, Merc, Rahu, Ketu)     : {stats['bio_hit']['mat_planet']}")
    print(f"  Triggered by Bio Houses   (1, 3, 4, 5, 7, 8, 9)       : {stats['bio_hit']['bio_house']}")
    print(f"  Triggered by Mat Houses   (2, 6, 10, 11, 12)          : {stats['bio_hit']['mat_house']}")
    print()
    print("When a penalty hits MATERIAL (Material Block):")
    print(f"  Triggered by Bio Planets  (Sun, Moon, Jup, Ven, Mars) : {stats['mat_hit']['bio_planet']}")
    print(f"  Triggered by Mat Planets  (Sat, Merc, Rahu, Ketu)     : {stats['mat_hit']['mat_planet']}")
    print(f"  Triggered by Bio Houses   (1, 3, 4, 5, 7, 8, 9)       : {stats['mat_hit']['bio_house']}")
    print(f"  Triggered by Mat Houses   (2, 6, 10, 11, 12)          : {stats['mat_hit']['mat_house']}")

if __name__ == "__main__":
    analyze_fate_distribution()
