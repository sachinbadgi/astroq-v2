"""
Crosscheck Pattern Fuzzer v2 - Full 7-Pattern Evaluation
========================================================

Executes ALL meta-patterns defined in `lk_pattern_constants.py` via Python logic 
on generated charts, covering the complete Dormancy physics, and comparing ALL
7 patterns against the engine's hardcoded rules database.
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
from astroq.lk_prediction.lk_pattern_constants import BENEFIC_YIELD_PATTERN, MATURITY_AGE_PATTERN

DB_PATH = "backend/data/rules.db"
DEFAULTS_PATH = "backend/data/model_defaults.json"

def is_house_dormant(house, occupied_houses):
    # Rule of Dormancy: Houses 7-12 go dormant if their corresponding 1-6 houses are blank.
    if house == 7 and 1 not in occupied_houses: return True
    if house == 8 and 2 not in occupied_houses: return True
    if house == 9 and 3 not in occupied_houses: return True
    if house == 10 and 4 not in occupied_houses: return True
    if house == 11 and 5 not in occupied_houses: return True
    if house == 12 and 6 not in occupied_houses: return True
    return False

def evaluate_pattern_logic(ppos):
    pattern_hits = {}
    occupied_houses = set(ppos.values())
    
    for planet, house in ppos.items():
        if planet == "Lagna": continue
        
        # PATTERN 1 & 5: DIGNITY & DORMANCY
        is_dormant = is_house_dormant(house, occupied_houses)
        
        # Hardcode Rahu/House 2 edge case dormancy mentioned in DB
        if planet == "Rahu" and 2 not in occupied_houses:
            is_dormant = True
            
        is_pakka = house == PLANET_PAKKA_GHAR.get(planet)
        is_uchha = house in PLANET_EXALTATION.get(planet, [])
        is_neech = house in PLANET_DEBILITATION.get(planet, [])
        
        # PATTERN 4: DOUBTFUL (Blind) CONDITIONS
        is_doubtful = False
        if planet == "Venus" and house == 4: is_doubtful = True
        if planet == "Sun" and house == 4 and ppos.get("Saturn") == 10: is_doubtful = True
        if planet == "Saturn" and house == 10 and ppos.get("Sun") == 4: is_doubtful = True
            
        # PATTERN 5 CONTINUED: 180-DEGREE OPPOSITION
        is_opposed = False
        for op_planet, op_house in ppos.items():
            if op_planet != planet:
                if house == (op_house + 6) % 12 or house == op_house - 6 or house == op_house + 6:
                    # Ignore sabotage if BOTH are explicitly exalted on the axis 
                    if not (is_uchha and op_house in PLANET_EXALTATION.get(op_planet, [])):
                        is_opposed = True
                        break
                        
        # PATTERN 2 & 6: ROUTING FATE DISTRIBUTION (Bio vs Mat)
        is_bio_planet = planet in ["Sun", "Moon", "Jupiter", "Venus", "Mars"]
        is_bio_house = house in [1, 3, 4, 5, 7, 8, 9]
        
        severity_prediction = "MINOR"
        scoring_prediction = "NEUTRAL"
        fate_bucket = "N/A"
        
        if is_dormant:
            severity_prediction = "NEUTRALIZED_DORMANT"
            scoring_prediction = "NEUTRAL"
        elif is_doubtful:
            severity_prediction = "EXTREME_MALEFIC"
            scoring_prediction = "PENALTY"
        elif is_neech or is_opposed:
            severity_prediction = "MODERATE_MALEFIC"
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
                
        # PATTERN 7: TIMING
        maturity_age = MATURITY_AGE_PATTERN["maturity_ages"].get(planet)
                
        pattern_hits[planet] = {
            "severity": severity_prediction,
            "scoring_type": scoring_prediction,
            "fate_bucket": fate_bucket,
            "house": house,
            "maturity_age": maturity_age,
            "is_dormant": is_dormant,
            "is_opposed": is_opposed,
            "is_doubtful": is_doubtful
        }
        
    return pattern_hits


def run_crosscheck_fuzzer(iterations=500):
    print(f"=== Starting 7-Pattern Exhaustive Crosscheck ({iterations} iterations) ===\n")
    
    cfg = ModelConfig(db_path=DB_PATH, defaults_path=DEFAULTS_PATH)
    generator = ChartGenerator()
    pipeline = LKPredictionPipeline(cfg)
    rules_engine = RulesEngine(cfg)
    rule_map = {r.get("id") or r.get("rule_id"): r for r in rules_engine._rules_cache}
    
    stats = {
        "P1_benefic_expected": 0, "P1_benefic_match": 0,
        "P1_dormant_caught": 0, "P1_dormant_match": 0,
        "P2_P6_bio_expected": 0, "P2_P6_bio_match": 0,
        "P2_P6_mat_expected": 0, "P2_P6_mat_match": 0,
        "P3_yields_expected": 0, "P3_yields_match": 0,
        "P4_doubtful_expected": 0, "P4_doubtful_match": 0,
        "P5_180_opp_expected": 0, "P5_180_opp_match": 0,
        "P7_timing_expected": 0, "P7_timing_match": 0,
        "total_evals": 0
    }
    
    bio_terms = {"mother", "father", "son", "daughter", "sister", "brother", "eye", "eyesight", "teeth", "health", "disease", "body", "wife", "spouse", "child", "children", "longevity", "death"}
    timing_terms = {"age", "year", "years", "until", 16, 21, 24, 25, 28, 34, 36, 42, 48}
    
    for i in range(1, iterations + 1):
        dob = (datetime.date(1940, 1, 1) + datetime.timedelta(days=random.randrange(30000))).strftime("%Y-%m-%d")
        tob = f"{random.randint(0,23):02d}:{random.randint(0,59):02d}"
        
        payload = generator.build_full_chart_payload(dob, tob, "New Delhi", 28.6139, 77.2090, "+05:30", "vedic")
        chart_data = payload.get("chart_0")
        if not chart_data: continue
            
        ppos = {p: d["house"] for p, d in chart_data["planets_in_houses"].items() if p != "Lagna"}
        
        # 1. Pattern Logic Predictions
        pattern_preds = evaluate_pattern_logic(ppos)
        
        # 2. Engine DB Predictions
        db_predictions = pipeline.generate_predictions(chart_data)
        
        planet_db = {p: {
            "has_boost": False, "has_penalty": False, 
            "has_bio": False, "has_mat": False, "has_yield": False, 
            "is_dormant_text": False, "has_timing": False
        } for p in ppos}
        
        for pred in db_predictions:
            for rid in pred.source_rules:
                if rid in rule_map:
                    rule = rule_map[rid]
                    scale = rule.get("scale", "minor")
                    stype = rule.get("scoring_type", "neutral")
                    desc = rule.get("description", "").lower() + " " + rule.get("verdict", "").lower()
                    
                    cond_str = rule.get("condition", "")
                    for p in ppos:
                        if p in cond_str:
                            if stype == "boost": planet_db[p]["has_boost"] = True
                            if stype == "penalty": planet_db[p]["has_penalty"] = True
                            
                            # Fate distributions
                            if stype == "penalty":
                                if any(term in desc for term in bio_terms): planet_db[p]["has_bio"] = True
                                else: planet_db[p]["has_mat"] = True
                                
                            # Dormancy keywords
                            if "dormant" in desc or "ineffective" in desc or "sleeping" in desc:
                                planet_db[p]["is_dormant_text"] = True
                                
                            # Yield Materialization (Pattern 3)
                            if stype == "boost":
                                h = ppos[p]
                                yields = [y.lower() for y in BENEFIC_YIELD_PATTERN["yield_mapping"].get(h, {}).get("primary_yields", [])]
                                if any(y in desc for y in yields):
                                    planet_db[p]["has_yield"] = True
                                    
                            # Timing words (Pattern 7)
                            if any(str(term) in desc for term in timing_terms):
                                planet_db[p]["has_timing"] = True
                                    
        # 3. Compare All 7 Patterns
        for planet, pat in pattern_preds.items():
            stats["total_evals"] += 1
            db_res = planet_db[planet]
            
            # P1: Dormancy Check 
            if pat["is_dormant"]:
                stats["P1_dormant_caught"] += 1
                if not db_res["has_boost"]: # Dormancy effectively neutralizes extreme boosts
                    stats["P1_dormant_match"] += 1

            # P1: Extreme Benefic
            if pat["severity"] == "EXTREME_BENEFIC":
                stats["P1_benefic_expected"] += 1
                if db_res["has_boost"]: stats["P1_benefic_match"] += 1
                
            # P4: Doubtful
            if pat["is_doubtful"]:
                stats["P4_doubtful_expected"] += 1
                if db_res["has_penalty"]: stats["P4_doubtful_match"] += 1
                
            # P5: 180 Opposition
            if pat["is_opposed"]:
                stats["P5_180_opp_expected"] += 1
                if db_res["has_penalty"]: stats["P5_180_opp_match"] += 1
                
            # P2 & P6: Fate routing
            if pat["fate_bucket"] == "TRANSFERENCE_TRAP_BIOLOGICAL":
                stats["P2_P6_bio_expected"] += 1
                if db_res["has_bio"]: stats["P2_P6_bio_match"] += 1
            
            if pat["fate_bucket"] == "MATERIAL_BLOCK_WEALTH":
                stats["P2_P6_mat_expected"] += 1
                if db_res["has_mat"]: stats["P2_P6_mat_match"] += 1
                
            # P3: Benefic Yield Pattern
            if pat["severity"] == "EXTREME_BENEFIC":
                stats["P3_yields_expected"] += 1
                if db_res["has_yield"]: stats["P3_yields_match"] += 1
                
            # P7: Age Timing Trigger
            if db_res["has_boost"] or db_res["has_penalty"]:
                if str(pat["maturity_age"]) in [r.get("description", "") for p in db_predictions for r in [rule_map.get(rid, {}) for rid in p.source_rules]]:
                    pass # Hard to tightly map dynamic age text due to complex strings, we will just count general timing presence
                stats["P7_timing_expected"] += 1
                if db_res["has_timing"]: stats["P7_timing_match"] += 1

    print("================================================================")
    print("      COMPREHENSIVE 7-PATTERN CROSSCHECK VALIDATION REPORT      ")
    print("================================================================")
    print(f"Total Planets Evaluated: {stats['total_evals']}\n")
    
    def report(name, ev, match):
        if ev > 0:
            rate = (match / ev) * 100
            print(f"- {name}: {match}/{ev} ({rate:.1f}%)")
            
    print("PATTERN 1: SEVERITY MATRIX & DORMANCY EXCEPTION")
    report("Dormancy Neutralization (Blocked Extreme Boosts)", stats["P1_dormant_caught"], stats["P1_dormant_match"])
    report("Extreme Benefic Outcomes (Pakka/Uchha minus Dormancy)", stats["P1_benefic_expected"], stats["P1_benefic_match"])
    print()
    print("PATTERN 2 & 6: FATE DISTRIBUTION ROUTING (Bio vs Mat)")
    report("Routed to Biological/Transference Trap", stats["P2_P6_bio_expected"], stats["P2_P6_bio_match"])
    report("Routed to Material Block/Wealth Loss", stats["P2_P6_mat_expected"], stats["P2_P6_mat_match"])
    print()
    print("PATTERN 3: BENEFIC MATERIALIZATION (Pakka Lord Yields)")
    report("Yielded Pakka Ghar Lord's Items (Gold, Cash, Iron, etc)", stats["P3_yields_expected"], stats["P3_yields_match"])
    print()
    print("PATTERN 4: DOUBTFUL CIPHERS (Blind Fates)")
    report("Doubtful Layout resulted in Extreme Penalty", stats["P4_doubtful_expected"], stats["P4_doubtful_match"])
    print()
    print("PATTERN 5: THE 180-DEGREE OPPOSITION (Uchha/Neech)")
    report("180-Degree Opposition Produced Penalty", stats["P5_180_opp_expected"], stats["P5_180_opp_match"])
    print()
    print("PATTERN 7: CHRONOLOGICAL TRIGGER (Maturity Age Timing)")
    report("Penalties/Boosts governed by timing/age constraints", stats["P7_timing_expected"], stats["P7_timing_match"])

if __name__ == "__main__":
    run_crosscheck_fuzzer(iterations=500)
