"""
Crosscheck Pattern Fuzzer
=========================

Executes the meta-patterns defined in `lk_pattern_constants.py` purely via Python logic 
on generated charts, and compares the resulting "Pattern Predictions" with the actual 
"Engine Predictions" (from the 1,145 hardcoded rules database) to prove consistency.
"""

import random
import datetime
import os
import sys

sys.path.append(os.path.join(os.getcwd(), "backend"))

from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.rules_engine import RulesEngine
from astroq.lk_prediction.pipeline import LKPredictionPipeline
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.lk_constants import PLANET_PAKKA_GHAR, PLANET_EXALTATION, PLANET_DEBILITATION

DB_PATH = "backend/data/rules.db"
DEFAULTS_PATH = "backend/data/model_defaults.json"

# Abstracted Pattern Evaluation Engine
def evaluate_pattern_logic(ppos):
    pattern_hits = {}
    
    # Pre-calculate house occupancies for Dormancy checking
    occupied_houses = set(ppos.values())
    
    for planet, house in ppos.items():
        if planet == "Lagna": continue
        
        # 1. Dormancy Check (Simplified logical approximation based on LK principles)
        is_dormant = False
        if planet == "Rahu" and 2 not in occupied_houses: is_dormant = True
        
        # 2. Structural Dignity
        is_pakka = house == PLANET_PAKKA_GHAR.get(planet)
        is_uchha = house in PLANET_EXALTATION.get(planet, [])
        is_neech = house in PLANET_DEBILITATION.get(planet, [])
        
        # 3. Doubtful (Blind) Conditions
        is_doubtful = False
        if planet == "Venus" and house == 4: is_doubtful = True
        if planet == "Sun" and house == 4 and ppos.get("Saturn") == 10: is_doubtful = True
            
        # 4. 180-Degree Opposition
        is_opposed = False
        for op_planet, op_house in ppos.items():
            if op_planet != planet:
                if house == op_house + 6 or house == op_house - 6:
                    # Ignore if BOTH are explicitly exalted on the axis 
                    # (e.g. Venus H12 and Mercury H6)
                    if not (is_uchha and op_house in PLANET_EXALTATION.get(op_planet, [])):
                        is_opposed = True
                        break
                        
        # 5. Routing Fate Distribution (Bio vs Mat)
        is_bio_planet = planet in ["Sun", "Moon", "Jupiter", "Venus", "Mars"]
        is_bio_house = house in [1, 3, 4, 5, 7, 8, 9]
        
        # Determine Logical Severity & Fate Type purely using PATTERN RULES
        severity_prediction = "MINOR"
        scoring_prediction = "NEUTRAL"
        fate_bucket = "N/A"
        
        if is_dormant:
            severity_prediction = "NEUTRALIZED"
            scoring_prediction = "NEUTRAL"
        elif is_doubtful:
            severity_prediction = "EXTREME_MALEFIC"
            scoring_prediction = "PENALTY"
        elif is_neech or is_opposed:
            severity_prediction = "MODERATE_MALEFIC" # or MINOR
            scoring_prediction = "PENALTY"
        elif is_uchha or is_pakka:
            severity_prediction = "EXTREME_BENEFIC"
            scoring_prediction = "BOOST"
            fate_bucket = "BENEFIC_HOUSE_LORD_YIELD"
            
        if scoring_prediction == "PENALTY":
            if is_bio_planet or is_bio_house:
                fate_bucket = "TRANSFERENCE_TRAP_BIOLOGICAL"
            else:
                fate_bucket = "MATERIAL_BLOCK_WEALTH"
                
        pattern_hits[planet] = {
            "severity": severity_prediction,
            "scoring_type": scoring_prediction,
            "fate_bucket": fate_bucket
        }
        
    return pattern_hits


