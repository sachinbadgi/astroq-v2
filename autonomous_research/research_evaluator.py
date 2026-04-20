import sqlite3
import os
import sys
import logging
import re
import importlib.util

# Ensure backend is in path
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), "backend")))

from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.pipeline import LKPredictionPipeline
from astroq.lk_prediction.config import ModelConfig

# CONFIG
DB_PATH = "backend/data/astroq_gt.db"
DEFAULTS_PATH = "backend/data/model_defaults.json"
RESEARCH_LOGIC_PATH = "autonomous_research/research_logic.py"

def normalize_name(name: str) -> str:
    return re.sub(r'[^a-zA-Z0-9]', '', name.lower())

def load_research_weights():
    spec = importlib.util.spec_from_file_location("research_logic", RESEARCH_LOGIC_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, "RESEARCH_PARAMS", {})

def fetch_ground_truth():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, client_name, birth_date, birth_time, birth_place, latitude, longitude, timezone_name FROM lk_birth_charts LIMIT 25")
    charts = cursor.fetchall()
    
    cursor.execute("SELECT figure_name, event_name, age, domain FROM benchmark_ground_truth")
    events = cursor.fetchall()
    conn.close()
    
    events_map = {}
    for fig, ev, age, dom in events:
        norm = normalize_name(fig)
        if norm not in events_map: events_map[norm] = []
        events_map[norm].append({"age": age, "domain": dom.lower() if dom else "career", "desc": ev})
    
    data = []
    for c in charts:
        cid, name, dob, tob, place, lat, lon, tz = c
        norm = normalize_name(name)
        if norm in events_map:
            data.append({"name": name, "dob": dob, "tob": tob, "place": place, "lat": lat, "lon": lon, "tz": tz, "events": events_map[norm]})
    return data

def calculate_whr(predictions, ground_truth_events):
    score = 0.0
    total = len(ground_truth_events)
    if total == 0: return 0.0
    
    # Simple mapping for speed
    # pred: list of LKPrediction objects
    for gt in ground_truth_events:
        gt_age = gt["age"]
        gt_domain = gt["domain"]
        
        # Find matches in predictions
        matches = [p for p in predictions if p.domain.lower() == gt_domain]
        if not matches: continue
        
        # Sort matches by probability DESC
        matches.sort(key=lambda x: x.probability, reverse=True)
        top_3 = matches[:3]
        
        # 1. Exact or near match in peak_age
        found_hit = False
        for p in matches:
            offset = abs(p.peak_age - gt_age)
            if offset == 0:
                score += 1.0
                found_hit = True
                break
            elif offset == 1:
                score += 0.5
                found_hit = True
                break
        
        # 2. Competitive bonus (Top 3)
        # Even if age offset is > 1, if the GT age falls within the window of a Top 3 prediction
        if not found_hit:
            for p in top_3:
                # If GT age is within predicted window
                start, end = p.age_window
                if start <= gt_age <= end:
                    score += 0.25 # Minor credit for window match
                    break

    return round(score / total, 4)

def run_evaluation():
    print(f"Loading research weights from {RESEARCH_LOGIC_PATH}...")
    weights = load_research_weights()
    
    print(f"Loading figures from {DB_PATH}...")
    figures = fetch_ground_truth()
    
    generator = ChartGenerator()
    config = ModelConfig(db_path=DB_PATH, defaults_path=DEFAULTS_PATH)
    config.set_volatile_overrides(weights) # INJECTION
    
    pipeline = LKPredictionPipeline(config)
    total_whr = 0.0
    
    print(f"Starting evaluation of {len(figures)} figures...")
    for fig in figures:
        try:
            full_payload = generator.build_full_chart_payload(
                dob_str=fig['dob'], tob_str=fig['tob'],
                place_name=fig['place'], latitude=fig['lat'], 
                longitude=fig['lon'], utc_string=fig['tz']
            )
            natal_chart = full_payload["chart_0"]
            annual_charts = {int(k.split("_")[1]): v for k, v in full_payload.items() if k.startswith("chart_") and k != "chart_0"}
            
            pipeline.load_natal_baseline(natal_chart)
            all_predictions = []
            
            # Predict for relevant ages [GT - 2, GT + 2]
            target_ages = set()
            for ev in fig['events']:
                for a in range(ev['age'] - 1, ev['age'] + 2):
                    if 0 <= a <= 75: target_ages.add(a)
            
            for age in sorted(target_ages):
                if age in annual_charts:
                    preds = pipeline.generate_predictions(annual_charts[age])
                    all_predictions.extend(preds)
            
            whr = calculate_whr(all_predictions, fig['events'])
            total_whr += whr
            print(f"  {fig['name']}: WHR = {whr}")
            
        except Exception as e:
            print(f"  Error processing {fig['name']}: {str(e)}")
            continue

    final_score = round(total_whr / len(figures), 4) if figures else 0.0
    print(f"\nFINAL_SCORE: {final_score}")

if __name__ == "__main__":
    run_evaluation()
