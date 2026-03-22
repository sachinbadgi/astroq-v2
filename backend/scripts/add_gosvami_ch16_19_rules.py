import sqlite3
import json
import os
import sys

# Connect to rules.db
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'rules.db'))

def seed_gosvami_rules():
    print(f"Connecting to database at: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}. Run migrations first.")
        sys.exit(1)

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    rules = [
        # Chapter 16: Travel
        ("LK_GOSW_P296_KETU_H7_TRAVEL", "travel", "Ketu in H7 -> Auspicious travel and change of city.",
         json.dumps({"type": "placement", "planet": "Ketu", "houses": [7]}),
         "Auspicious travel and change of city is certain.", "major", "boost", 0.85, "Page 296"),
         
        ("LK_GOSW_P296_KETU_H8_TRAVEL", "travel", "Ketu in H8 -> Unpleasant travel.",
         json.dumps({"type": "placement", "planet": "Ketu", "houses": [8]}),
         "Unpleasant, unwilling and malefic travel.", "major", "penalty", 0.8, "Page 296"),

        # Chapter 16: Profession
        ("LK_GOSW_P280_SUN_H10_PROF", "profession", "Sun in H10 -> Works with Accounts/Govt.",
         json.dumps({"type": "placement", "planet": "Sun", "houses": [10]}),
         "Affairs of state, government, or accounts.", "major", "boost", 0.8, "Page 280"),

        ("LK_GOSW_P280_JUP_H2_PROF", "profession", "Jupiter in H2 -> Law/Sermons.",
         json.dumps({"type": "placement", "planet": "Jupiter", "houses": [2]}),
         "Soil based work beneficial, legal/sermons.", "moderate", "boost", 0.7, "Page 280"),

        # Chapter 17: Marriage
        ("LK_GOSW_P298_VEN_H4_MARR", "marriage", "Venus in H4 -> Delayed/Doubtful marriage.",
         json.dumps({"type": "placement", "planet": "Venus", "houses": [4]}),
         "Marriage may be delayed or doubtful without remedies.", "moderate", "penalty", 0.85, "Page 298"),

        ("LK_GOSW_P299_SUN_JUP_H7_MARR", "marriage", "Sun-Jupiter in H7 -> Father and spouse clash.",
         json.dumps({"type": "AND", "conditions": [
             {"type": "placement", "planet": "Sun", "houses": [7]},
             {"type": "placement", "planet": "Jupiter", "houses": [7]}
         ]}),
         "Father and spouse do not survive together.", "extreme", "penalty", 0.9, "Page 299"),

        # Chapter 17: Progeny
        ("LK_GOSW_P308_KETU_H11_PROG", "progeny", "Ketu in H11 -> Male child.",
         json.dumps({"type": "placement", "planet": "Ketu", "houses": [11]}),
         "Highly auspicious for male offspring.", "major", "boost", 0.9, "Page 308"),

        ("LK_GOSW_P313_RAHU_KETU_SAT_H5_PROG", "progeny", "Rahu/Ketu/Saturn in H5 -> Obstruction to child birth.",
         json.dumps({"type": "OR", "conditions": [
             {"type": "placement", "planet": "Rahu", "houses": [5]},
             {"type": "placement", "planet": "Ketu", "houses": [5]},
             {"type": "placement", "planet": "Saturn", "houses": [5]}
         ]}),
         "Obstruction in child birth or delay.", "major", "penalty", 0.85, "Page 313"),

        # Chapter 18: Money Matters (Wealth)
        ("LK_GOSW_P314_JUP_SUN_WEALTH", "wealth", "Jupiter-Sun together -> Super-royal income.",
         json.dumps({"type": "AND", "conditions": [
             {"type": "placement", "planet": "Sun", "houses": [1,2,3,4,5,6,7,8,9,10,11,12]},
             {"type": "placement", "planet": "Jupiter", "houses": [1,2,3,4,5,6,7,8,9,10,11,12]},
             {"type": "conjunction", "planet_a": "Sun", "planet_b": "Jupiter"} # Custom conjunction check could be used, but since we map to same house:
         ]}), # Assuming rules_engine evaluates AND conditions for same house as conjunction if we don't know the exact house
         "Super-royal income, yielding 21 base units multiplied by earning years.", "extreme", "boost", 0.9, "Page 314")
    ]
    
    # We will insert these by iterating through houses 1 to 12 for the conjunction to make it work with placement
    # Or rely on dynamic evaluation. Better: add a simpler rule for Wealth
    wealth_rules = []
    for h in range(1, 13):
        wealth_rules.append(
            (f"LK_GOSW_P314_JUP_SUN_H{h}_WEALTH", "wealth", f"Jupiter-Sun in H{h} -> Super-royal income",
             json.dumps({"type": "AND", "conditions": [
                 {"type": "placement", "planet": "Sun", "houses": [h]},
                 {"type": "placement", "planet": "Jupiter", "houses": [h]}
             ]}),
             "Super-royal income, yielding 21 base units multiplied by earning years.", "extreme", "boost", 0.9, "Page 314")
        )

    rules.pop() # remove the last complex generic one
    rules.extend(wealth_rules)

    print(f"Inserting {len(rules)} new deterministic rules from Gosvami Chapters 16-19...")
    
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
    seed_gosvami_rules()
