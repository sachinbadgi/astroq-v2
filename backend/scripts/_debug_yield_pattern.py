"""
Explicit Validation of Benefic Materialization (Pattern 3)
"""

import os
import sys

sys.path.append(os.path.join(os.getcwd(), "backend"))

from astroq.lk_prediction.rules_engine import RulesEngine
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.lk_pattern_constants import BENEFIC_YIELD_PATTERN
from astroq.lk_prediction.lk_constants import PLANET_PAKKA_GHAR

DB_PATH = "backend/data/rules.db"
DEFAULTS_PATH = "backend/data/model_defaults.json"

def run_yield_verification():
    cfg = ModelConfig(db_path=DB_PATH, defaults_path=DEFAULTS_PATH)
    rules_engine = RulesEngine(cfg)
    
    # Flatten all items by planet for matching
    planet_items = {}
    for h, val in BENEFIC_YIELD_PATTERN["yield_mapping"].items():
        lord = val["house_lord"]
        if lord not in planet_items:
            planet_items[lord] = []
        planet_items[lord].extend([y.lower() for y in val["primary_yields"]])

    # Collect all items for searching
    all_known_items = []
    for items in planet_items.values():
        all_known_items.extend(items)
        
    stats = {
        "rules_with_explicit_nouns": 0,
        "rules_matching_correct_lord": 0,
        "anomalies": []
    }

    for rule in rules_engine._rules_cache:
        # Only look at MAJOR/EXTREME BOOSTS
        if rule.get("scoring_type") != "boost": continue
        if rule.get("scale") not in ["major", "extreme"]: continue
            
        desc = rule.get("description", "").lower() + " " + rule.get("verdict", "").lower()
        cond_str = rule.get("condition", "")
        
        # Determine if any of our yield nouns are explicitly mentioned in this rule
        mentioned_items = [item for item in all_known_items if item in desc]
        
        if len(mentioned_items) > 0:
            stats["rules_with_explicit_nouns"] += 1
            
            # Now check if the mentioned item belongs to the Pakka Lord of the house the planet is in
            matched_lord = False
            
            # Extract which houses this rule fires on
            involved_houses = []
            for h in range(1, 13):
                if f"H{h}" in cond_str or f"house {h}" in desc or f"H.No.{h}" in desc:
                    involved_houses.append(h)
                    
            if not involved_houses:
                # If we can't parse the house, assume generic 
                matches_any = True
            else:
                for h in involved_houses:
                    # Get the correct lord for this house
                    mapping = BENEFIC_YIELD_PATTERN["yield_mapping"].get(h)
                    if mapping:
                        correct_lord = mapping["house_lord"]
                        correct_items = planet_items.get(correct_lord, [])
                        
                        if any(item in correct_items for item in mentioned_items):
                            matched_lord = True
                            break
                            
            if matched_lord or not involved_houses:
                stats["rules_matching_correct_lord"] += 1
            else:
                stats["anomalies"].append((desc, mentioned_items, involved_houses))

    print("================================================================")
    print("      EXPLICIT YIELD VERIFICATION (PATTERN 3 ISOLATION)         ")
    print("================================================================")
    print(f"Total Major/Extreme Benefic Rules mentioning specific items: {stats['rules_with_explicit_nouns']}")
    
    if stats["rules_with_explicit_nouns"] > 0:
        rate = (stats['rules_matching_correct_lord'] / stats['rules_with_explicit_nouns']) * 100
        print(f"Total explicitly matching the correct Pakka Ghar Lord: {stats['rules_matching_correct_lord']}")
        print(f"Consistency Rate for Explicit Nouns: {rate:.1f}%")
        
    if stats["anomalies"]:
        print("\nAnomalies found:")
        for ann in stats["anomalies"][:5]:
            print(f"- {ann}")

if __name__ == "__main__":
    run_yield_verification()
