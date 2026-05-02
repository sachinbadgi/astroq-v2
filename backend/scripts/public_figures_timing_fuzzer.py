import os
import sys
import json
from datetime import datetime

sys.path.append(os.path.join(os.getcwd(), "backend"))

from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.varshphal_timing_engine import VarshphalTimingEngine
from astroq.lk_prediction.astrological_context import UnifiedAstrologicalContext
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.natal_fate_view import NatalFateView

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
    "Skopje, North Macedonia": (42.0003, 21.4280, "+01:00")
}

def _confidence_score(confidence: str) -> int:
    return {"None": 0, "Low": 1, "Medium": 2, "High": 3}.get(confidence, 0)

def run_public_figures_timing_fuzzer():
    print(f"=== Starting Public Figures Timing Fuzzer (Graha Phal - Strict Boolean) ===")
    
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
        
    total_events = 0
    confirmed_events = 0
    
    total_noise_years = 0
    noise_hits = 0
    
    domain_map = {
        "career":   "career_travel",
        "legal":    "career_travel",
        "other":    "career_travel",
        "finance":  "finance",
        "health":   "health",
        "marriage": "marriage",
        "progeny":  "progeny",
    }
    
    for fig in figures:
        name = fig["name"]
        dob = fig["dob"]
        tob = fig["tob"]
        if len(tob.split(":")) == 2:
            tob = tob + ":00" # pad seconds if missing
            
        place = fig.get("birth_place", "New Delhi, India")
        lat, lon, tz = GEO_MAP.get(place, (28.6139, 77.2090, "+05:30"))
        
        print(f"\nAnalyzing {name}...")
        
        try:
            payload = generator.build_full_chart_payload(
                dob_str=dob, tob_str=tob, place_name=place, 
                latitude=lat, longitude=lon, utc_string=tz, chart_system="vedic"
            )
        except Exception as e:
            print(f"  Error generating payload for {name}: {e}")
            continue
            
        natal_chart = payload.get("chart_0")
        if not natal_chart:
            print(f"  Could not find Natal Chart!")
            continue
            
        # Pre-calculate Natal Fate View for the figure
        fate_entries = fate_view.evaluate(natal_chart)
            
        for event in fig.get("events", []):
            age = event.get("age")
            year = event.get("year")
            desc = event.get("description")
            domain = event.get("domain", "career_travel")
            engine_domain = domain_map.get(domain, "career_travel")
            
            total_events += 1
            
            # Helper to find annual chart by age
            def get_annual(target_age):
                for k, v in payload.items():
                    if k.startswith("chart_") and v.get("chart_type") == "Yearly" and v.get("chart_period") == target_age:
                        return v
                return None

            annual_chart = get_annual(age)
            if not annual_chart:
                print(f"  [Event Age {age}] {desc} - Could not find Annual Chart!")
                continue
                
            # Find fate type for this domain
            domain_entry = next((e for e in fate_entries if e["domain"] == engine_domain), None)
            fate_type = domain_entry["fate_type"] if domain_entry else "RASHI_PHAL"

            # Evaluate event year
            context = UnifiedAstrologicalContext(chart=annual_chart, natal_chart=natal_chart, config=config)
            result = engine.get_timing_confidence(context, engine_domain, fate_type=fate_type, age=age)
            score = _confidence_score(result["confidence"])
            
            # Boolean logic: Medium (2) or High (3) is a hit. Low (1) or None (0) is a miss.
            is_hit = score > 1
            
            if is_hit:
                confirmed_events += 1
                triggers = " | ".join(result.get("triggers", []))
                print(f"  [Age {age}] {desc} - ✓ HIT: {triggers}")
            else:
                print(f"  [Age {age}] {desc} - ✗ MISS: No exact double confirmation triggered.")
                
            # Evaluate noise years (True Negative Rate testing)
            NOISE_WINDOW = 5
            for n_age in range(max(1, age - NOISE_WINDOW), age + NOISE_WINDOW + 1):
                if n_age == age: continue
                n_chart = get_annual(n_age)
                if n_chart:
                    total_noise_years += 1
                    n_context = UnifiedAstrologicalContext(chart=n_chart, natal_chart=natal_chart, config=config)
                    n_res = engine.get_timing_confidence(n_context, engine_domain, fate_type=fate_type, age=n_age)
                    if _confidence_score(n_res["confidence"]) > 1:
                        noise_hits += 1

    print("\n" + "="*50)
    print("      PUBLIC FIGURES DOUBLE-CONFIRMATION REPORT")
    print("      (Strict Boolean Graha Phal Logic)")
    print("="*50)
    if total_events > 0:
        hit_rate = (confirmed_events / total_events) * 100
        print(f"Total Life Events Analyzed: {total_events}")
        print(f"Absolute Hits (Janam + Varshphal Lock): {confirmed_events} ({hit_rate:.1f}%)")
        
    if total_noise_years > 0:
        fpr = (noise_hits / total_noise_years) * 100
        tnr = 100 - fpr
        print(f"\nTotal Noise Years Analyzed: {total_noise_years}")
        print(f"False Positives: {noise_hits} ({fpr:.1f}%)")
        print(f"True Negative Rate (Silence Metric): {tnr:.1f}%")

if __name__ == "__main__":
    run_public_figures_timing_fuzzer()
