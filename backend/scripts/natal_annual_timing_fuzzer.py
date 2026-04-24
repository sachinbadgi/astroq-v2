import os
import sys
import json

sys.path.append(os.path.join(os.getcwd(), "backend"))
from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.pipeline import LKPredictionPipeline
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.rules_engine import RulesEngine

GEO_MAP = {
    "Allahabad, India": (25.4358, 81.8463, "+05:30"),
    "Mumbai, India": (19.0760, 72.8777, "+05:30"),
    "Vadnagar, India": (23.7801, 72.6373, "+05:30"),
    "San Francisco, California, US": (37.7749, -122.4194, "-08:00"),
    "Seattle, Washington, US": (47.6062, -122.3321, "-08:00"),
    "Sandringham, Norfolk, UK": (52.8311, 0.5054, "+00:00"),
    "New Delhi, India": (28.6139, 77.2090, "+05:30"),
    "Gary, Indiana, US": (41.5934, -87.3464, "-06:00"),
    "Pretoria, South Africa": (-25.7479, 28.2293, "+02:00"),
    "Porbandar, India": (21.6417, 69.6293, "+05:30"),
    "Raisen, India": (23.3308, 77.7788, "+05:30"),
    "Madanapalle, India": (13.5562, 78.5020, "+05:30"),
    "Indore, India": (22.7196, 75.8577, "+05:30"),
    "Jamshedpur, India": (22.8046, 86.2029, "+05:30"),
    "Jamaica Hospital, Queens, New York, US": (40.7028, -73.8152, "-05:00"),
    "Honolulu, Hawaii, US": (21.3069, -157.8583, "-10:00"),
    "Scranton, Pennsylvania, US": (41.4090, -75.6624, "-05:00"),
    "Mayfair, London, UK": (51.5100, -0.1458, "+00:00"),
    "Buckingham Palace, London, UK": (51.5014, -0.1419, "+00:00"),
    "Skopje, North Macedonia": (42.0003, 21.4280, "+01:00")
}

def run_natal_annual_fuzzer():
    print("=== Starting Natal-to-Annual Promise Fuzzer ===")
    
    cfg = ModelConfig(db_path="backend/data/rules.db", defaults_path="backend/data/model_defaults.json")
    generator = ChartGenerator()
    pipeline = LKPredictionPipeline(cfg)
    rules_engine = RulesEngine(cfg)
    rule_map = {r.get("id") or r.get("rule_id"): r for r in rules_engine._rules_cache}
    
    data_path = os.path.join("backend", "data", "public_figures_ground_truth.json")
    with open(data_path, "r") as f: figures = json.load(f)
        
    for fig in figures[:5]:  # Limit to first 5 figures to keep output readable and fast
        name = fig["name"]
        dob = fig["dob"]
        tob = fig["tob"]
        if len(tob.split(":")) == 2: tob += ":00"
        place = fig.get("birth_place", "New Delhi, India")
        lat, lon, tz = GEO_MAP.get(place, (28.6139, 77.2090, "+05:30"))
        
        print(f"\\nAnalyzing {name} (Lifetime 1-80 years)...")
        try:
            # We must generate charts up to age 80 to check uniqueness
            payload = generator.build_full_chart_payload(
                dob_str=dob, tob_str=tob, place_name=place, 
                latitude=lat, longitude=lon, utc_string=tz, chart_system="vedic"
            )
        except Exception as e:
            continue
            
        natal_chart = payload.get("chart_0")
        if not natal_chart: continue
        
        natal_preds = pipeline.generate_predictions(natal_chart)
        natal_rules = set()
        for p in natal_preds: natal_rules.update(p.source_rules)
        
        # Pre-calculate rules for all 80 years to allow fast uniqueness checking
        annual_rules_by_year = {}
        for y in range(1, 81):
            y_chart_key = f"chart_{y}"
            if y_chart_key in payload:
                y_preds = pipeline.generate_predictions(payload[y_chart_key])
                y_rules = set()
                for p in y_preds: y_rules.update(p.source_rules)
                annual_rules_by_year[y] = y_rules
                
        for event in fig.get("events", []):
            age = event.get("age")
            if not age or age > 80 or age not in annual_rules_by_year: continue
            
            desc = event.get("description")
            event_domain = event.get("domain", "").lower()
            
            event_rules = annual_rules_by_year[age]
            
            # The "Promise": Rules that fired in NATAL and fired AGAIN in EVENT YEAR
            promise_overlap = natal_rules.intersection(event_rules)
            
            if not promise_overlap:
                print(f"  [Age {age}] {desc} - ✗ No Natal Promise overlap found in this year.")
                continue
                
            # Now, for each overlapped rule, how many OTHER years in the person's life did it fire?
            standout_rules = []
            
            for rid in promise_overlap:
                rule = rule_map.get(rid, {})
                rule_desc = rule.get("description", "")
                r_domain = rule.get("domain", "").lower()
                
                # Check how many years this rule fired
                years_fired = []
                for y, y_rules in annual_rules_by_year.items():
                    if rid in y_rules:
                        years_fired.append(y)
                        
                # We are looking for highly specific triggers (e.g. only happens < 5 times in a lifetime)
                if len(years_fired) <= 5:
                    standout_rules.append((rid, rule_desc, r_domain, years_fired))
                    
            if standout_rules:
                print(f"  [Age {age}] {desc} - ✓ HIGHLY UNIQUE TIMING FOUND!")
                for rid, rdesc, rdom, years in standout_rules:
                    domain_flag = "⭐ DOMAIN MATCH" if (event_domain in rdom or rdom in event_domain) else ""
                    print(f"      Rule: {rdesc[:80]}...")
                    print(f"      Fired in years: {years} {domain_flag}")
            else:
                print(f"  [Age {age}] {desc} - ✗ Overlaps found, but they are common (fire 6+ times in lifetime, no standout uniqueness).")

if __name__ == "__main__":
    run_natal_annual_fuzzer()
