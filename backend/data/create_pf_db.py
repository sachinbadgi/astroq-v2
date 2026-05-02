import json
import sqlite3
import glob
import os

DB_PATH = "public_figures.db"
JSON_DIR = "puplic_figures_data"

def init_db(conn):
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS public_figures (
        id TEXT PRIMARY KEY,
        name TEXT,
        category TEXT,
        birth_date TEXT,
        birth_time TEXT,
        time_zone TEXT,
        birth_place TEXT,
        lat REAL,
        lon REAL,
        rodden_rating TEXT
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS life_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        figure_id TEXT,
        event TEXT,
        date TEXT,
        type TEXT,
        FOREIGN KEY(figure_id) REFERENCES public_figures(id)
    )
    ''')
    conn.commit()

def load_data():
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    cursor = conn.cursor()
    
    total_figures = 0
    total_events = 0
    
    for filepath in glob.glob(os.path.join(JSON_DIR, "*.json")):
        with open(filepath, 'r') as f:
            try:
                data = json.load(f)
                for item in data:
                    # Insert figure
                    coords = item.get("coordinates", {})
                    lat = coords.get("lat")
                    lon = coords.get("lon")
                    
                    cursor.execute('''
                    INSERT OR REPLACE INTO public_figures 
                    (id, name, category, birth_date, birth_time, time_zone, birth_place, lat, lon, rodden_rating)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.get("id"), item.get("name"), item.get("category"),
                        item.get("birth_date"), item.get("birth_time"), item.get("time_zone"),
                        item.get("birth_place"), lat, lon, item.get("rodden_rating")
                    ))
                    total_figures += 1
                    
                    # Delete existing events for this figure to avoid duplicates on rerun
                    cursor.execute('DELETE FROM life_events WHERE figure_id = ?', (item.get("id"),))
                    
                    # Insert events
                    events = item.get("life_events", [])
                    for event in events:
                        cursor.execute('''
                        INSERT INTO life_events (figure_id, event, date, type)
                        VALUES (?, ?, ?, ?)
                        ''', (item.get("id"), event.get("event"), event.get("date"), event.get("type")))
                        total_events += 1
                        
            except json.JSONDecodeError:
                print(f"Error decoding {filepath}")
                
    conn.commit()
    conn.close()
    print(f"Successfully loaded {total_figures} public figures and {total_events} life events into {DB_PATH}.")

if __name__ == "__main__":
    load_data()
