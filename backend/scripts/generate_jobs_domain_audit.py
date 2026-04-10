import sys
import os
import sqlite3
import json

# Ensure backend is in path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.pipeline import LKPredictionPipeline

# All possible domains for disaggregation
ALL_DOMAINS = [
    "Health", "Wealth", "Career", "Marriage", "Progeny", 
    "Family", "Education", "Travel", "Spirituality", "Luck", 
    "Mother", "Father", "Siblings", "Children", "Status",
    "Business", "Communication", "Intelligence", "Longevity",
    "Accidents", "Obstacles", "Sudden Events", "Expenses", "Losses"
]

def generate_domain_audit():
    db_path = "backend/data/astroq_gt.db"
    defaults_path = "backend/data/model_defaults.json"
    audit_db_path = "/tmp/jobs_domain_audit.db"
    
    if os.path.exists(audit_db_path):
        try:
            os.remove(audit_db_path)
        except PermissionError:
            print(f"Warning: Could not remove {audit_db_path}, appending instead.")
        
    audit_conn = sqlite3.connect(audit_db_path)
    audit_cur = audit_conn.cursor()
    
    # Create tables
    audit_cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_domain_scores (
            age INTEGER,
            domain TEXT,
            max_score REAL,
            contributing_planets TEXT
        )
    """)
    audit_cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_rules_flat (
            age INTEGER,
            domain TEXT,
            rule_description TEXT
        )
    """)
    
    config = ModelConfig(db_path=db_path, defaults_path=defaults_path)
    generator = ChartGenerator()
    pipeline = LKPredictionPipeline(config)
    
    # 1. Birth Data for Steve Jobs
    person_dob = "1955-02-24"
    person_tob = "19:15"
    person_place = "San Francisco, California"
    person_lat = 37.7749
    person_lon = -122.4194
    person_tz = "-08:00"
    
    # 2. Generate Chart Payload
    print("Generating charts...")
    natal_chart = generator.generate_chart(
        dob_str=person_dob,
        tob_str=person_tob,
        place_name=person_place,
        latitude=person_lat,
        longitude=person_lon,
        utc_string=person_tz
    )
    annual_charts = generator.generate_annual_charts(natal_chart, max_years=75)
    
    # 4. Phase 1: Natal Promise Baseline (Identity Collection)
    print("Collecting Natal Promise Baseline (Age 0) Identity...")
    pipeline.load_natal_baseline(natal_chart)
    natal_predictions = pipeline.generate_predictions(natal_chart)
    
    # Track the "Birth Identity" of every rule hit to identify what is a constant trait
    birth_signatures = set()
    birth_hits = pipeline.rules_engine.evaluate_chart(natal_chart)
    for h in birth_hits:
        # Signature: (Rule ID + Target Planets + Target Houses)
        sig = (h.rule_id, tuple(sorted(h.primary_target_planets)), tuple(sorted(h.target_houses)))
        birth_signatures.add(sig)
    
    # Store Natal Promise Audit (Age 0)
    for p in natal_predictions:
        for d in p.domain.split("/"):
            audit_cur.execute(
                "INSERT INTO audit_domain_scores (age, domain, max_score, contributing_planets) VALUES (?, ?, ?, ?)",
                (0, d.strip(), p.magnitude, ",".join(p.source_planets))
            )
            for r in p.source_rules:
                audit_cur.execute(
                    "INSERT INTO audit_rules_flat (age, domain, rule_description) VALUES (?, ?, ?)",
                    (0, d.strip(), r)
                )

    # 5. Phase 2: Annual Timing (1 to 75) - PLACEMENT ONLY
    print("Aggregating Placement-Only Timing for years 1 to 75...")
    # Satisfy pipeline's internal baseline requirement with a neutral one
    pipeline._natal_baseline = {
        p: {"strength": 0.0, "house": 0, "strength_total": 0.0, "strength_breakdown": {}}
        for p in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
    }
    
    import math
    for age in range(1, 76):
        if age % 10 == 0: print(f"  Age {age}...")
        chart = annual_charts[f"chart_{age}"]
        
        # 1. Get raw rule hits for this year
        annual_hits = pipeline.rules_engine.evaluate_chart(chart)
        
        # 2. Filter out anything that matches the Birth Signature
        timing_hits = []
        for h in annual_hits:
            sig = (h.rule_id, tuple(sorted(h.primary_target_planets)), tuple(sorted(h.target_houses)))
            if sig not in birth_signatures:
                timing_hits.append(h)
        
        if not timing_hits:
            continue
            
        # 3. Group hits by Planet/House to create Enriched Events
        planet_hits = {}
        for h in timing_hits:
            # Use first primary planet or "General"
            p_name = h.primary_target_planets[0] if h.primary_target_planets else "General"
            h_num = h.target_houses[0] if h.target_houses else 0
            key = (p_name, h_num)
            if key not in planet_hits:
                planet_hits[key] = {
                    "planet": p_name, "house": h_num, "rule_hits": [], 
                    "annual_magnitude": 0.0, "final_probability": 0.0
                }
            planet_hits[key]["rule_hits"].append(h)
            planet_hits[key]["annual_magnitude"] += h.magnitude

        # 4. Convert grouped hits into Classifiable events
        raw_events = []
        for key, data in planet_hits.items():
            # Calculate a pure annual probability (1/(1+e^-k*mag))
            mag = data["annual_magnitude"]
            data["final_probability"] = 1.0 / (1.0 + math.exp(-1.2 * mag))
            raw_events.append(data)
            
        classified = pipeline.classifier.classify_events(raw_events, age=age)
        
        domain_peaks = {}
        for p in classified:
            for d in p.domains:
                if d not in domain_peaks:
                    domain_peaks[d] = {"max_score": 0.0, "planets": set(), "rules": []}
                
                if abs(p.magnitude) > abs(domain_peaks[d]["max_score"]):
                    domain_peaks[d]["max_score"] = p.magnitude
                
                domain_peaks[d]["planets"].add(p.planet)
                domain_peaks[d]["rules"].extend(p.contributing_rules)

        for d, data in domain_peaks.items():
            audit_cur.execute(
                "INSERT INTO audit_domain_scores (age, domain, max_score, contributing_planets) VALUES (?, ?, ?, ?)",
                (age, d, data["max_score"], ",".join(list(data["planets"])))
            )
            for r in set(data["rules"]):
                audit_cur.execute(
                    "INSERT INTO audit_rules_flat (age, domain, rule_description) VALUES (?, ?, ?)",
                    (age, d, r)
                )
    
    audit_conn.commit()
    audit_conn.close()
    print(f"Domain Audit Complete. Database: {audit_db_path}")

if __name__ == "__main__":
    generate_domain_audit()
