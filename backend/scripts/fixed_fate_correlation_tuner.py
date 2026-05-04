import os
import sys
import json
from datetime import datetime
from collections import defaultdict

sys.path.append(os.path.join(os.getcwd(), "backend"))

from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.varshphal_timing_engine import VarshphalTimingEngine
from astroq.lk_prediction.astrological_context import UnifiedAstrologicalContext
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.natal_fate_view import NatalFateView

# Quick geocode dictionary for public figures
from astroq.lk_prediction.location_provider import GEO_MAP, DEFAULT_GEO

def _confidence_score(confidence: str) -> int:
    return {"None": 0, "Low": 1, "Medium": 2, "High": 3}.get(confidence, 0)

def analyze_fixed_fate_correlation():
    print(f"=== Fixed Fate Correlation Analysis ===")
    
    generator = ChartGenerator()
    engine = VarshphalTimingEngine()
    fate_view = NatalFateView()
    
    # Load configuration
    db_path = os.path.join("backend", "data", "config.db")
    defaults_path = os.path.join("backend", "data", "model_defaults.json")
    config = ModelConfig(db_path, defaults_path)
    
    data_path = os.path.join("backend", "data", "public_figures_ground_truth.json")
    
    with open(data_path, "r") as f:
        figures = json.load(f)
        
    domain_map = {
        "career":   "career_travel",
        "legal":    "career_travel",
        "other":    "career_travel",
        "finance":  "finance",
        "health":   "health",
        "marriage": "marriage",
        "progeny":  "progeny",
    }
    
    # Metrics per person
    person_metrics = []
    
    for fig in figures:
        name = fig["name"]
        dob = fig["dob"]
        tob = fig["tob"]
        if len(tob.split(":")) == 2:
            tob = tob + ":00"
            
        place = fig.get("birth_place", "New Delhi, India")
        lat, lon, tz = GEO_MAP.get(place, (28.6139, 77.2090, "+05:30"))
        
        try:
            payload = generator.build_full_chart_payload(
                dob_str=dob, tob_str=tob, place_name=place, 
                latitude=lat, longitude=lon, utc_string=tz, chart_system="vedic"
            )
        except Exception as e:
            continue
            
        natal_chart = payload.get("chart_0")
        if not natal_chart:
            continue
            
        # Calculate Fixed Fate %
        fate_entries = fate_view.evaluate(natal_chart)
        total_active_domains = sum(1 for e in fate_entries if e["fate_type"] != "NEITHER")
        fixed_domains = sum(1 for e in fate_entries if e["fate_type"] == "GRAHA_PHAL")
        hybrid_domains = sum(1 for e in fate_entries if e["fate_type"] == "HYBRID")
        
        fixed_fate_perc = (fixed_domains / total_active_domains * 100) if total_active_domains > 0 else 0
        structural_certainty = ((fixed_domains + 0.5 * hybrid_domains) / total_active_domains * 100) if total_active_domains > 0 else 0
        
        total_events = 0
        hits = 0
        
        for event in fig.get("events", []):
            age = event.get("age")
            domain = event.get("domain", "career_travel")
            engine_domain = domain_map.get(domain, "career_travel")
            
            # Helper to find annual chart by age
            def get_annual(target_age):
                for k, v in payload.items():
                    if k.startswith("chart_") and v.get("chart_type") == "Yearly" and v.get("chart_period") == target_age:
                        return v
                return None

            # Find fate type for this domain
            domain_entry = next((e for e in fate_entries if e["domain"] == engine_domain), None)
            fate_type = domain_entry["fate_type"] if domain_entry else "RASHI_PHAL"

            annual_chart = get_annual(age)
            if not annual_chart:
                continue
                
            total_events += 1
            context = UnifiedAstrologicalContext(chart=annual_chart, natal_chart=natal_chart, config=config)
            result = engine.get_timing_confidence(context, engine_domain, fate_type=fate_type, age=age)
            if _confidence_score(result["confidence"]) > 1:
                hits += 1
        
        accuracy = (hits / total_events * 100) if total_events > 0 else 0
        
        person_metrics.append({
            "name": name,
            "fixed_fate_perc": fixed_fate_perc,
            "structural_certainty": structural_certainty,
            "accuracy": accuracy,
            "total_events": total_events
        })
        
    # Sort and group into buckets
    buckets = defaultdict(list)
    for m in person_metrics:
        # Group by 10% buckets of structural certainty
        bucket_key = int(m["structural_certainty"] // 10) * 10
        buckets[bucket_key].append(m["accuracy"])
        
    print("\n" + "="*60)
    print("      CORRELATION: STRUCTURAL CERTAINTY VS ACCURACY")
    print("="*60)
    print(f"{'Certainty Bucket':<20} | {'Avg Accuracy':<15} | {'Sample Size':<12}")
    print("-" * 60)
    
    for bucket in sorted(buckets.keys()):
        accs = buckets[bucket]
        avg_acc = sum(accs) / len(accs)
        print(f"{bucket}% - {bucket+9}%{' ':<10} | {avg_acc:>12.1f}% | {len(accs):>12}")
        
    print("\n" + "="*60)
    print("      INDIVIDUAL TOP PERFORMERS (HIGHEST CERTAINTY)")
    print("="*60)
    for m in sorted(person_metrics, key=lambda x: x["structural_certainty"], reverse=True)[:10]:
        print(f"{m['name']:<25} | Certainty: {m['structural_certainty']:>4.1f}% | Accuracy: {m['accuracy']:>4.1f}%")

if __name__ == "__main__":
    analyze_fixed_fate_correlation()
