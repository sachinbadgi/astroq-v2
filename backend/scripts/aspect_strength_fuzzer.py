import os
import sys
import json
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Any, Optional

sys.path.append(os.path.join(os.getcwd(), "backend"))

from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.varshphal_timing_engine import VarshphalTimingEngine
from astroq.lk_prediction.astrological_context import UnifiedAstrologicalContext
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.natal_fate_view import NatalFateView
from astroq.lk_prediction.doubtful_timing_engine import DoubtfulTimingEngine
from astroq.lk_prediction.lk_constants import NATURAL_RELATIONSHIPS
from astroq.lk_prediction.dignity_engine import DignityEngine

# Quick geocode dictionary for public figures
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
    "Skopje, North Macedonia": (42.0003, 21.4280, "+01:00"),
    "Ranchi, India": (23.3441, 85.3096, "+05:30")
}

def get_aspects(house_pos: Dict[str, int]) -> List[Dict[str, Any]]:
    aspects = []
    planets = list(house_pos.keys())
    rules = [
        (1, 7, "Direct (1-7)"), (4, 10, "Direct (4-10)"), (1, 8, "Takkar (1-8)"),
        (2, 6, "Blocked/Gali (2-6)"), (3, 11, "Direct (3-11)"), (5, 9, "Direct (5-9)"),
        (6, 12, "Direct (6-12)"), (8, 2, "Direct (8-2)"),
    ]
    for p1 in planets:
        h1 = house_pos[p1]
        for p2 in planets:
            if p1 == p2: continue
            h2 = house_pos[p2]
            for src, tgt, name in rules:
                if h1 == src and h2 == tgt:
                    aspects.append({"source": p1, "target": p2, "type": name})
    return aspects

def _confidence_score(confidence: str) -> int:
    return {"None": 0, "Low": 1, "Medium": 2, "High": 3}.get(confidence, 0)

