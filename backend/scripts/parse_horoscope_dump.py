import re
import json
import os

DB_DUMP_PATH = "D:/astroq-mar26/horoscope_db.db"
OUTPUT_PATH = "backend/data/public_figures_ground_truth_v2.json"
CHART_DIR = "backend/tests/data/public_figures/"

def parse_dump():
    print(f"Reading {DB_DUMP_PATH} as binary...")
    with open(DB_DUMP_PATH, "rb") as f:
        raw_data = f.read()
    
    print(f"Total Bytes Read: {len(raw_data)}")
    if not raw_data:
        print("Empty raw data!")
        return
        
    try:
        content = raw_data.decode("utf-16")
    except Exception as e:
        print(f"UTF-16 Decode Failed: {e}")
        return
    
    lines = content.splitlines()
    print(f"Total Lines: {len(lines)}")
    
    figures = {} # figure_id -> name
    events = {}  # figure_id -> list of events
    
    current_table = None
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line: continue
        
        # Detect table headers (case-insensitive, fuzzy)
        if "Table:" in line:
            if "public_figures" in line.lower():
                current_table = "public_figures"
                print(f"Found Table: public_figures at line {i}")
            elif "life_events" in line.lower():
                current_table = "life_events"
                print(f"Found Table: life_events at line {i}")
            continue
            
        if current_table == "public_figures":
            # Format: ID: amitabh_bachchan | Name: Amitabh Bachchan | ...
            if "ID:" not in line or "|" not in line: continue
            m = re.search(r"ID:\s*(.*?)\s*\|\s*Name:\s*(.*?)\s*($|\|)", line)
            if m:
                fig_id = m.group(1).strip()
                name = m.group(2).strip()
                figures[fig_id] = name
                
        elif current_table == "life_events":
            # Format: ID: ev_1 | Figure: amitabh_bachchan | Age: 31 | Domain: Profession | Description: Zanjeer
            if "ID:" not in line or "|" not in line: continue
            m = re.search(r"ID:\s*(.*?)\s*\|\s*Figure:\s*(.*?)\s*\|\s*Age:\s*(\d+)\s*\|\s*Domain:\s*(.*?)\s*\|\s*Description:\s*(.*)", line)
            if m:
                fig_id = m.group(2).strip()
                age = int(m.group(3))
                domain = m.group(4).strip().lower()
                desc = m.group(5).strip()
                
                if fig_id not in events: events[fig_id] = []
                
                # Normalize domain
                if "profession" in domain or "career" in domain: domain = "career"
                elif "health" in domain: domain = "health"
                elif "marriage" in domain: domain = "marriage"
                else: domain = "career"
                
                planet = "Sun"
                if domain == "marriage": planet = "Venus"
                elif domain == "health": planet = "Saturn"
                
                events[fig_id].append({
                    "age": age,
                    "domain": domain,
                    "bench": 22 if planet == "Sun" else 25 if planet == "Venus" else 36,
                    "planet": planet,
                    "description": desc
                })

    # Join with charts
    dataset = []
    for fig_id, name in figures.items():
        if fig_id not in events: continue
        
        # Find chart file
        chart_filename = f"{fig_id}_enriched_chart.json"
        # Special case: some IDs might be "a_p_j_abdul_kalam" but filename is different?
        # We'll check if the file exists.
        chart_path = os.path.join(CHART_DIR, chart_filename)
        
        if not os.path.exists(chart_path):
            # Try fuzzy mapping if needed
            continue
            
        with open(chart_path, "r") as cf:
            chart_data = json.load(cf)
            if "chart_0" not in chart_data: continue
            birth_chart = chart_data["chart_0"]
            
        dataset.append({
            "id": fig_id,
            "name": name,
            "chart": birth_chart,
            "events": events[fig_id]
        })
        
    with open(OUTPUT_PATH, "w") as f:
        json.dump(dataset, f, indent=2)
        
    print(f"Extracted {len(dataset)} figures and {sum(len(d['events']) for d in dataset)} events to {OUTPUT_PATH}")

if __name__ == "__main__":
    parse_dump()
