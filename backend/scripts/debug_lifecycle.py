import sys
import os
sys.path.append(os.path.join(os.getcwd(), "backend"))

from astroq.lk_prediction.lifecycle_engine import LifecycleEngine
from astroq.lk_prediction.chart_generator import ChartGenerator

def debug_lifecycle():
    # Steve Jobs
    dob = "1955-02-24"
    tob = "19:15:00"
    place = "San Francisco, California, US"
    lat, lon, tz = (37.7749, -122.4194, "-08:00")
    
    gen = ChartGenerator()
    payload = gen.build_full_chart_payload(dob, tob, place, lat, lon, tz, "vedic")
    natal_chart = payload["chart_0"]
    
    natal_positions = {
        p: info.get("house")
        for p, info in natal_chart.get("planets_in_houses", {}).items()
        if info.get("house")
    }
    
    engine = LifecycleEngine()
    history = engine.run_75yr_analysis(natal_positions)
    
    print(f"Lifecycle Analysis for {dob}")
    for age in range(1, 40):
        ledger = history[age]
        net = sum(ledger.get_leakage_multiplier(p) for p in ledger.planets) / 9.0
        burst = [p for p, s in ledger.planets.items() if s.is_burst]
        trauma = sum(s.trauma_points for s in ledger.planets.values())
        print(f"Age {age:2}: Net {net:.2f}, Trauma {trauma:4.1f}, Burst: {burst}")

if __name__ == "__main__":
    debug_lifecycle()
