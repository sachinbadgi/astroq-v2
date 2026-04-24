import os
import json
import re
from datetime import datetime

md_path = os.path.join("reference-docs", "Public_Figures_Birth_Data.md")
json_path = os.path.join("backend", "data", "public_figures_ground_truth.json")

def parse_markdown_table(md_content):
    lines = md_content.strip().split('\n')
    records = []
    # Find start of table
    start_idx = 0
    for i, line in enumerate(lines):
        if '| Name' in line and 'Date' in line:
            start_idx = i + 2 # skip header and separator
            break
            
    for line in lines[start_idx:]:
        if not line.strip() or not line.startswith('|'): continue
        parts = [p.strip() for p in line.split('|')][1:-1]
        if len(parts) >= 5:
            name, dob, tob, place, events_str = parts[:5]
            if dob == "nan" or not dob: continue
            
            # Format tob
            if 'AM' in tob or 'PM' in tob:
                try:
                    tob_obj = datetime.strptime(tob, "%I:%M %p")
                    tob = tob_obj.strftime("%H:%M")
                except:
                    pass
            
            birth_year = int(dob.split('-')[0])
            
            events = []
            for ev in events_str.split(';'):
                ev = ev.strip()
                if not ev: continue
                # Match date like "Oct 7, 2001: Sworn in as CM"
                match = re.match(r'([A-Za-z]+\s+\d{1,2},?\s+(\d{4})):?\s*(.*)', ev)
                if not match:
                    # Try just year like "1945: Torna Fort capture"
                    match = re.match(r'(.*?(\d{4})[^:]*):?\s*(.*)', ev)
                
                if match:
                    year_str = match.group(2)
                    desc = match.group(3)
                    year = int(year_str)
                    age = year - birth_year
                    if age > 0:
                        domain = "other"
                        lower_desc = desc.lower()
                        if "marriage" in lower_desc or "wedding" in lower_desc or "marriage to" in lower_desc:
                            domain = "marriage"
                        elif "passing" in lower_desc or "accident" in lower_desc or "diagnosis" in lower_desc:
                            domain = "health"
                        elif "ceo" in lower_desc or "founded" in lower_desc or "win" in lower_desc or "elected" in lower_desc or "release" in lower_desc or "debut" in lower_desc or "award" in lower_desc or "prize" in lower_desc:
                            domain = "career"
                        elif "birth" in lower_desc:
                            domain = "progeny"
                        
                        events.append({
                            "age": age,
                            "year": year,
                            "domain": domain,
                            "description": desc
                        })
                        
            records.append({
                "name": name,
                "dob": dob,
                "tob": tob,
                "birth_place": place,
                "events": events
            })
    return records

def merge_data():
    with open(md_path, "r") as f:
        md_records = parse_markdown_table(f.read())
        
    with open(json_path, "r") as f:
        json_records = json.load(f)
        
    existing_names = {r["name"].lower(): r for r in json_records}
    added = 0
    updated = 0
    
    for md_r in md_records:
        name_lower = md_r["name"].lower()
        if name_lower in existing_names:
            # Update existing if it lacks events
            existing = existing_names[name_lower]
            if len(existing.get("events", [])) < len(md_r["events"]):
                existing["events"] = md_r["events"]
                updated += 1
        else:
            json_records.append(md_r)
            added += 1
            
    with open(json_path, "w") as f:
        json.dump(json_records, f, indent=2)
        
    print(f"Merged Markdown data! Added {added} new records, updated {updated} existing records. Total records: {len(json_records)}")

if __name__ == "__main__":
    merge_data()
