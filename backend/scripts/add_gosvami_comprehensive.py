import sqlite3
import json
import os
import sys

# Connect to rules.db
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'rules.db'))

def seed_comprehensive_gosvami_rules():
    print(f"Connecting to database at: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}. Run migrations first.")
        sys.exit(1)

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    
    rules = []
    
    # ---------------------------------------------------------
    # 1. Travel Rules (From Chapter 16)
    # ---------------------------------------------------------
    travel_rules = [
        (1, "Travel preparation complete but no movement or return within 100 days. ", "penalty", "moderate"),
        (2, "Travel on promotion.", "boost", "major"),
        (3, "Live alone away from friends/relatives.", "penalty", "minor"),
        (4, "No travel or only local to mother. No malefic effects.", "neutral", "minor"),
        (5, "No change of city, only local changes.", "neutral", "minor"),
        (6, "Travel/transfer order cancelled at least once.", "penalty", "moderate"),
        (7, "Change of city and travel is certain. Auspicious.", "boost", "major"),
        (8, "Unpleasant, unwilling and malefic travel.", "penalty", "major"),
        (9, "Auspicious, happiness giving, favourable travel.", "boost", "major"),
        (10, "Painful, causing untimely unacceptable travel.", "penalty", "major"),
        (11, "Order held enroute. Minor movement. Travel 11 times auspicious.", "boost", "moderate"),
        (12, "Time to live with family. Promotion without transfer. Gainful travel.", "boost", "major")
    ]
    
    for house, desc, scoring, scale in travel_rules:
        rules.append((
            f"LK_GOSW_CH16_TRAVEL_KETU_H{house}", 
            "travel", 
            f"Ketu in H{house} -> {desc}",
            json.dumps({"type": "placement", "planet": "Ketu", "houses": [house]}),
            desc, scale, scoring, 0.85, "Page 296"
        ))
        
    # ---------------------------------------------------------
    # 2. Marriage Rules (From Chapter 17)
    # ---------------------------------------------------------
    marriage_rules = [
        ("Venus", 4, "Marriage may take place but is not auspicious/fruitful. Doubtful nature.", "penalty", "major"),
        ("Rahu", 7, "Marriage at the age of 21 is inauspicious and meaningless.", "penalty", "major"),
        ("Rahu", 1, "Marriage at the age of 21 is meaningless.", "penalty", "major"),
        ("Saturn", 6, "Marriage is inauspicious especially if Venus is in H2 or H12.", "penalty", "moderate"),
        ("Sun", 7, "Comfort from spouse is little and one has liaisons outside.", "penalty", "major"),
        ("Jupiter", 1, "If H.No. 7 is blank, early marriage is advisable.", "boost", "moderate"),
        ("Jupiter", 7, "With Sun-Jupiter or Mars-Jupiter, father and spouse do not survive together.", "penalty", "extreme"),
    ]
    
    for planet, house, desc, scoring, scale in marriage_rules:
        rules.append((
            f"LK_GOSW_CH17_MARR_{planet.upper()}_H{house}",
            "marriage",
            f"{planet} in H{house} -> {desc}",
            json.dumps({"type": "placement", "planet": planet, "houses": [house]}),
            desc, scale, scoring, 0.85, "Page 298-302"
        ))

    # Conjunction rules for Marriage
    rules.append((
        "LK_GOSW_CH17_MARR_JUP_VEN_H7", "marriage", "Jupiter-Venus together in H7 -> Issuelessness",
        json.dumps({"type": "AND", "conditions": [
            {"type": "placement", "planet": "Jupiter", "houses": [7]},
            {"type": "placement", "planet": "Venus", "houses": [7]}
        ]}),
        "Keeps one issueless.", "extreme", "penalty", 0.9, "Page 313"
    ))
    
    rules.append((
        "LK_GOSW_CH17_MARR_VEN_KETU_H1", "marriage", "Venus-Ketu in H1 -> Impotent / Childless",
        json.dumps({"type": "AND", "conditions": [
            {"type": "placement", "planet": "Venus", "houses": [1]},
            {"type": "placement", "planet": "Ketu", "houses": [1]}
        ]}),
        "Impotent/deprived of male offspring.", "extreme", "penalty", 0.9, "Page 303"
    ))

    # ---------------------------------------------------------
    # 3. Progeny Rules (From Chapter 17)
    # ---------------------------------------------------------
    progeny_rules = [
        ("Ketu", 11, "Gives male child.", "boost", "major"),
        ("Moon", 6, "All daughters.", "neutral", "moderate"),
        ("Ketu", 4, "All sons.", "boost", "major"),
        ("Saturn", 5, "Only one son till age 48.", "neutral", "moderate"),
        ("Saturn", 7, "At least 7 sons (if Rahu not in 11).", "boost", "extreme"),
        ("Rahu", 9, "Only one son will survive between age 21 and 42.", "penalty", "major"),
        ("Rahu", 5, "Extremely malefic for child birth (without Sun/Moon support).", "penalty", "extreme"),
        ("Mars", 4, "Obstruction of child birth.", "penalty", "major"),
        ("Sun", 12, "Will not make a person issueless.", "boost", "minor")
    ]
    
    for planet, house, desc, scoring, scale in progeny_rules:
        rules.append((
            f"LK_GOSW_CH17_PROG_{planet.upper()}_H{house}",
            "progeny",
            f"{planet} in H{house} -> {desc}",
            json.dumps({"type": "placement", "planet": planet, "houses": [house]}),
            desc, scale, scoring, 0.85, "Page 308-313"
        ))

    # Complex Progeny Obstructions
    rules.append((
        "LK_GOSW_CH17_PROG_SUN_H6_MARS_H10", "progeny", "Sun H6, Mars H10 -> Loss of sons",
        json.dumps({"type": "AND", "conditions": [
            {"type": "placement", "planet": "Sun", "houses": [6]},
            {"type": "placement", "planet": "Mars", "houses": [10]}
        ]}),
        "Loss of sons one after another.", "extreme", "penalty", 0.9, "Page 313"
    ))

    # ---------------------------------------------------------
    # 4. Wealth / Profession Rules (Chapter 16/18)
    # ---------------------------------------------------------
    profession_placements = [
        ("Sun", 10, "Govt, Accounts, Books"),
        ("Jupiter", 10, "Iron, House, Buffalo"),
        ("Saturn", 10, "Sea animals, Machinery, Building"),
        ("Moon", 10, "Ancestral Property"),
        ("Venus", 10, "Earth and cotton, Items of night comforts"),
        ("Ketu", 10, "Foundation of houses, Trading in dogs")
    ]

    for planet, house, desc in profession_placements:
        rules.append((
            f"LK_GOSW_CH16_PROF_{planet.upper()}_H{house}",
            "profession",
            f"{planet} in H{house} -> {desc}",
            json.dumps({"type": "placement", "planet": planet, "houses": [house]}),
            f"Profession / Fortune related to: {desc}.", "major", "boost", 0.8, "Page 280-281"
        ))

    # Wealth Units
    wealth_conjunctions = [
        ("Jupiter", "Moon", "Hidden wealth", 20),
        ("Jupiter", "Venus", "False showy wealth", 17),
        ("Jupiter", "Mars", "Honest family wealth", 18),
        ("Jupiter", "Saturn", "Wealth of an Ascetic", 21),
        ("Sun", "Moon", "Super employment", 19),
        ("Sun", "Mars", "Landlord", 17),
        ("Moon", "Mars", "Noble wealth", 16),
        ("Mars", "Saturn", "Machinery/Technical wealth", 18),
        ("Sun", "Mercury", "Royal advisor", 13),
        ("Mercury", "Venus", "Luxury wealth", 9)
    ]

    for p1, p2, desc, units in wealth_conjunctions:
        # Just creating one generic rule per conjunction (regardless of house) by searching generic houses 1-12
        rules.append((
            f"LK_GOSW_CH18_WEALTH_{p1.upper()}_{p2.upper()}",
            "wealth",
            f"{p1}-{p2} together -> {desc} ({units} units)",
            json.dumps({"type": "AND", "conditions": [
                # In rules engine, an aspect check could be used, or we just rely on presence in same house loosely
                {"type": "OR", "conditions": [
                     {"type": "AND", "conditions": [{"type": "placement", "planet": p1, "houses": [h]}, {"type": "placement", "planet": p2, "houses": [h]}]}
                     for h in range(1, 13)
                ]}
            ]}),
            f"{desc}, yielding {units} base income units.", "extreme" if units > 18 else "major", "boost", 0.8, "Page 314"
        ))
        
    # Combine and save
    print(f"Total compiled comprehensive rules: {len(rules)}")
    
    try:
        cur.executemany('''
            INSERT OR REPLACE INTO deterministic_rules 
            (id, domain, description, condition, verdict, scale, scoring_type, success_weight, source_page)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', rules)
        con.commit()
        print(f"Successfully inserted {cur.rowcount} rules into database.")
    except Exception as e:
        print(f"Database error: {e}")
        con.rollback()
    finally:
        con.close()

if __name__ == "__main__":
    seed_comprehensive_gosvami_rules()
