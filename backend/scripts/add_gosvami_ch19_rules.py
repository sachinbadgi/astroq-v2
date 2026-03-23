import sqlite3
import json
import os
import sys

# Connect to rules.db
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'rules.db'))

def seed_ch19_health_rules(target_db=None):
    db_to_use = target_db or DB_PATH
    print(f"Connecting to database at: {db_to_use}")
    
    # Ensure directory exists if not default
    if target_db:
        os.makedirs(os.path.dirname(target_db), exist_ok=True)

    con = sqlite3.connect(db_to_use)
    cur = con.cursor()

    # Ensure table exists (in case of tmp_db)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS deterministic_rules (
            id TEXT PRIMARY KEY,
            domain TEXT,
            description TEXT,
            condition TEXT,
            verdict TEXT,
            scale TEXT,
            scoring_type TEXT,
            success_weight REAL,
            source_page TEXT
        )
    """)

    rules = [
        # Chapter 19: Health/Diseases
        ("LK_GOSW_CH19_HEALTH_ASTHMA_1", "health", "Sun and Saturn in House 1 -> Respiratory issues/Asthma.",
         json.dumps({
             "type": "AND",
             "conditions": [
                 {"type": "placement", "planet": "Sun", "houses": [1]},
                 {"type": "placement", "planet": "Saturn", "houses": [1]}
             ]
         }),
         "Risk of chronic respiratory issues or breathing difficulties.", "major", "penalty", 0.8, "Chapter 19"),

        ("LK_GOSW_CH19_HEALTH_EYESIGHT_1", "health", "Sun in 4, Saturn in 10 -> Weak eyesight (Blind Chart/Andha Teva).",
         json.dumps({
             "type": "AND",
             "conditions": [
                 {"type": "placement", "planet": "Sun", "houses": [4]},
                 {"type": "placement", "planet": "Saturn", "houses": [10]}
             ]
         }),
         "Eyesight may be weak from birth or deteriorate significantly.", "extreme", "penalty", 0.9, "Chapter 19"),

        ("LK_GOSW_CH19_HEALTH_SKIN_1", "health", "Mercury and Rahu in H6 -> Skin ailments.",
         json.dumps({
             "type": "AND",
             "conditions": [
                 {"type": "placement", "planet": "Mercury", "houses": [6]},
                 {"type": "placement", "planet": "Rahu", "houses": [6]}
             ]
         }),
         "Vulnerability to skin diseases, allergies, or fungal issues.", "moderate", "penalty", 0.75, "Chapter 19"),
         
        ("LK_GOSW_CH19_HEALTH_BONE_1", "health", "Saturn in H1 and Sun in H10 -> Bone/Joint issues.",
         json.dumps({
             "type": "AND",
             "conditions": [
                 {"type": "placement", "planet": "Saturn", "houses": [1]},
                 {"type": "placement", "planet": "Sun", "houses": [10]}
             ]
         }),
         "Structural issues in bones or chronic joint pain.", "moderate", "penalty", 0.75, "Chapter 19")
    ]

    print(f"Inserting {len(rules)} new health rules from Gosvami Chapter 19...")
    
    try:
        cur.executemany('''
            INSERT OR REPLACE INTO deterministic_rules 
            (id, domain, description, condition, verdict, scale, scoring_type, success_weight, source_page)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', rules)
        con.commit()
        print(f"Successfully inserted {cur.rowcount} rules.")
    except Exception as e:
        print(f"Database error: {e}")
        con.rollback()
    finally:
        con.close()

if __name__ == "__main__":
    seed_ch19_health_rules()
