"""
Auto-tuner: finds the best (best_single, composite) thresholds
to maximize timing accuracy while keeping average array length low.
"""
import json, os, sys
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), "backend")))
from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.quantum_engine.chart_generator import QuantumChartGenerator

DOMAIN_CONFIG = {
    "marriage":     {"karakas": ["Venus", "Mercury"],                                 "primary_h": [7],         "support_h": [2]},
    "career":       {"karakas": ["Sun", "Mars", "Saturn", "Jupiter"],                 "primary_h": [10],        "support_h": [6, 2]},
    "career_travel":{"karakas": ["Sun", "Mars", "Saturn", "Rahu", "Jupiter", "Ketu"], "primary_h": [10],        "support_h": [6, 2, 12, 9]},
    "health":       {"karakas": ["Sun", "Mars", "Saturn"],                            "primary_h": [1, 6],      "support_h": [8]},
    "progeny":      {"karakas": ["Jupiter", "Ketu"],                                  "primary_h": [5],         "support_h": []},
    "real_estate":  {"karakas": ["Moon", "Mars", "Saturn"],                           "primary_h": [4],         "support_h": [8]},
    "finance":      {"karakas": ["Jupiter", "Venus", "Mercury"],                      "primary_h": [2, 11],     "support_h": [9]},
}
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
    is_dig = amp >= 2.0
    if is_rul: score += 1.0
    elif is_dig: score *= 0.7
    else: score *= 0.05
    return score

def evaluate(timelines, figures_events, thresh_single, thresh_composite):
    hits = 0; total = 0; arr_len = 0
    for (timeline, natal_q), events in zip(timelines, figures_events):
        for ev in events:
            domain = ev.get("domain","").lower()
            actual_age = ev.get("age")
            cfg = DOMAIN_CONFIG.get(domain)
            if not cfg: continue
            total += 1
            primary_h = cfg["primary_h"]; support_h = cfg["support_h"]
            all_active = primary_h + support_h
            predicted = []
            for age in range(1, 76):
                chart = timeline.get(f"chart_{age}", {})
                planets = chart.get("planets_in_houses", {})
                comp = 0.0; best = 0.0
                for k in cfg["karakas"]:
                    pd = planets.get(k)
                    if not pd: continue
                    h = pd.get("house",0)
                    if h not in all_active: continue
                    hw = 1.0 if h in primary_h else 0.5
                    s = planet_score(pd, k, age) * hw
                    comp += s
                    if s > best: best = s
                if best >= thresh_single and comp >= thresh_composite:
                    predicted.append(age)
            arr_len += len(predicted)
            if any(abs(a - actual_age) <= 1 for a in predicted):
                hits += 1
    pct = (hits/total*100) if total else 0
    avg_arr = (arr_len/total) if total else 0
    return pct, avg_arr, hits, total

print("Precomputing timelines...")
figures = json.load(open("backend/data/public_figures_ground_truth.json"))
base_gen = ChartGenerator()
q_gen = QuantumChartGenerator("backend/astroq/quantum_engine/quantum_weights.json")
timelines = []
figures_events = []
for fig in figures:
    events = fig.get("events", [])
    if not events: continue
    try:
        payload = base_gen.build_full_chart_payload(
            dob_str=fig['dob'], tob_str=fig.get('tob','12:00'),
            place_name=fig.get('birth_place','New Delhi'),
            latitude=fig.get('lat',28.61), longitude=fig.get('lon',77.20),
            utc_string=fig.get('tz','+05:30'), chart_system="vedic"
        )
        timeline = q_gen.generate_quantum_timeline(payload["chart_0"], max_years=75)
        natal_q = timeline.get("chart_0",{})
        timelines.append((timeline, natal_q))
        figures_events.append(events)
    except Exception as e:
        print(f"  skip {fig.get('name')}: {e}")

print(f"Loaded {len(timelines)} figures\n")
print(f"{'best_single':>12} {'composite':>10} {'timing%':>8} {'avg_array':>10}")
print("-"*45)
best_results = []
for bs in [0.5, 0.6, 0.7, 0.8, 0.9]:
    for comp in [0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5]:
        pct, avg_arr, hits, total = evaluate(timelines, figures_events, bs, comp)
        # score = timing% / avg_array (higher ratio = better)
        ratio = pct / max(avg_arr, 1)
        best_results.append((ratio, bs, comp, pct, avg_arr))
        print(f"{bs:>12.2f} {comp:>10.2f} {pct:>8.2f}% {avg_arr:>10.1f}")

print("\nTop 5 by ratio (timing% / avg_array):")
best_results.sort(reverse=True)
for ratio, bs, comp, pct, avg_arr in best_results[:5]:
    print(f"  single={bs:.2f} composite={comp:.2f} -> timing={pct:.2f}% avg_array={avg_arr:.1f} ratio={ratio:.3f}")
