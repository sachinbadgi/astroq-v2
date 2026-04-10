import sys
import os
import sqlite3
import json

# Ensure backend is in path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.lse_validator import ValidatorAgent
from astroq.lk_prediction.data_contracts import LifeEventLog

def check_fp(figure_id):
    db_path = "backend/data/astroq_gt.db"
    defaults_path = "backend/data/model_defaults.json"
    
    config = ModelConfig(db_path=db_path, defaults_path=defaults_path)
    generator = ChartGenerator()
    validator = ValidatorAgent()
    
    # 1. Load Life Events
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Get birth chart 
    chart_row = cur.execute("""
        SELECT birth_date, birth_time, birth_place, latitude, longitude, utc_offset, client_name 
        FROM lk_birth_charts WHERE client_name = ?
    """, (figure_id,)).fetchone()
    
    if not chart_row:
        # Try searching by figure_id if client_name doesn't match
        chart_row = cur.execute("""
            SELECT birth_date, birth_time, birth_place, latitude, longitude, utc_offset, client_name 
            FROM lk_birth_charts WHERE client_name LIKE ?
        """, (f"%{figure_id}%",)).fetchone()
        
    if not chart_row:
        print(f"Figure {figure_id} not found.")
        return
        
    birth_chart = {
        "date": chart_row[0],
        "time": chart_row[1],
        "place": chart_row[2],
        "lat": chart_row[3],
        "lon": chart_row[4],
        "tz": chart_row[5],
        "name": chart_row[6]
    }
    
    # Get ground truth events
    events_rows = cur.execute("""
        SELECT domain, age, event_name FROM benchmark_ground_truth WHERE figure_name = ?
    """, (figure_id,)).fetchall()
    life_event_log = [{"domain": r[0], "age": r[1], "description": r[2]} for r in events_rows]
    
    # 2. Get stored DNA overrides
    dna_row = cur.execute("SELECT config_overrides_json FROM chart_dna WHERE figure_id = ?", (figure_id,)).fetchone()
    if not dna_row:
        # try figure_name if figure_id check fails
        dna_row = cur.execute("SELECT config_overrides_json FROM chart_dna WHERE figure_id LIKE ?", (f"%{figure_id}%",)).fetchone()
    
    overrides = json.loads(dna_row[0]) if dna_row else {}
    
    # 3. Generate baseline predictions
    print("Generating natal chart...", flush=True)
    natal_chart = generator.generate_chart(
        dob_str=birth_chart["date"],
        tob_str=birth_chart["time"],
        place_name=birth_chart["place"],
        latitude=birth_chart["lat"],
        longitude=birth_chart["lon"],
        utc_string=birth_chart["tz"]
    )
    print("Generating 75 annual charts...", flush=True)
    annual_charts = generator.generate_annual_charts(natal_chart, max_years=75)
    
    print("Initializing Pipeline...", flush=True)
    from astroq.lk_prediction.pipeline import LKPredictionPipeline
    pipeline = LKPredictionPipeline(config)
    pipeline.load_natal_baseline(natal_chart)
    
    print("Generating predictions across 75 years...", flush=True)
    baseline_predictions = []
    # Natal
    baseline_predictions.extend(pipeline.generate_predictions(natal_chart))
    # Annuals
    for age in range(1, 76):
        if age % 10 == 0: print(f"  Processed age {age}...", flush=True)
        chart_key = f"chart_{age}"
        if chart_key in annual_charts:
            baseline_predictions.extend(pipeline.generate_predictions(annual_charts[chart_key]))
            
    print(f"Total predictions generated: {len(baseline_predictions)}", flush=True)
    from dataclasses import replace
    predictions = [replace(p) for p in baseline_predictions]
    
    # 4. Apply overrides manually (simulating LSEOrchestrator)
    print("Applying DNA overrides...", flush=True)
    for p in predictions:
        for planet in p.source_planets:
            for k, v in overrides.items():
                if k.startswith("align.") and planet.lower() in k.lower():
                    p.peak_age = int(v)
                    break
                if k.startswith("delay.") and planet.lower() in k.lower():
                    p.peak_age += float(v)
                    break
                    
    # 5. Validate with upgraded ValidatorAgent
    print("Running ValidatorAgent...", flush=True)
    gap_report = validator.compare_to_events(predictions, life_event_log)
    
    print(f"\nReport for {figure_id}:", flush=True)
    print(f"Hits: {gap_report['hits']}/{gap_report['total']}", flush=True)
    print(f"False Positives (Redundant Predictions): {len(gap_report['false_positives'])}", flush=True)
    for fp in gap_report['false_positives'][:10]:
        print(f"  - {fp}", flush=True)
    if len(gap_report['false_positives']) > 10:
        print(f"  ... and {len(gap_report['false_positives']) - 10} more.", flush=True)

if __name__ == "__main__":
    print("Starting False Positive Audit...", flush=True)
    check_fp("Steve Jobs")
    print("Audit Complete.", flush=True)
