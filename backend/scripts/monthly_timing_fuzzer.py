import random
import datetime
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.lk_constants import PLANET_PAKKA_GHAR, PLANET_EXALTATION, PLANET_DEBILITATION

def get_random_dob():
    start_date = datetime.date(1940, 1, 1)
    end_date = datetime.date(2025, 12, 31)
    time_between = end_date - start_date
    days_between = time_between.days
    random_days = random.randrange(days_between)
    random_date = start_date + datetime.timedelta(days=random_days)
    return random_date.strftime("%Y-%m-%d")

def get_random_tob():
    h = random.randint(0, 23)
    m = random.randint(0, 59)
    return f"{h:02d}:{m:02d}"

def is_doubtful_placement(planet, ppos):
    if planet == "Venus" and ppos.get("Venus") == 4: return True
    if planet == "Sun" and ppos.get("Sun") == 4 and ppos.get("Saturn") == 10: return True
    if planet == "Saturn" and ppos.get("Saturn") == 10 and ppos.get("Sun") == 4: return True
    return False

def check_states(ppos):
    states = []
    for planet, house in ppos.items():
        if house == PLANET_PAKKA_GHAR.get(planet): states.append((planet, "Pakka Ghar"))
        if house in PLANET_EXALTATION.get(planet, []): states.append((planet, "Exalted"))
        if house in PLANET_DEBILITATION.get(planet, []): states.append((planet, "Debilitated"))
        if is_doubtful_placement(planet, ppos): states.append((planet, "Doubtful"))
    return states

def run_monthly_timing_fuzzer(iterations=500):
    print(f"=== Starting Monthly Timing Validation Fuzzer ({iterations} iterations) ===")
    
    generator = ChartGenerator()
    
    stats = {
        "annual_pakka": 0, "monthly_double_pakka": 0,
        "annual_exalted": 0, "monthly_double_exalted": 0,
        "annual_debilitated": 0, "monthly_double_debilitated": 0,
        "annual_doubtful": 0, "monthly_double_doubtful": 0,
    }
    
    for i in range(1, iterations + 1):
        dob = get_random_dob()
        tob = get_random_tob()
        
        # Build payload
        payload = generator.build_full_chart_payload(
            dob_str=dob, tob_str=tob, place_name="New Delhi", 
            latitude=28.6139, longitude=77.2090, utc_string="+05:30", chart_system="vedic"
        )
        
        # Grab a random annual chart
        annual_keys = [k for k in payload.keys() if k.startswith("chart_") and k != "chart_0" and payload[k].get("chart_type") == "Yearly"]
        if not annual_keys: continue
        
        annual_chart_key = random.choice(annual_keys)
        annual_chart = payload[annual_chart_key]
        
        # States in Annual
        ppos_annual = {p: d["house"] for p, d in annual_chart["planets_in_houses"].items() if p != "Lagna"}
        annual_states = check_states(ppos_annual)
        
        # Generate the 12 monthly charts for this annual chart
        monthly_charts = []
        for m in range(1, 13):
            m_chart = generator.generate_monthly_chart(annual_chart, m)
            monthly_charts.append({p: d["house"] for p, d in m_chart["planets_in_houses"].items() if p != "Lagna"})
            
        # For each state found in Annual, check if it appears in ANY monthly chart
        for planet, state_type in annual_states:
            if state_type == "Pakka Ghar":
                stats["annual_pakka"] += 1
                if any(state_type in [st for pl, st in check_states(mc) if pl == planet] for mc in monthly_charts):
                    stats["monthly_double_pakka"] += 1
            elif state_type == "Exalted":
                stats["annual_exalted"] += 1
                if any(state_type in [st for pl, st in check_states(mc) if pl == planet] for mc in monthly_charts):
                    stats["monthly_double_exalted"] += 1
            elif state_type == "Debilitated":
                stats["annual_debilitated"] += 1
                if any(state_type in [st for pl, st in check_states(mc) if pl == planet] for mc in monthly_charts):
                    stats["monthly_double_debilitated"] += 1
            elif state_type == "Doubtful":
                stats["annual_doubtful"] += 1
                if any(state_type in [st for pl, st in check_states(mc) if pl == planet] for mc in monthly_charts):
                    stats["monthly_double_doubtful"] += 1

    print("\n" + "="*50)
    print("      MONTHLY TIMING DOUBLE-CONFIRMATION REPORT")
    print("="*50)
    
    if stats['annual_pakka'] > 0:
        rate = (stats['monthly_double_pakka'] / stats['annual_pakka']) * 100
        print(f"Pakka Ghar Annual Hits: {stats['annual_pakka']}")
        print(f"-> Repeated in at least one Monthly Chart: {stats['monthly_double_pakka']} ({rate:.1f}%)")
        
    if stats['annual_exalted'] > 0:
        rate = (stats['monthly_double_exalted'] / stats['annual_exalted']) * 100
        print(f"Exalted Annual Hits: {stats['annual_exalted']}")
        print(f"-> Repeated in at least one Monthly Chart: {stats['monthly_double_exalted']} ({rate:.1f}%)")
        
    if stats['annual_debilitated'] > 0:
        rate = (stats['monthly_double_debilitated'] / stats['annual_debilitated']) * 100
        print(f"Debilitated Annual Hits: {stats['annual_debilitated']}")
        print(f"-> Repeated in at least one Monthly Chart: {stats['monthly_double_debilitated']} ({rate:.1f}%)")
        
    if stats['annual_doubtful'] > 0:
        rate = (stats['monthly_double_doubtful'] / stats['annual_doubtful']) * 100
        print(f"Doubtful Annual Hits: {stats['annual_doubtful']}")
        print(f"-> Repeated in at least one Monthly Chart: {stats['monthly_double_doubtful']} ({rate:.1f}%)")

if __name__ == "__main__":
    run_monthly_timing_fuzzer(iterations=250)