def run_crosscheck_fuzzer(iterations=500):
    print(f"=== Starting Pattern Logic vs Rules Engine Crosscheck ({iterations} iterations) ===\n")
    
    cfg = ModelConfig(db_path=DB_PATH, defaults_path=DEFAULTS_PATH)
    generator = ChartGenerator()
    pipeline = LKPredictionPipeline(cfg)
    rules_engine = RulesEngine(cfg)
    rule_map = {r.get("id") or r.get("rule_id"): r for r in rules_engine._rules_cache}
    
    stats = {
        "total_planets_checked": 0,
        "congruent_benefic_spikes": 0,
        "congruent_malefic_spikes": 0,
        "congruent_transference_hits": 0,
        "congruent_material_hits": 0,
        "total_expected_benefic_spikes": 0,
        "total_expected_malefic_spikes": 0,
        "total_expected_transference": 0,
        "total_expected_material": 0
    }
    
    bio_terms = {"mother", "father", "son", "daughter", "sister", "brother", "eye", "eyesight", "teeth", "health", "disease", "body", "wife", "spouse", "child", "children", "longevity", "death"}
    
    for i in range(1, iterations + 1):
        start_date = datetime.date(1940, 1, 1)
        end_date = datetime.date(2025, 12, 31)
        dob = (start_date + datetime.timedelta(days=random.randrange((end_date - start_date).days))).strftime("%Y-%m-%d")
        tob = f"{random.randint(0,23):02d}:{random.randint(0,59):02d}"
        
        payload = generator.build_full_chart_payload(dob, tob, "New Delhi", 28.6139, 77.2090, "+05:30", "vedic")
        chart_data = payload.get("chart_0")
        if not chart_data: continue
            
        ppos = {p: d["house"] for p, d in chart_data["planets_in_houses"].items() if p != "Lagna"}
        
        # 1. Get Pure Pattern Logic Predictions
        pattern_predictions = evaluate_pattern_logic(ppos)
        
        # 2. Get Raw Engine DB Predictions
        db_predictions = pipeline.generate_predictions(chart_data)
        
        # Aggregate DB rules per planet
        planet_db_outcomes = {p: {"has_extreme_boost": False, "has_extreme_penalty": False, "has_bio_hit": False, "has_mat_hit": False} for p in ppos}
        
        for pred in db_predictions:
            for rid in pred.source_rules:
                if rid in rule_map:
                    rule = rule_map[rid]
                    scale = rule.get("scale", "minor")
                    stype = rule.get("scoring_type", "neutral")
                    desc = rule.get("description", "").lower() + " " + rule.get("verdict", "").lower()
                    
                    # Associate rule with planet from generic condition string
                    cond_str = rule.get("condition", "")
                    for p in ppos:
                        if p in cond_str:
                            if scale in ["major", "extreme"] and stype == "boost":
                                planet_db_outcomes[p]["has_extreme_boost"] = True
                            if scale in ["major", "extreme"] and stype == "penalty":
                                planet_db_outcomes[p]["has_extreme_penalty"] = True
                            if stype == "penalty":
                                is_bio = any(term in desc for term in bio_terms)
                                if is_bio: 
                                    planet_db_outcomes[p]["has_bio_hit"] = True
                                else:
                                    planet_db_outcomes[p]["has_mat_hit"] = True
                                    
        # 3. Compare Pattern vs Engine!
        for planet, pat in pattern_predictions.items():
            stats["total_planets_checked"] += 1
            
            db_res = planet_db_outcomes[planet]
            
            # Check Extreme Benefic Match
            if pat["severity"] == "EXTREME_BENEFIC":
                stats["total_expected_benefic_spikes"] += 1
                if db_res["has_extreme_boost"]: stats["congruent_benefic_spikes"] += 1
                
            # Check Extreme Malefic Match
            if pat["severity"] == "EXTREME_MALEFIC":
                stats["total_expected_malefic_spikes"] += 1
                if db_res["has_extreme_penalty"]: stats["congruent_malefic_spikes"] += 1
                
            # Check Fate Routing Match
            if pat["fate_bucket"] == "TRANSFERENCE_TRAP_BIOLOGICAL":
                stats["total_expected_transference"] += 1
                if db_res["has_bio_hit"]: stats["congruent_transference_hits"] += 1
                
            if pat["fate_bucket"] == "MATERIAL_BLOCK_WEALTH":
                stats["total_expected_material"] += 1
                if db_res["has_mat_hit"]: stats["congruent_material_hits"] += 1

    print("==================================================")
    print("      CROSSCHECK VALIDATION RESULTS (PATTERN VS. ENGINE)")
    print("==================================================")
    print(f"Total Planets Evaluated: {stats['total_planets_checked']}\n")
    
    if stats['total_expected_benefic_spikes'] > 0:
        rate = (stats['congruent_benefic_spikes'] / stats['total_expected_benefic_spikes']) * 100
        print(f"EXTREME BENEFIC PREDICTION (Pakka/Uchha minus Dormancy):")
        print(f"  Pattern Expected : {stats['total_expected_benefic_spikes']}")
        print(f"  Engine Triggered : {stats['congruent_benefic_spikes']}")
        print(f"  Consistency Rate : {rate:.1f}%\n")
        
    if stats['total_expected_malefic_spikes'] > 0:
        rate = (stats['congruent_malefic_spikes'] / stats['total_expected_malefic_spikes']) * 100
        print(f"EXTREME MALEFIC PREDICTION (Doubtful/Blind):")
        print(f"  Pattern Expected : {stats['total_expected_malefic_spikes']}")
        print(f"  Engine Triggered : {stats['congruent_malefic_spikes']}")
        print(f"  Consistency Rate : {rate:.1f}%\n")

    if stats['total_expected_transference'] > 0:
        rate = (stats['congruent_transference_hits'] / stats['total_expected_transference']) * 100
        print(f"TRANSFERENCE TRAP (Biological Entity Loss Predicted):")
        print(f"  Pattern Expected : {stats['total_expected_transference']}")
        print(f"  Engine Triggered : {stats['congruent_transference_hits']}")
        print(f"  Consistency Rate : {rate:.1f}%\n")
        
    if stats['total_expected_material'] > 0:
        rate = (stats['congruent_material_hits'] / stats['total_expected_material']) * 100
        print(f"MATERIAL BLOCK (Wealth/Work Loss Predicted):")
        print(f"  Pattern Expected : {stats['total_expected_material']}")
        print(f"  Engine Triggered : {stats['congruent_material_hits']}")
        print(f"  Consistency Rate : {rate:.1f}%\n")

if __name__ == "__main__":
    run_crosscheck_fuzzer(iterations=500)
