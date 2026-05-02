"""Debug marriage domain scoring for multiple figures."""
import json, os, sys
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), "backend")))
from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.quantum_engine.chart_generator import QuantumChartGenerator

PLANET_UNITS = {"Jupiter": 11, "Saturn": 10.5, "Sun": 10, "Moon": 9, "Mars": 8, "Rahu": 7, "Venus": 6, "Ketu": 6, "Mercury": 3}
PLANET_MATURITY = {"Jupiter": 16, "Sun": 22, "Moon": 24, "Venus": 25, "Mars": 28, "Mercury": 34, "Saturn": 36, "Rahu": 42, "Ketu": 48}
CYCLE_35 = [(1,6,"Saturn"),(7,12,"Rahu"),(13,15,"Ketu"),(16,21,"Jupiter"),(22,23,"Sun"),(24,24,"Moon"),(25,27,"Venus"),(28,33,"Mars"),(34,35,"Mercury")]

def ruler(age):
    period = (age - 1) % 35 + 1
    for s,e,p in CYCLE_35:
        if s<=period<=e: return p
    return None

def planet_score(p_data, karaka, age):
    if not p_data: return 0.0
    amp = p_data.get("amplitude", 0)
    if amp <= 0: return 0.0
    score = amp * (PLANET_UNITS.get(karaka,5)/11.0)
    if age < PLANET_MATURITY.get(karaka,0): score *= 0.5
    is_rul = ruler(age) == karaka
    is_dig = amp >= 2.2
    if is_rul: score += 1.0
    elif is_dig: score *= 0.7
    else: score *= 0.05
    return score

figures = json.load(open("backend/data/public_figures_ground_truth.json"))
base_gen = ChartGenerator()
q_gen = QuantumChartGenerator("backend/astroq/quantum_engine/quantum_weights.json")

# Focus on marriage events
marriage_figs = [f for f in figures if any(e.get('domain','')=='marriage' for e in f.get('events',[]))]

for fig in marriage_figs[:5]:
    ev = next((e for e in fig.get('events',[]) if e.get('domain')=='marriage'), None)
    if not ev: continue
    actual_age = ev.get('age')
    print(f"\n{'='*60}")
    print(f"FIGURE: {fig['name']} | Marriage age: {actual_age}")
    
    payload = base_gen.build_full_chart_payload(
        dob_str=fig['dob'], tob_str=fig.get('tob','12:00'),
        place_name=fig.get('birth_place','New Delhi'),
        latitude=fig.get('lat',28.61), longitude=fig.get('lon',77.20),
        utc_string=fig.get('tz','+05:30'), chart_system="vedic"
    )
    natal = payload['chart_0']
    
    # Print natal Venus and Mercury
    for p in ['Venus', 'Mercury']:
        pd = natal['planets_in_houses'].get(p,{})
        print(f"  NATAL {p}: house={pd.get('house')}, states={pd.get('states')}")
    
    timeline = q_gen.generate_quantum_timeline(natal, max_years=75)
    
    # Check scores at actual marriage age and nearby
    print(f"\n  Scores at ages near marriage ({actual_age}):")
    print(f"  {'age':>4} {'ruler':>8} {'Venus_amp':>10} {'Venus_score':>12} {'Merc_amp':>10} {'Merc_score':>11} {'composite':>10} {'best':>6}")
    for age in range(max(1, actual_age-3), min(76, actual_age+4)):
        chart = timeline.get(f"chart_{age}", {})
        planets = chart.get("planets_in_houses", {})
        rul = ruler(age)
        
        comp = 0; best = 0
        row = {}
        for k in ['Venus', 'Mercury']:
            pd = planets.get(k)
            h = pd.get('house',0) if pd else 0
            amp = pd.get('amplitude',0) if pd else 0
            # house weight: H7=1.0, H2=0.5
            hw = 1.0 if h==7 else (0.5 if h==2 else 0)
            s = planet_score(pd, k, age) * hw if hw > 0 else 0
            comp += s
            if s > best: best = s
            row[k] = (amp, h, s)
        
        trigger = "TRIGGER" if best >= 0.5 and comp >= 0.9 else ""
        print(f"  {age:>4} {rul:>8} {row['Venus'][0]:>10.2f} {row['Venus'][2]:>12.3f} {row['Mercury'][0]:>10.2f} {row['Mercury'][2]:>11.3f} {comp:>10.3f} {best:>6.3f} {trigger}")
