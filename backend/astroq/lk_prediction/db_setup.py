"""
Research Loop: Database Setup
=============================
Initializes the ground truth database for public figures.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "research_ground_truth.db")

def init_db():
    print(f"Initializing database at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Clear existing data for a clean re-seed
    cursor.execute("DELETE FROM public_figure_events")

    # Create table for public figure events
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS public_figure_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            figure_id TEXT NOT NULL,
            age INTEGER NOT NULL,
            domain TEXT NOT NULL,
            actual_score REAL NOT NULL,
            event_type TEXT,
            description TEXT
        )
    """)

    # Seed data from public_figures_ground_truth.json
    figures = [
        ('amitabh_bachchan', 31, 'career', 0.98, 'PEAK', 'Zanjeer stardom'),
        ('amitabh_bachchan', 40, 'health', 0.10, 'CRISIS', 'Coolie accident'),
        ('sachin_tendulkar', 16, 'career', 0.90, 'EVENT', 'Debut'),
        ('sachin_tendulkar', 38, 'career', 0.99, 'PEAK', 'World Cup'),
        ('narendra_modi', 51, 'career', 0.95, 'PEAK', 'Chief Minister'),
        ('narendra_modi', 64, 'career', 0.99, 'PEAK', 'Prime Minister'),
        ('steve_jobs', 21, 'career', 0.90, 'PEAK', 'Founding Apple'),
        ('steve_jobs', 30, 'career', 0.05, 'CRISIS', 'Fired from Apple'),
        ('bill_gates', 20, 'career', 0.95, 'PEAK', 'Microsoft'),
        ('bill_gates', 66, 'marriage', 0.20, 'CRISIS', 'Divorce'),
        ('princess_diana', 20, 'marriage', 0.95, 'EVENT', 'Marriage'),
        ('princess_diana', 36, 'health', 0.01, 'CRISIS', 'Assassination'),
        ('shah_rukh_khan', 27, 'career', 0.90, 'EVENT', 'Debut'),
        ('michael_jackson', 24, 'career', 0.99, 'PEAK', 'Thriller'),
        ('indira_gandhi', 49, 'career', 0.98, 'PEAK', 'Prime Minister'),
        ('elon_musk', 31, 'career', 0.90, 'PEAK', 'SpaceX')
    ]
    
    for fig in figures:
        cursor.execute("""
            INSERT INTO public_figure_events (figure_id, age, domain, actual_score, event_type, description)
            VALUES (?, ?, ?, ?, ?, ?)
        """, fig)

    conn.commit()
    conn.close()
    print("Database initialized and seed data inserted.")

if __name__ == "__main__":
    init_db()
