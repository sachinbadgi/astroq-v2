import sqlite3
import json
import os

# Paths
DB_PATH = "backend/data/astroq_gt.db"
OUTPUT_PATH = "backend/data/public_figures_ground_truth_v2.json"

def extract():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all figures
    cursor.execute("SELECT id, name FROM public_figures")
    figures = cursor.fetchall()
    
    dataset = []
    
    # Domain Mapping
    DOMAIN_MAP = {
        "Profession": "career",
        "Marriage": "marriage",
        "Health": "health",
        "Fame": "career",
        "Politics": "career",
        "Sports": "career"
    }
    
    # Benchmark Mapping
    BENCH_MAP = {
        "Sun": 22,
        "Saturn": 36,
        "Venus": 25,
        "Jupiter": 16,
        "Mars": 28,
        "Mercury": 34,
        "Rahu": 42,
        "Ketu": 48
    }

    for fig_id, name in figures:
        # Get events for this figure
        cursor.execute("SELECT description, event_age, event_type FROM life_events WHERE public_figure_id = ?", (fig_id,))
        events_raw = cursor.fetchall()
        
        events = []
        for desc, age, e_type in events_raw:
            domain = DOMAIN_MAP.get(e_type, "career")
            
            # Simple planet heuristic for the extracted data
            # (In a real scenario, we'd check the chart, but for ground truth mapping, we use domain benchmarks)
            planet = "Sun"
            if domain == "marriage": planet = "Venus"
            elif domain == "health": planet = "Saturn"
            elif domain == "career": planet = "Sun"
            
            bench = BENCH_MAP.get(planet, 22)
            
            events.append({
                "age": age,
                "domain": domain,
                "bench": bench,
                "planet": planet,
                "description": desc
            })
            
        if events:
            # Chart Path Heuristic (align with existing enriched charts)
            chart_id = name.lower().replace(" ", "_").replace(".", "")
            
            dataset.append({
                "id": chart_id,
                "name": name,
                "events": events
            })
            
    conn.close()
    
    with open(OUTPUT_PATH, "w") as f:
        json.dump(dataset, f, indent=2)
        
    print(f"Extracted {len(dataset)} figures and {sum(len(d['events']) for d in dataset)} events to {OUTPUT_PATH}")

if __name__ == "__main__":
    extract()
