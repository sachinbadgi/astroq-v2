import sqlite3
import json
import os

DB_PATH = "d:/astroq-v2/backend/data/horoscope_db_temp.db"
OUTPUT_PATH = "d:/astroq-v2/backend/data/public_figures_ground_truth_v2.json"
CHART_DIR = "d:/astroq-v2/backend/tests/data/public_figures"

def extract_data():
    if not os.path.exists(DB_PATH):
        print(f"CRITICAL ERROR: {DB_PATH} does not exist!")
        return
        
    print(f"Connecting to {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Debug: Print all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cursor.fetchall()]
    print(f"Tables found in DB: {tables}")
    
    if "public_figures" not in tables:
        print("ERROR: 'public_figures' table not found!")
        return
    
    # Get all figures
    
    # Get all events
    cursor.execute("SELECT figure_id, age, event_type, description FROM life_events")
    events = cursor.fetchall()
    print(f"Found {len(events)} events in DB")
    
    # Map events to figures
    fig_events_map = {}
    for fig_id, age, e_type, desc in events:
        if fig_id not in fig_events_map:
            fig_events_map[fig_id] = []
        
        # Normalize domain
        domain = e_type.lower()
        if "profession" in domain or "career" in domain: domain = "career"
        elif "marriage" in domain: domain = "marriage"
        elif "health" in domain: domain = "health"
        else: domain = "career" # Fallback
        
        # Benchmarks
        planet = "Sun" if domain == "career" else "Venus" if domain == "marriage" else "Saturn"
        bench = 22 if planet == "Sun" else 25 if planet == "Venus" else 36
        
        fig_events_map[fig_id].append({
            "age": age,
            "domain": domain,
            "bench": bench,
            "planet": planet,
            "description": desc
        })
        
    # Join with charts
    dataset = []
    for f_id, f_name in figures:
        # Check if we have the chart file
        chart_filename = f"{f_id}_enriched_chart.json"
        chart_path = os.path.join(CHART_DIR, chart_filename)
        
        if os.path.exists(chart_path):
            with open(chart_path, "r") as f:
                chart_data = json.load(f)
                birth_chart = chart_data.get("chart_0")
                if birth_chart:
                    dataset.append({
                        "id": f_id,
                        "name": f_name,
                        "chart": birth_chart,
                        "events": fig_events_map.get(f_id, [])
                    })
        else:
            # Maybe skip silent failures or Log the skip
            print(f"Skipping {f_name} ({f_id}) - Chart not found at {chart_path}")
            
    # Output to JSON
    with open(OUTPUT_PATH, "w") as f:
        json.dump(dataset, f, indent=2)
        
    print(f"Successfully unified {len(dataset)} figures into {OUTPUT_PATH}")

if __name__ == "__main__":
    extract_data()