def analyze_fate_role_strength_correlation():
    print(f"=== Natal Fate + Role + Strength Multi-Dimensional Analysis ===")
    generator = ChartGenerator()
    engine = VarshphalTimingEngine()
    fate_view = NatalFateView()
    doubtful_engine = DoubtfulTimingEngine()
    config = ModelConfig(os.path.join("backend", "data", "config.db"), os.path.join("backend", "data", "model_defaults.json"))
    dignity_engine = DignityEngine(config)
    
    data_path = os.path.join("backend", "data", "public_figures_ground_truth.json")
    figures = json.load(open(data_path, "r"))
    
    domain_map = {"career": "career_travel", "legal": "career_travel", "other": "career_travel", "finance": "finance", "health": "health", "marriage": "marriage", "progeny": "progeny"}
    
    stats = defaultdict(lambda: {"tp": 0, "fn": 0, "fp": 0, "tn": 0})
    
    for fig in figures:
        name = fig["name"]; dob = fig["dob"]; tob = fig["tob"]
        if len(tob.split(":")) == 2: tob += ":00"
        place = fig.get("birth_place", "New Delhi, India")
        lat, lon, tz = GEO_MAP.get(place, (28.6139, 77.2090, "+05:30"))
        
        try:
            payload = generator.build_full_chart_payload(dob, tob, place, lat, lon, tz, "vedic")
        except Exception: continue
        
        natal_chart = payload.get("chart_0")
        if not natal_chart: continue
        context_natal = UnifiedAstrologicalContext(natal_chart, natal_chart, config=config)
        
        # 1. Identify Natal Fate Context per Domain
        fate_entries = fate_view.evaluate(natal_chart)
        doubtful_promises = doubtful_engine._identify_doubtful_natal_promises(context_natal)
        
        # Events
        event_ages = []
        for event in fig.get("events", []):
            age = event.get("age"); event_ages.append(age)
            engine_domain = domain_map.get(event.get("domain"), "career_travel")
            annual_chart = next((v for k,v in payload.items() if k.startswith("chart_") and v.get("chart_period")==age), None)
            if not annual_chart: continue
            
            # Determine Natal Fate for this domain
            domain_entry = next((e for e in fate_entries if e["domain"] == engine_domain), None)
            fate_type = domain_entry["fate_type"] if domain_entry else "RASHI_PHAL"
            
            # Is this specific domain "Doubtful"?
            is_doubtful = any(p["domain"] == engine_domain for p in doubtful_promises)
            fate_context = "DOUBTFUL" if is_doubtful else ("FIXED (GP)" if fate_type == "GRAHA_PHAL" else "CONDITIONAL (RP)")
            
            annual_pos = {p: info.get("house") for p, info in annual_chart.get("planets_in_houses", {}).items()}
            aspects = get_aspects(annual_pos)
            
            context = UnifiedAstrologicalContext(annual_chart, natal_chart, config=config)
            is_hit = _confidence_score(engine.get_timing_confidence(context, engine_domain, fate_type=fate_type, age=age)["confidence"]) > 1
            
            for asp in aspects:
                tgt_p = asp["target"]
                tgt_mult = dignity_engine.get_annual_dignity_multiplier(tgt_p, context.get_natal_house(tgt_p), age)
                s_tgt = "High" if tgt_mult > 1.1 else "Low" if tgt_mult < 0.9 else "Medium"
                
                # We focus on the TARGET planet (the anvil) and the Natal Fate context
                key = f"{asp['type']} | {fate_context} | Target: {s_tgt}"
                
                if is_hit: stats[key]["tp"] += 1
                else: stats[key]["fn"] += 1

        # Noise
        noise_sampled = 0
        for n_age in range(15, 65):
            if n_age in event_ages or noise_sampled >= 15: continue
            n_chart = next((v for k,v in payload.items() if k.startswith("chart_") and v.get("chart_period")==n_age), None)
            if not n_chart: continue
            
            n_pos = {p: info.get("house") for p, info in n_chart.get("planets_in_houses", {}).items()}
            n_aspects = get_aspects(n_pos)
            
            for d_name in ["career_travel", "marriage"]:
                domain_entry = next((e for e in fate_entries if e["domain"] == d_name), None)
                fate_type = domain_entry["fate_type"] if domain_entry else "RASHI_PHAL"
                is_doubtful = any(p["domain"] == d_name for p in doubtful_promises)
                fate_context = "DOUBTFUL" if is_doubtful else ("FIXED (GP)" if fate_type == "GRAHA_PHAL" else "CONDITIONAL (RP)")
                
                context = UnifiedAstrologicalContext(n_chart, natal_chart, config=config)
                is_fp = _confidence_score(engine.get_timing_confidence(context, d_name, age=n_age)["confidence"]) > 1
                for asp in n_aspects:
                    tgt_mult = dignity_engine.get_annual_dignity_multiplier(asp["target"], context.get_natal_house(asp["target"]), n_age)
                    s_tgt = "High" if tgt_mult > 1.1 else "Low" if tgt_mult < 0.9 else "Medium"
                    
                    key = f"{asp['type']} | {fate_context} | Target: {s_tgt}"
                    if is_fp: stats[key]["fp"] += 1
                    else: stats[key]["tn"] += 1
            noise_sampled += 1

    print("\n" + "="*125)
    print("      NATAL FATE TYPE VS ASPECT TARGET STRENGTH (PRECISION ANALYSIS)")
    print("="*125)
    print(f"{'Aspect | Natal Fate | Target Strength':<55} | {'TP':>4} | {'FN':>4} | {'FP':>4} | {'TN':>4} | {'Hit Rate':>10} | {'Silence':>10}")
    print("-" * 125)
    sorted_keys = sorted(stats.keys())
    for k in sorted_keys:
        s = stats[k]
        tp, fn, fp, tn = s["tp"], s["fn"], s["fp"], s["tn"]
        acc = (tp / (tp + fn) * 100) if (tp + fn) > 0 else 0
        tnr = (tn / (tn + fp) * 100) if (tn + fp) > 0 else 0
        if tp + fn >= 5:
            print(f"{k:<55} | {tp:>4} | {fn:>4} | {fp:>4} | {tn:>4} | {acc:>9.1f}% | {tnr:>9.1f}%")

if __name__ == "__main__":
    analyze_fate_role_strength_correlation()
