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

# Quick geocode dictionary for public figures
from astroq.lk_prediction.location_provider import GEO_MAP, DEFAULT_GEO

def get_aspects(house_pos: Dict[str, int]) -> List[Dict[str, Any]]:
    """Detects primary Lal Kitab aspects between planets."""
    aspects = []
    planets = list(house_pos.keys())
    
    # Simple aspect map: (Source House -> Target House, Name)
    rules = [
        (1, 7, "Direct (1-7)"),
        (4, 10, "Direct (4-10)"),
        (1, 8, "Takkar (1-8)"),
        (2, 6, "Blocked/Gali (2-6)"),
        (3, 11, "Direct (3-11)"),
        (5, 9, "Direct (5-9)"),
        (6, 12, "Direct (6-12)"),
        (8, 2, "Direct (8-2)"),
    ]
    
    for p1 in planets:
        h1 = house_pos[p1]
        for p2 in planets:
            if p1 == p2: continue
            h2 = house_pos[p2]
            
            for src, tgt, name in rules:
                if h1 == src and h2 == tgt:
                    # Check relationship
                    rel = "Neutral"
                    friends = NATURAL_RELATIONSHIPS.get(p1, {}).get("Friends", [])
                    enemies = NATURAL_RELATIONSHIPS.get(p1, {}).get("Enemies", [])
                    if p2 in friends: rel = "Benefic"
                    elif p2 in enemies: rel = "Malefic"
                    
                    aspects.append({
                        "source": p1, "target": p2, "type": name, "rel": rel
                    })
    return aspects

def _confidence_score(confidence: str) -> int:
    return {"None": 0, "Low": 1, "Medium": 2, "High": 3}.get(confidence, 0)

def analyze_aspect_doubt_correlation():
    print(f"=== Aspect-based Doubt Fuzzer Analysis ===")
    
    generator = ChartGenerator()
    engine = VarshphalTimingEngine()
    fate_view = NatalFateView()
    doubtful_engine = DoubtfulTimingEngine()
    
    config = ModelConfig(os.path.join("backend", "data", "config.db"), 
                         os.path.join("backend", "data", "model_defaults.json"))
    
    data_path = os.path.join("backend", "data", "public_figures_ground_truth.json")
    figures = json.load(open(data_path, "r"))
    
    domain_map = {"career": "career_travel", "legal": "career_travel", "other": "career_travel",
                  "finance": "finance", "health": "health", "marriage": "marriage", "progeny": "progeny"}
    
    aspect_stats = defaultdict(lambda: {"tp": 0, "fn": 0, "fp": 0, "tn": 0})
    
    for fig in figures:
        name = fig["name"]
        dob, tob = fig["dob"], fig["tob"]
        if len(tob.split(":")) == 2: tob += ":00"
        place = fig.get("birth_place", "New Delhi, India")
        lat, lon, tz = GEO_MAP.get(place, (28.6139, 77.2090, "+05:30"))
        
        try:
            payload = generator.build_full_chart_payload(dob, tob, place, lat, lon, tz, "vedic")
        except Exception: continue
        
        natal_chart = payload.get("chart_0")
        if not natal_chart: continue
        
        context_natal = UnifiedAstrologicalContext(natal_chart, natal_chart, config=config)
        active_promises = doubtful_engine._identify_doubtful_natal_promises(context_natal)
        if not active_promises: continue
        
        fate_entries = fate_view.evaluate(natal_chart)
        
        # Analyze by Specific Aspect + Strength
    strength_stats = defaultdict(lambda: {"hits": 0, "misses": 0})
    dignity_engine = DignityEngine(config)
    
    for fig in figures:
        name = fig["name"]
        dob, tob = fig["dob"], fig["tob"]
        if len(tob.split(":")) == 2: tob += ":00"
        place = fig.get("birth_place", "New Delhi, India")
        lat, lon, tz = GEO_MAP.get(place, (28.6139, 77.2090, "+05:30"))
        
        try:
            payload = generator.build_full_chart_payload(dob, tob, place, lat, lon, tz, "vedic")
        except Exception: continue
        
        natal_chart = payload.get("chart_0")
        if not natal_chart: continue
        context_natal = UnifiedAstrologicalContext(natal_chart, natal_chart, config=config)
        active_promises = doubtful_engine._identify_doubtful_natal_promises(context_natal)
        if not active_promises: continue
        
        fate_entries = fate_view.evaluate(natal_chart)
        
        for event in fig.get("events", []):
            age = event.get("age")
            engine_domain = domain_map.get(event.get("domain"), "career_travel")
            annual_chart = None
            for k, v in payload.items():
                if k.startswith("chart_") and v.get("chart_period") == age:
                    annual_chart = v; break
            if not annual_chart: continue
            
            annual_pos = {p: info.get("house") for p, info in annual_chart.get("planets_in_houses", {}).items()}
            annual_aspects = get_aspects(annual_pos)
            
            domain_entry = next((e for e in fate_entries if e["domain"] == engine_domain), None)
            fate_type = domain_entry["fate_type"] if domain_entry else "RASHI_PHAL"
            context = UnifiedAstrologicalContext(annual_chart, natal_chart, config=config)
            result = engine.get_timing_confidence(context, engine_domain, fate_type=fate_type, age=age)
            is_hit = _confidence_score(result["confidence"]) > 1
            
            for asp in annual_aspects:
                # Calculate Strength Score based on Dignity
                src_p, tgt_p = asp["source"], asp["target"]
                src_h = annual_pos[src_p]
                tgt_h = annual_pos[tgt_p]
                
                # We use a simple dignity-based strength: 
                # (1.0 base + multipliers for Pakka Ghar/Exaltation)
                src_mult = dignity_engine.get_annual_dignity_multiplier(src_p, context.get_natal_house(src_p), age)
                tgt_mult = dignity_engine.get_annual_dignity_multiplier(tgt_p, context.get_natal_house(tgt_p), age)
                
                # Average strength
                strength = (src_mult + tgt_mult) / 2.0
                strength_label = "High" if strength > 1.1 else "Low" if strength < 0.9 else "Medium"
                
                key = f"{asp['type']} | {strength_label} Strength"
                if is_hit: strength_stats[key]["hits"] += 1
                else: strength_stats[key]["misses"] += 1

    print("\n" + "="*85)
    print("      ASPECT STRENGTH (DIGNITY-BASED) VS PREDICTIVE ACCURACY")
    print("="*85)
    print(f"{'Aspect Type & Strength Bucket':<45} | {'Hits':>4} | {'Misses':>6} | {'Accuracy':>10}")
    print("-" * 85)
    
    sorted_stats = sorted(strength_stats.items(), key=lambda x: (x[1]["hits"] / (x[1]["hits"] + x[1]["misses"]) if (x[1]["hits"] + x[1]["misses"]) > 0 else 0), reverse=True)
    
    for key, stats in sorted_stats:
        total = stats["hits"] + stats["misses"]
        acc = (stats["hits"] / total * 100) if total > 0 else 0
        if total >= 5:
            print(f"{key:<45} | {stats['hits']:>4} | {stats['misses']:>6} | {acc:>9.1f}%")

if __name__ == "__main__":
    analyze_aspect_doubt_correlation()
