import os
import sys
import json

sys.path.append(os.path.join(os.getcwd(), "backend"))
from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.pipeline import LKPredictionPipeline
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.rules_engine import RulesEngine

from astroq.lk_prediction.location_provider import GEO_MAP, DEFAULT_GEO

def run_natal_annual_fuzzer():
    print("=== Starting Natal-to-Annual Promise Fuzzer (All Figures) ===")
    
    covered = 0        # any natal overlap (broad Graha Phal coverage)
    domain_matched = 0  # overlap that also matches the event's domain
    unique_hit = 0      # highly specific rules (fires <= 5 times in a lifetime)
    missed  = 0
    
    cfg = ModelConfig(db_path="backend/data/rules.db", defaults_path="backend/data/model_defaults.json")
    generator = ChartGenerator()
    pipeline = LKPredictionPipeline(cfg)
    rules_engine = RulesEngine(cfg)
    rule_map = {r.get("id") or r.get("rule_id"): r for r in rules_engine._rules_cache}
    
    data_path = os.path.join("backend", "data", "public_figures_ground_truth.json")
    with open(data_path, "r") as f: figures = json.load(f)
        
    for fig in figures:  # All figures
        name = fig["name"]
        dob = fig["dob"]
        tob = fig["tob"]
        if len(tob.split(":")) == 2: tob += ":00"
        place = fig.get("birth_place", "New Delhi, India")
        lat, lon, tz = GEO_MAP.get(place, (28.6139, 77.2090, "+05:30"))
        
        print(f"\nAnalyzing {name}...")
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
                missed += 1
                print(f"  [Age {age}] {desc} - \u2717 No Natal Promise overlap found in this year.")
                continue
                
            # This event has some Graha Phal coverage at the broad level
            covered += 1
                
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
                unique_hit += 1
                print(f"  [Age {age}] {desc} - \u2713 HIGHLY UNIQUE TIMING FOUND!")
                for rid, rdesc, rdom, years in standout_rules:
                    domain_flag = "\u2b50 DOMAIN MATCH" if (event_domain in rdom or rdom in event_domain) else ""
                    print(f"      Rule: {rdesc[:80]}...")
                    print(f"      Fired in years: {years} {domain_flag}")
            else:
                # Check for domain match among common rules
                has_domain_match = any(
                    event_domain in rule_map.get(rid, {}).get("domain", "").lower() or
                    rule_map.get(rid, {}).get("domain", "").lower() in event_domain
                    for rid in promise_overlap
                )
                if has_domain_match:
                    domain_matched += 1
                    print(f"  [Age {age}] {desc} - \u2713 DOMAIN MATCH (common rule)")
                else:
                    print(f"  [Age {age}] {desc} - \u2717 Overlaps found but non-specific, no domain match.")

    # Summary
    total = covered + missed
    print("\n" + "="*60)
    print("  GRAHA PHAL COVERAGE REPORT (Natal Promise Overlap)")
    print("="*60)
    print(f"  Total Events Analyzed:         {total}")
    print(f"  Broad Graha Phal Coverage:     {covered} ({covered/total*100:.1f}%)  [any natal rule fires in event year]")
    print(f"  Domain-Matched Coverage:       {domain_matched} ({domain_matched/total*100:.1f}%)  [rule domain matches event domain]")
    print(f"  Highly Unique Timing:          {unique_hit} ({unique_hit/total*100:.1f}%)  [rule fires <=5 times in lifetime]")
    print(f"  Not Covered (Silent):          {missed}  ({missed/total*100:.1f}%)")

if __name__ == "__main__":
    run_natal_annual_fuzzer()
