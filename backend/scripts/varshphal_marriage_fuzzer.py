import os
import sys
import json

sys.path.append(os.path.join(os.getcwd(), "backend"))
from astroq.lk_prediction.chart_generator import ChartGenerator

from astroq.lk_prediction.location_provider import GEO_MAP, DEFAULT_GEO

def check_marriage_rules(natal_pos, annual_pos):
    """
    Checks the 8 B.M. Goswami Varshphal Marriage rules.
    Returns a list of matched rule IDs.
    """
    matches = []
    
    # Extract positions
    n_ven = natal_pos.get("Venus")
    n_mer = natal_pos.get("Mercury")
    n_sun = natal_pos.get("Sun")
    n_mon = natal_pos.get("Moon")
    n_rah = natal_pos.get("Rahu")
    
    a_ven = annual_pos.get("Venus")
    a_mer = annual_pos.get("Mercury")
    a_sat = annual_pos.get("Saturn")
    a_sun = annual_pos.get("Sun")
    a_mon = annual_pos.get("Moon")
    a_rah = annual_pos.get("Rahu")
    a_jup = annual_pos.get("Jupiter")
    
    # Rule 1: Venus/Mercury in 1,2,10,11,12 AND Saturn in 1, 10
    if (a_ven in [1,2,10,11,12] or a_mer in [1,2,10,11,12]) and a_sat in [1, 10]:
        matches.append("Rule 1 (Ven/Mer in 1,2,10,11,12 + Sat in 1,10)")
        
    # Rule 2: Natal Ven/Mer in 7, no enemies in 3,11, Annual Ven/Mer in 7
    if n_ven == 7 or n_mer == 7:
        if not any(x in [3, 11] for x in [n_sun, n_mon, n_rah]):
            if a_ven == 7 or a_mer == 7:
                matches.append("Rule 2 (Natal Ven/Mer H7 returns to H7)")
                
    # Rule 3: Mercury-Venus conjoined in Annual, Saturn in 2,7,12
    if a_ven == a_mer and a_sat in [2, 7, 12]:
        matches.append("Rule 3 (Annual Ven-Mer conjoined + Sat in 2,7,12)")
        
    # Rule 4: Saturn in H1
    if a_sat == 1:
        matches.append("Rule 4 (Annual Saturn in H1)")
        
    # Rule 5: Venus/Mercury in same house as Natal, no enemies in 2,7
    if a_ven == n_ven or a_mer == n_mer:
        if not any(x in [2, 7] for x in [a_sun, a_mon, a_rah]):
            matches.append("Rule 5 (Ven/Mer returned to Natal House + No Enemies in 2,7)")
            
    # Rule 6: Natal H2, H7 blank -> Annual Jup/Ven comes to 2,7
    natal_houses_occupied = list(natal_pos.values())
    if 2 not in natal_houses_occupied and 7 not in natal_houses_occupied:
        if a_jup in [2, 7] or a_ven in [2, 7]:
            matches.append("Rule 6 (Natal H2/H7 blank + Annual Jup/Ven in 2,7)")
            
    # Rule 8: Annual Venus or Mercury in 2 or 7
    if a_ven in [2, 7] or a_mer in [2, 7]:
        matches.append("Rule 8 (Annual Ven/Mer in H2 or H7)")
        
    return matches

def run_fuzzer():
    print("=== Varshphal Marriage Timing Triggers Explorer ===")
    generator = ChartGenerator()
    data_path = os.path.join("backend", "data", "public_figures_ground_truth.json")
    with open(data_path, "r") as f: figures = json.load(f)
        
    for fig in figures:
        name = fig["name"]
        marriage_events = [e for e in fig.get("events", []) if e.get("domain", "") == "marriage"]
        if not marriage_events: continue
            
        dob = fig["dob"]
        tob = fig["tob"]
        if len(tob.split(":")) == 2: tob += ":00"
        place = fig.get("birth_place", "New Delhi, India")
        lat, lon, tz = GEO_MAP.get(place, (28.6139, 77.2090, "+05:30"))
        
        try:
            payload = generator.build_full_chart_payload(
                dob_str=dob, tob_str=tob, place_name=place, 
                latitude=lat, longitude=lon, utc_string=tz, chart_system="vedic"
            )
        except Exception as e:
            continue
            
        natal = payload.get("chart_0")
        if not natal: continue
        natal_pos = {p: d["house"] for p, d in natal["planets_in_houses"].items() if p != "Lagna"}
        
        for event in marriage_events:
            age = event.get("age")
            if not age: continue
            
            print(f"\\n--- {name} | MARRIAGE AT AGE {age} ---")
            
            for test_age in range(age - 2, age + 3):
                chart_key = f"chart_{test_age}"
                if chart_key not in payload: continue
                    
                chart = payload[chart_key]
                annual_pos = {p: d["house"] for p, d in chart["planets_in_houses"].items() if p != "Lagna"}
                
                matches = check_marriage_rules(natal_pos, annual_pos)
                
                marker = "⭐ EVENT YEAR ⭐" if test_age == age else "               "
                if matches:
                    print(f"  {marker} Age {test_age} | Triggers Fired: {len(matches)}")
                    for m in matches:
                        print(f"       -> {m}")
                else:
                    print(f"  {marker} Age {test_age} | No Varshphal triggers.")

if __name__ == "__main__":
    run_fuzzer()
