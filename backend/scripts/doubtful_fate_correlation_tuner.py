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
from astroq.lk_prediction.doubtful_timing_engine import DoubtfulTimingEngine

# Quick geocode dictionary for public figures
from astroq.lk_prediction.location_provider import GEO_MAP, DEFAULT_GEO

def _confidence_score(confidence: str) -> int:
    return {"None": 0, "Low": 1, "Medium": 2, "High": 3}.get(confidence, 0)

def analyze_doubtful_fate_correlation():
    print(f"=== Doubtful Fate Correlation Analysis ===")
    
    generator = ChartGenerator()
    engine = VarshphalTimingEngine()
    fate_view = NatalFateView()
    doubtful_engine = DoubtfulTimingEngine()
    
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
        except Exception:
            continue
            
        natal_chart = payload.get("chart_0")
        if not natal_chart:
            continue
            
        context_natal = UnifiedAstrologicalContext(chart=natal_chart, natal_chart=natal_chart, config=config)
        
        # Identify Doubtful Promises
        doubtful_promises = doubtful_engine._identify_doubtful_natal_promises(context_natal)
        doubtful_count = len(doubtful_promises)
        
        # Pre-calculate Natal Fate View
        fate_entries = fate_view.evaluate(natal_chart)
        
        total_events = 0
        hits = 0
        
        for event in fig.get("events", []):
            age = event.get("age")
            domain = event.get("domain", "career_travel")
            engine_domain = domain_map.get(domain, "career_travel")
            
            def get_annual(target_age):
                for k, v in payload.items():
                    if k.startswith("chart_") and v.get("chart_type") == "Yearly" and v.get("chart_period") == target_age:
                        return v
                return None

            annual_chart = get_annual(age)
            if not annual_chart:
                continue
                
            # Find fate type
            domain_entry = next((e for e in fate_entries if e["domain"] == engine_domain), None)
            fate_type = domain_entry["fate_type"] if domain_entry else "RASHI_PHAL"

            total_events += 1
            context = UnifiedAstrologicalContext(chart=annual_chart, natal_chart=natal_chart, config=config)
            result = engine.get_timing_confidence(context, engine_domain, fate_type=fate_type, age=age)
            if _confidence_score(result["confidence"]) > 1:
                hits += 1
        
        accuracy = (hits / total_events * 100) if total_events > 0 else 0
        
        person_metrics.append({
            "name": name,
            "doubtful_count": doubtful_count,
            "promises": [p["name"] for p in doubtful_promises],
            "accuracy": accuracy,
            "total_events": total_events
        })
        
    # Analyze by Specific Promise Name
    promise_stats = defaultdict(lambda: {"tp": 0, "fn": 0, "fp": 0, "tn": 0})
    
    for fig in figures:
        name = fig["name"]
        dob = fig["dob"]
        tob = fig["tob"]
        if len(tob.split(":")) == 2: tob = tob + ":00"
        place = fig.get("birth_place", "New Delhi, India")
        lat, lon, tz = GEO_MAP.get(place, (28.6139, 77.2090, "+05:30"))
        
        try:
            payload = generator.build_full_chart_payload(
                dob_str=dob, tob_str=tob, place_name=place, 
                latitude=lat, longitude=lon, utc_string=tz, chart_system="vedic"
            )
        except Exception: continue
        
        natal_chart = payload.get("chart_0")
        if not natal_chart: continue
        
        context_natal = UnifiedAstrologicalContext(chart=natal_chart, natal_chart=natal_chart, config=config)
        active_promises = doubtful_engine._identify_doubtful_natal_promises(context_natal)
        fate_entries = fate_view.evaluate(natal_chart)
        
        for promise in active_promises:
            p_name = promise["name"]
            p_domain = promise["domain"]
            
            # 1. Analyze Events (TP/FN)
            for event in fig.get("events", []):
                age = event.get("age")
                engine_domain = domain_map.get(event.get("domain"), "career_travel")
                if engine_domain != p_domain: continue
                
                annual_chart = None
                for k, v in payload.items():
                    if k.startswith("chart_") and v.get("chart_type") == "Yearly" and v.get("chart_period") == age:
                        annual_chart = v; break
                if not annual_chart: continue
                
                domain_entry = next((e for e in fate_entries if e["domain"] == engine_domain), None)
                fate_type = domain_entry["fate_type"] if domain_entry else "RASHI_PHAL"
                context = UnifiedAstrologicalContext(chart=annual_chart, natal_chart=natal_chart, config=config)
                result = engine.get_timing_confidence(context, engine_domain, fate_type=fate_type, age=age)
                
                if _confidence_score(result["confidence"]) > 1:
                    promise_stats[p_name]["tp"] += 1
                else:
                    promise_stats[p_name]["fn"] += 1

            # 2. Analyze Noise (FP/TN) - Random sample of 15 noise years
            event_ages = [e.get("age") for e in fig.get("events", [])]
            noise_sampled = 0
            for n_age in range(15, 65):
                if n_age in event_ages or noise_sampled >= 15: continue
                
                n_chart = None
                for k, v in payload.items():
                    if k.startswith("chart_") and v.get("chart_type") == "Yearly" and v.get("chart_period") == n_age:
                        n_chart = v; break
                if not n_chart: continue
                
                domain_entry = next((e for e in fate_entries if e["domain"] == p_domain), None)
                fate_type = domain_entry["fate_type"] if domain_entry else "RASHI_PHAL"
                n_context = UnifiedAstrologicalContext(chart=n_chart, natal_chart=natal_chart, config=config)
                n_res = engine.get_timing_confidence(n_context, p_domain, fate_type=fate_type, age=n_age)
                
                noise_sampled += 1
                if _confidence_score(n_res["confidence"]) > 1:
                    promise_stats[p_name]["fp"] += 1
                else:
                    promise_stats[p_name]["tn"] += 1

    print("\n" + "="*110)
    print("      GRANULAR CONFUSION MATRIX: DOUBTFUL PROMISE (PLANET/HOUSE) VS PERFORMANCE")
    print("="*110)
    print(f"{'Doubtful Promise / Configuration':<45} | {'TP':>4} | {'FN':>4} | {'FP':>4} | {'TN':>4} | {'Hit Rate':>10} | {'Silence':>10}")
    print("-" * 110)
    
    sorted_promises = sorted(promise_stats.items(), key=lambda x: (x[1]["tp"] / (x[1]["tp"] + x[1]["fn"]) if (x[1]["tp"] + x[1]["fn"]) > 0 else 0), reverse=True)
    
    for p_name, stats in sorted_promises:
        tp, fn, fp, tn = stats["tp"], stats["fn"], stats["fp"], stats["tn"]
        acc = (tp / (tp + fn) * 100) if (tp + fn) > 0 else 0
        tnr = (tn / (tn + fp) * 100) if (tn + fp) > 0 else 0
        if tp + fn > 0:
            print(f"{p_name[:45]:<45} | {tp:>4} | {fn:>4} | {fp:>4} | {tn:>4} | {acc:>9.1f}% | {tnr:>9.1f}%")
        
    print("\n" + "="*60)
    print("      HIGH DOUBTFUL FATE INDIVIDUALS (MOST PROMISES)")
    print("="*60)
    for m in sorted(person_metrics, key=lambda x: x["doubtful_count"], reverse=True)[:10]:
        promises_str = ", ".join(m["promises"])[:50]
        print(f"{m['name']:<25} | Promises: {m['doubtful_count']} | Acc: {m['accuracy']:>4.1f}% | {promises_str}")

if __name__ == "__main__":
    analyze_doubtful_fate_correlation()
