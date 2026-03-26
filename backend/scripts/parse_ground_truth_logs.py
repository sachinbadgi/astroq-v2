import re
import json
import os

LOG_PATH = "D:/astroq-mar26/timing_debug.txt"
OUTPUT_PATH = "backend/data/public_figures_ground_truth_v2.json"

def parse_logs():
    with open(LOG_PATH, "r") as f:
        content = f.read()
    
    # Regex to find: [DEBUG FigureName] Events: [('Event', Age), ...]
    # Handle leading spaces and multi-line
    pattern = r"\[DEBUG\s+(.*?)\]\s+Events:\s+\[(.*?)\]"
    matches = re.findall(pattern, content)
    
    dataset = []
    seen_ids = set()
    
    # Directory with charts
    CHART_DIR = "backend/tests/data/public_figures/"
    
    for name, events_str in matches:
        # Map Name to Filename
        # Example: "Abraham Lincoln" -> "abraham_lincoln_enriched_chart.json"
        chart_id = name.lower().replace(" ", "_").replace(".", "")
        if chart_id in seen_ids: continue
        
        filename = f"{chart_id}_enriched_chart.json"
        # Special case for "Lincoln" in logs (which might be Abraham Lincoln)
        if chart_id == "lincoln": filename = "abraham_lincoln_enriched_chart.json"
        
        chart_path = os.path.join(CHART_DIR, filename)
        if not os.path.exists(chart_path):
            # Try fuzzy match? (e.g. "Lincoln" in many files)
            print(f"Skipping {name} (chart not found at {chart_path})")
            continue
            
        with open(chart_path, "r") as cf:
            chart_data = json.load(cf)
            # Use chart_0 as the "chart"
            if "chart_0" not in chart_data: continue
            birth_chart = chart_data["chart_0"]

        # Parse events: ('Elected President', 51)
        event_matches = re.findall(r"\('(.*?)',\s+(\d+)\)", events_str)
        
        events = []
        for desc, age in event_matches:
            age = int(age)
            # Default to career for these extracted ones
            domain = "career"
            planet = "Sun"
            bench = 22
            
            events.append({
                "age": age,
                "domain": domain,
                "bench": bench,
                "planet": planet,
                "description": desc
            })
            
        if events:
            dataset.append({
                "id": chart_id,
                "name": name,
                "chart": birth_chart, # BatchRunner wants this
                "events": events
            })
            seen_ids.add(chart_id)
                
    # Also search for "Figure                 | Domain       | Avg Offset" table entries if any
    # (The table at the end of timing_debug.txt also has names)
    
    with open(OUTPUT_PATH, "w") as f:
        json.dump(dataset, f, indent=2)
        
    print(f"Parsed {len(dataset)} figures from logs to {OUTPUT_PATH}")

if __name__ == "__main__":
    parse_logs()
