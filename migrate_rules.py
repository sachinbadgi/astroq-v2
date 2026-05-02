import sqlite3
import os
import re

def is_living_hit(text: str) -> bool:
    """Check if the text implies a biological/living entity affliction."""
    text = text.lower()
    bio_keywords = [
        "eyeball", "nose", "teeth", "stomach", "heart", "skull", "tongue",
        "relative", "son", "mother", "father", "brother", "sister", "wife", "nephew",
        "disease", "asthma", "epilepsy", "baldness", "sick", "body", "health",
        "death", "child", "progeny", "eye", "pregnancy", "blind", "uncle", "aunt", "maternal", "paternal"
    ]
    for k in bio_keywords:
        if re.search(r'\b' + k + r'\b', text):
            return True
    return False

def migrate_rules_db():
    default_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), 'backend', 'data'))
    db_path = os.path.join(default_dir, "rules.db")
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    con = sqlite3.connect(db_path)
    cur = con.cursor()

    # Check if column exists
    cur.execute("PRAGMA table_info(deterministic_rules)")
    columns = [col[1] for col in cur.fetchall()]
    if "afflicts_living" not in columns:
        cur.execute("ALTER TABLE deterministic_rules ADD COLUMN afflicts_living BOOLEAN DEFAULT 0")
        print("Added column 'afflicts_living'.")

    # Fetch and update rules
    cur.execute("SELECT id, description, verdict FROM deterministic_rules")
    rows = cur.fetchall()
    
    update_count = 0
    for row in rows:
        rid, desc, verdict = row
        if is_living_hit(desc) or is_living_hit(verdict):
            cur.execute("UPDATE deterministic_rules SET afflicts_living = 1 WHERE id = ?", (rid,))
            update_count += 1

    con.commit()
    con.close()
    print(f"Migration complete. Updated {update_count} out of {len(rows)} rules to afflicts_living=1.")

if __name__ == "__main__":
    migrate_rules_db()
