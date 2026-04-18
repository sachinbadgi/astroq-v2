import sqlite3
import json
import os

DB_PATH = "backend/data/astroq_gt.db"

def populate():
    # Load JSON
    with open("backend/data/public_figures_ground_truth.json", "r") as f:
        data = json.load(f)
        
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE lk_birth_charts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT,
            birth_date TEXT,
            birth_time TEXT,
            birth_place TEXT,
            latitude REAL,
            longitude REAL,
            timezone_name TEXT
        )
    """)
    
    cur.execute("""
        CREATE TABLE benchmark_ground_truth (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            figure_name TEXT,
            event_name TEXT,
            age INTEGER,
            domain TEXT,
            event_date TEXT
        )
    """)
    
    cur.execute("""
        CREATE TABLE chart_dna (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            figure_id TEXT UNIQUE,
            chart_dna_blob TEXT,
            confidence_score REAL,
            iterations_run INTEGER,
            back_test_hit_rate REAL,
            mean_offset_years REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    for fig in data:
        name = fig["name"]
        dob = fig["dob"]
        tob = fig["tob"]
        place = "Delhi, India" # Placeholder
        lat = 0.0
        lon = 0.0
        tz = "+05:30"
        
        # Hardcode some well-known ones to prevent geocode failures
        if name == "Amitabh Bachchan": place = "Allahabad, India"; lat=25.4358; lon=81.8463
        elif name == "Sachin Tendulkar": place = "Mumbai, India"; lat=19.0760; lon=72.8777
        elif name == "Narendra Modi": place = "Vadnagar, India"; lat=23.7825; lon=72.6366
        
        cur.execute("""
            INSERT INTO lk_birth_charts 
            (client_name, birth_date, birth_time, birth_place, latitude, longitude, timezone_name)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, dob, tob, place, lat, lon, tz))
        
        for ev in fig.get("events", []):
            desc = ev.get("description", "")
            age = ev.get("age", 0)
            domain = ev.get("domain", "")
            cur.execute("""
                INSERT INTO benchmark_ground_truth
                (figure_name, event_name, age, domain, event_date)
                VALUES (?, ?, ?, ?, ?)
            """, (name, desc, age, domain, None))
            
    conn.commit()
    conn.close()
    print("Database built successfully!")

if __name__ == "__main__":
    populate()
