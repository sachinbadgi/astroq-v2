import sqlite3
import json
import sys
import os
import re

# Add backend directory to path to import astroq
sys.path.append(os.path.abspath(".."))
from astroq.lk_prediction.chart_generator import ChartGenerator

DB_PATH = "public_figures.db"

def extract_utc_offset(tz_str):
    if not tz_str:
        return "+00:00"
    match = re.search(r'([+-]\d{2}:\d{2})', tz_str)
    if match:
        return match.group(1)
    if "IST" in tz_str: return "+05:30"
    if "EST" in tz_str: return "-05:00"
    if "EDT" in tz_str: return "-04:00"
    if "CST" in tz_str: return "-06:00"
    if "PST" in tz_str: return "-08:00"
    if "PDT" in tz_str: return "-07:00"
    if "GMT" in tz_str or "UTC" in tz_str or "LMT" in tz_str: return "+00:00"
    return "+00:00"

def run():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all figures
    cursor.execute('''
        SELECT id, name, birth_date, birth_time, time_zone, birth_place, lat, lon
        FROM public_figures
        
    ''')
    rows = cursor.fetchall()
    
    total = len(rows)
    print(f"Found {total} figures to process...")
    
    gen = ChartGenerator()
    
    for idx, row in enumerate(rows, 1):
        fid, name, dob, tob, tz, place, lat, lon = row
        print(f"[{idx}/{total}] Generating charts for {name} ({dob})...", end='', flush=True)
        
        # Format time to ensure HH:MM:SS
        if tob and len(tob) == 5:
            tob = tob + ":00"
            
        clean_tz = extract_utc_offset(tz)
            
        try:
            payload = gen.build_full_chart_payload(
                dob_str=dob,
                tob_str=tob,
                place_name=place,
                latitude=lat,
                longitude=lon,
                utc_string=clean_tz,
                chart_system="vedic"
            )
            
            natal_chart = payload.get("chart_0")
            annual_charts = {k: v for k, v in payload.items() if k.startswith("chart_") and k != "chart_0"}
            
            cursor.execute('''
                UPDATE public_figures 
                SET natal_chart_json = ?, annual_charts_json = ?
                WHERE id = ?
            ''', (
                json.dumps(natal_chart),
                json.dumps(annual_charts),
                fid
            ))
            conn.commit()
            print(" Done.")
            
        except Exception as e:
            print(f" ERROR: {e}")
            conn.rollback()

    conn.close()
    print("Chart generation complete.")

if __name__ == "__main__":
    run()
