import os
import sys
import json
import logging

sys.path.append(os.path.join(os.getcwd(), "backend"))

from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.pipeline import LKPredictionPipeline
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.rules_engine import RulesEngine

# Quick geocode dictionary for public figures
from astroq.lk_prediction.location_provider import GEO_MAP, DEFAULT_GEO

def run_rules_timing_fuzzer():
    print(f"=== Starting Detailed Rules Timing Fuzzer ===")
    
    cfg = ModelConfig(db_path="backend/data/rules.db", defaults_path="backend/data/model_defaults.json")
    generator = ChartGenerator()
    pipeline = LKPredictionPipeline(cfg)
    rules_engine = RulesEngine(cfg)
    
    # Preload rule mapping for domain check
    rule_map = {r.get("id") or r.get("rule_id"): r for r in rules_engine._rules_cache}
    
    data_path = os.path.join("backend", "data", "public_figures_ground_truth.json")
    with open(data_path, "r") as f:
        figures = json.load(f)
        
    total_events = 0
    confirmed_events = 0
    
    for fig in figures:
        name = fig["name"]
        dob = fig["dob"]
        tob = fig["tob"]
        if len(tob.split(":")) == 2: tob += ":00"
            
        place = fig.get("birth_place", "New Delhi, India")
        lat, lon, tz = GEO_MAP.get(place, (28.6139, 77.2090, "+05:30"))
        
        print(f"\\nAnalyzing {name}...")
        try:
            payload = generator.build_full_chart_payload(
                dob_str=dob, tob_str=tob, place_name=place, 
                latitude=lat, longitude=lon, utc_string=tz, chart_system="vedic"
            )
        except Exception as e:
            print(f"  Error generating payload for {name}: {e}")
            continue
            
        for event in fig.get("events", []):
            age = event.get("age")
            event_domain = event.get("domain", "").lower()
            desc = event.get("description")
            total_events += 1
            
            annual_chart_key = f"chart_{age}"
            if annual_chart_key not in payload:
                found_key = None
                for k, v in payload.items():
                    if k.startswith("chart_") and v.get("chart_type") == "Yearly" and v.get("chart_period") == age:
                        found_key = k
                        break
                if found_key:
                    annual_chart_key = found_key
                else:
                    print(f"  [Age {age}] {desc} - Could not find Annual Chart!")
                    continue
                    
            annual_chart = payload[annual_chart_key]
            
            # 1. Run pipeline on Annual Chart
            annual_preds = pipeline.generate_predictions(annual_chart)
            annual_rule_ids = set()
            for p in annual_preds:
                annual_rule_ids.update(p.source_rules)
                
            if not annual_rule_ids:
                print(f"  [Age {age}] {desc} - No canonical rules matched in Annual Chart.")
                continue
                
            # Filter annual rules that match the event domain (or are major rules)
            # To avoid noise, let's just see if ANY rule double-confirms, but we will print if it matches domain.
            
            # 2. Run pipeline on Monthly Charts
            confirmed = False
            confirming_months = set()
            confirming_rules = set()
            
            for m in range(1, 13):
                m_chart = generator.generate_monthly_chart(annual_chart, m)
                monthly_preds = pipeline.generate_predictions(m_chart)
                monthly_rule_ids = set()
                for p in monthly_preds:
                    monthly_rule_ids.update(p.source_rules)
                    
                overlap = annual_rule_ids.intersection(monthly_rule_ids)
                if overlap:
                    # We have a double confirmation of specific rules!
                    confirmed = True
                    confirming_months.add(m)
                    for rid in overlap:
                        confirming_rules.add(rid)
            
            if confirmed:
                confirmed_events += 1
                months_str = ", ".join(map(str, sorted(confirming_months)))
                
                # Try to see if any confirming rule matches the event domain
                domain_match = False
                matched_rule_desc = ""
                for rid in confirming_rules:
                    if rid in rule_map:
                        r = rule_map[rid]
                        r_domain = r.get("domain", "").lower()
                        if event_domain and r_domain and (event_domain in r_domain or r_domain in event_domain):
                            domain_match = True
                            matched_rule_desc = r.get("description", "")[:60] + "..."
                            break
                            
                status = "✓ DOUBLE CONFIRMED" if not domain_match else f"⭐ DOMAIN-MATCHED DOUBLE CONFIRMATION ({matched_rule_desc})"
                print(f"  [Age {age}] {desc} - {status} in Month(s) {months_str}. Overlapping Rules: {len(confirming_rules)}")
            else:
                print(f"  [Age {age}] {desc} - ✗ {len(annual_rule_ids)} Annual rules matched, but NONE double-confirmed in any month.")

    print("\\n" + "="*50)
    print("      RULE-LEVEL TIMING DOUBLE-CONFIRMATION REPORT")
    print("="*50)
    if total_events > 0:
        rate = (confirmed_events / total_events) * 100
        print(f"Total Life Events Analyzed: {total_events}")
        print(f"Events with at least 1 Rule Double Confirmation: {confirmed_events} ({rate:.1f}%)")

if __name__ == "__main__":
    run_rules_timing_fuzzer()
