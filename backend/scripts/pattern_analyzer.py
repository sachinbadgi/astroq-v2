#!/usr/bin/env python3
"""
pattern_analyzer.py
===================
Analyzes the public_figures.db for precise geometric patterns (Hammer and Anvil, 
Mechanics of Fate) and saves the raw occurrences back to the database.
"""

import os
import sys
import json
import sqlite3
from typing import Dict, Any, List

sys.path.append(os.path.join(os.getcwd(), "backend"))

from astroq.lk_prediction.aspect_engine import AspectEngine
from astroq.lk_prediction.astrological_context import UnifiedAstrologicalContext
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.natal_fate_view import NatalFateView

DOMAIN_MAP = {
    "Career": "career_travel", "Legal": "career_travel", "Business": "career_travel",
    "Debut": "career_travel", "Success": "career_travel", "Finance": "finance",
    "Health": "health", "Death": "health", "Marriage": "marriage",
    "Progeny": "progeny", "Sports": "career_travel", "Award": "career_travel",
    "Triumph": "career_travel", "Setback": "career_travel", "Relocation": "career_travel"
}

NOISE_WINDOW = 5

def init_tables(cursor):
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pattern_definitions (
        id TEXT PRIMARY KEY,
        name TEXT,
        description TEXT,
        category TEXT
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS raw_pattern_occurrences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        figure_id TEXT,
        age INTEGER,
        domain TEXT,
        fate_type TEXT,
        pattern_id TEXT,
        source_planet TEXT,
        target_planet TEXT,
        source_dignity TEXT,
        target_dignity TEXT,
        is_event BOOLEAN,
        confidence TEXT
    )
    ''')
    
    # Insert pattern definitions
    patterns = [
        ("WEAK_ANVIL", "Weak Anvil", "Target Low dignity + Aspect Hit", "Hammer and Anvil"),
        ("STRONG_SHIELD", "Strong Shield", "Target High dignity + Aspect Silence", "Hammer and Anvil"),
        ("TAKKAR_PARADOX", "Takkar Paradox", "1-8 axis with Source Low / Target Low", "Hammer and Anvil"),
        ("GALI_SWEET_SPOT", "Gali Sweet Spot", "2-6 axis with Source High / Target Medium", "Hammer and Anvil"),
        ("DOUBTFUL_RESOLUTION_6_12", "Doubtful Resolution (6-12)", "6-12 axis for RASHI_PHAL/HYBRID", "Mechanics of Fate"),
        ("DOUBTFUL_RESOLUTION_2_6", "Doubtful Resolution (2-6)", "2-6 axis for RASHI_PHAL/HYBRID", "Mechanics of Fate"),
        ("FIXED_FATE_FREEZE_1_7", "Fixed Fate Freeze (1-7)", "1-7 axis for GRAHA_PHAL", "Mechanics of Fate"),
        ("FIXED_FATE_FREEZE_3_11", "Fixed Fate Freeze (3-11)", "3-11 axis for GRAHA_PHAL", "Mechanics of Fate"),
        ("CONDITIONAL_PRECISION", "Conditional Precision", "4-10 axis for RASHI_PHAL + Target Low", "Mechanics of Fate"),
        ("FIXED_WEALTH", "Fixed Wealth Correlation", "8-2 axis for GRAHA_PHAL", "Mechanics of Fate")
    ]
    cursor.executemany("INSERT OR IGNORE INTO pattern_definitions VALUES (?, ?, ?, ?)", patterns)

def get_dignity_grade(planet: str, house: int, states: list, config: ModelConfig) -> str:
    from astroq.lk_prediction.dignity_engine import DignityEngine
    engine = DignityEngine(config)
    weights = {
        "pakka_ghar": config.get("strength.natal.pakka_ghar", fallback=2.20),
        "exalted": config.get("strength.natal.exalted", fallback=5.00),
        "debilitated": config.get("strength.natal.debilitated", fallback=-5.00),
        "fixed_house_lord": config.get("strength.natal.fixed_house_lord", fallback=1.50),
    }
    score = engine.get_dignity_score(planet, house, states, weights)
    if score >= 2.0: return "High"
    if score <= -2.0: return "Low"
    return "Medium"

def extract_patterns(annual_chart: dict, natal_chart: dict, config: ModelConfig, age: int, engine_domain: str, fate_type: str, is_event: bool, fid: str, cursor):
    ctx = UnifiedAstrologicalContext(chart=annual_chart, natal_chart=natal_chart, config=config)
    aspect_engine = AspectEngine()
    all_planets = annual_chart.get("planets_in_houses", {})
    
    # To determine hitting confidence, we use VarshphalTimingEngine, but here we just need to know if the pattern fired.
    from astroq.lk_prediction.varshphal_timing_engine import VarshphalTimingEngine
    timing_engine = VarshphalTimingEngine()
    result = timing_engine.get_timing_confidence(ctx, engine_domain, fate_type=fate_type, age=age)
    confidence = result["confidence"]
    
    occurrences = []

    for source_planet, data in all_planets.items():
        sh = data.get("house", 0)
        s_states = data.get("states", [])
        s_dig = get_dignity_grade(source_planet, sh, s_states, config)
        
        aspects = aspect_engine.calculate_planet_aspects(source_planet, sh, all_planets)
        for aspect in aspects:
            target_planet = aspect["target"]
            th = aspect["target_house"]
            axis = f"{sh}-{th}"
            
            t_data = all_planets.get(target_planet, {})
            t_states = t_data.get("states", [])
            t_dig = get_dignity_grade(target_planet, th, t_states, config)
            
            base_occ = (fid, age, engine_domain, fate_type, source_planet, target_planet, s_dig, t_dig, is_event, confidence)

            # 1. Weak Anvil
            if t_dig == "Low":
                occurrences.append(base_occ[:5] + ("WEAK_ANVIL",) + base_occ[5:])
            
            # 2. Strong Shield
            if t_dig == "High":
                occurrences.append(base_occ[:5] + ("STRONG_SHIELD",) + base_occ[5:])
            
            # 3. Takkar Paradox
            if axis == "1-8" and s_dig == "Low" and t_dig == "Low":
                occurrences.append(base_occ[:5] + ("TAKKAR_PARADOX",) + base_occ[5:])
            
            # 4. Gali Sweet Spot
            if axis == "2-6" and s_dig == "High" and t_dig == "Medium":
                occurrences.append(base_occ[:5] + ("GALI_SWEET_SPOT",) + base_occ[5:])
                
            # 5. Doubtful Resolution
            if fate_type in ["RASHI_PHAL", "HYBRID"]:
                if axis == "6-12":
                    occurrences.append(base_occ[:5] + ("DOUBTFUL_RESOLUTION_6_12",) + base_occ[5:])
                if axis == "2-6":
                    occurrences.append(base_occ[:5] + ("DOUBTFUL_RESOLUTION_2_6",) + base_occ[5:])
            
            # 6. Fixed Fate Freeze
            if fate_type == "GRAHA_PHAL":
                if axis == "1-7":
                    occurrences.append(base_occ[:5] + ("FIXED_FATE_FREEZE_1_7",) + base_occ[5:])
                if axis == "3-11":
                    occurrences.append(base_occ[:5] + ("FIXED_FATE_FREEZE_3_11",) + base_occ[5:])
                    
            # 7. Conditional Precision
            if fate_type == "RASHI_PHAL" and axis == "4-10" and t_dig == "Low":
                occurrences.append(base_occ[:5] + ("CONDITIONAL_PRECISION",) + base_occ[5:])
                
            # 8. Fixed Wealth Correlation
            if fate_type == "GRAHA_PHAL" and axis == "8-2":
                occurrences.append(base_occ[:5] + ("FIXED_WEALTH",) + base_occ[5:])

    if occurrences:
        cursor.executemany('''
            INSERT INTO raw_pattern_occurrences 
            (figure_id, age, domain, fate_type, source_planet, pattern_id, target_planet, source_dignity, target_dignity, is_event, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', occurrences)

def main():
    db_path = os.path.join("backend", "data", "config.db")
    defaults_path = os.path.join("backend", "data", "model_defaults.json")
    pf_db_path = os.path.join("backend", "data", "public_figures.db")

    config = ModelConfig(db_path, defaults_path)
    fate_view = NatalFateView()

    conn = sqlite3.connect(pf_db_path)
    cursor = conn.cursor()
    
    init_tables(cursor)
    cursor.execute("DELETE FROM raw_pattern_occurrences") # Reset
    conn.commit()
    
    cursor.execute("SELECT id, natal_chart_json, annual_charts_json FROM public_figures WHERE natal_chart_json IS NOT NULL")
    figure_rows = cursor.fetchall()
    
    total = len(figure_rows)
    print(f"Loaded {total} public figures.")

    for idx, (fid, natal_str, annual_str) in enumerate(figure_rows, 1):
        print(f"\rProcessing {idx}/{total}...", end="", flush=True)
        try:
            natal = json.loads(natal_str)
            annuals = json.loads(annual_str)
        except Exception: continue
        
        fate_entries = fate_view.evaluate(natal)
        fate_by_domain = {e["domain"]: e["fate_type"] for e in fate_entries}

        cursor.execute("SELECT event, date, type FROM life_events WHERE figure_id = ?", (fid,))
        event_rows = cursor.fetchall()
        
        birth_year = 0
        b_time = natal.get("birth_time", "")
        if b_time:
            try: birth_year = int(b_time[:4])
            except: pass
            
        event_ages = set()
        valid_events = []
        death_age = None
        for e in event_rows:
            date_str = e[1]
            if not date_str or not birth_year: continue
            try:
                age = int(date_str[:4]) - birth_year
                if 0 < age <= 100:
                    event_ages.add(age)
                    valid_events.append({"age": age, "type": e[2], "event": e[0]})
                    if e[2] and e[2].lower() == "death" and death_age is None:
                        death_age = age
            except: pass
            
        for ev in valid_events:
            age = ev["age"]
            engine_domain = DOMAIN_MAP.get(ev.get("type", "Career"), "career_travel")
            fate_type = fate_by_domain.get(engine_domain, "RASHI_PHAL")
            
            annual = annuals.get(f"chart_{age}")
            if annual:
                extract_patterns(annual, natal, config, age, engine_domain, fate_type, True, fid, cursor)
                
            # Noise years — capped at death_age if known
            max_noise_age = death_age if death_age else (age + NOISE_WINDOW)
            for n_age in range(max(1, age - NOISE_WINDOW), min(max_noise_age, age + NOISE_WINDOW) + 1):
                if n_age == age or n_age in event_ages: continue
                n_annual = annuals.get(f"chart_{n_age}")
                if n_annual:
                    extract_patterns(n_annual, natal, config, n_age, engine_domain, fate_type, False, fid, cursor)

    conn.commit()
    conn.close()
    print("\nPattern extraction complete!")

if __name__ == "__main__":
    main()
