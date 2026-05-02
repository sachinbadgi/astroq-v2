import json, os, sys
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), "backend")))
from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.quantum_engine.chart_generator import QuantumChartGenerator

DOMAIN_CONFIG = {
    "career": {"primary": ["Sun", "Saturn"], "support": ["Mars", "Jupiter"], "primary_h": [10], "support_h": [6, 2]},
}
PLANET_UNITS = {"Jupiter": 11, "Saturn": 10.5, "Sun": 10, "Moon": 9, "Mars": 8, "Rahu": 7, "Venus": 6, "Ketu": 6, "Mercury": 3}
PLANET_MATURITY = {"Jupiter": 16, "Sun": 22, "Moon": 24, "Venus": 25, "Mars": 28, "Mercury": 34, "Saturn": 36, "Rahu": 42, "Ketu": 48}
CYCLE_35_YEAR_RANGES = [
    (1,6,"Saturn"),(7,12,"Rahu"),(13,15,"Ketu"),(16,21,"Jupiter"),
    (22,23,"Sun"),(24,24,"Moon"),(25,27,"Venus"),(28,33,"Mars"),(34,35,"Mercury")
]
def get_35_year_ruler(age):
    period = (age - 1) % 35 + 1
    for s,e,p in CYCLE_35_YEAR_RANGES:
        if s<=period<=e: return p
    return None

def get_score(p_data, karaka, age):
    if not p_data: return 0.0
    amp = p_data.get("amplitude", 0)
    if amp <= 0: return 0.0
    score = amp * (PLANET_UNITS.get(karaka,5)/11.0)
    mat = PLANET_MATURITY.get(karaka,0)
    if age < mat: score *= 0.5
    is_ruler = get_35_year_ruler(age) == karaka
    is_dignified = amp >= 2.0
    if is_ruler: score += 1.0
    elif is_dignified: score *= 0.5
    else: score *= 0.05
    return score

figures = json.load(open("backend/data/public_figures_ground_truth.json"))
dhoni = [f for f in figures if f['name'] == 'MS Dhoni'][0]

gen = ChartGenerator()
payload = gen.build_full_chart_payload(
    dob_str=dhoni['dob'], tob_str=dhoni.get('tob','12:00'),
    place_name=dhoni.get('birth_place','New Delhi'),
    latitude=dhoni.get('lat',28.61), longitude=dhoni.get('lon',77.20),
    utc_string=dhoni.get('tz','+05:30'), chart_system="vedic"
)
qgen = QuantumChartGenerator("backend/astroq/quantum_engine/quantum_weights.json")
timeline = qgen.generate_quantum_timeline(payload["chart_0"], max_years=75)

# Dhoni IPL captaincy at age 26 (2008, born 1981)
domain = "career"
config = DOMAIN_CONFIG[domain]
for age in [24,25,26,27,28,30]:
    chart = timeline.get(f"chart_{age}",{})
    planets = chart.get("planets_in_houses",{})
    ruler = get_35_year_ruler(age)
    p_score = 0; s_score = 0; p_hits = 0
    details = []
    for k in config["primary"]:
        pd = planets.get(k); 
        if not pd: continue
        h = pd.get("house",0)
        hw = 1.0 if h in config["primary_h"] else (0.4 if h in config["support_h"] else 0)
        if hw == 0: continue
        s = get_score(pd, k, age) * hw
        p_score += s
        if s >= 0.6: p_hits += 1
        details.append(f"  {k}[H{h},amp={pd.get('amplitude')}] score={s:.3f}")
    for k in config["support"]:
        pd = planets.get(k)
        if not pd: continue
        h = pd.get("house",0)
        hw = 1.0 if h in config["primary_h"] else (0.4 if h in config["support_h"] else 0)
        if hw == 0: continue
        s = get_score(pd, k, age) * hw
        s_score += s
        details.append(f"  {k}[H{h},amp={pd.get('amplitude')}] supp={s:.3f}")
    composite = p_score + s_score*0.5
    triggered = (p_hits>=1) and (composite>=1.2)
    print(f"Age {age} (Ruler={ruler}): primary_hits={p_hits} composite={composite:.3f} -> {'TRIGGER' if triggered else 'dormant'}")
    for d in details: print(d)
