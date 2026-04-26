import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.getcwd(), "backend")))

from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.quantum_engine.chart_generator import QuantumChartGenerator

JSON_PATH = "backend/data/public_figures_ground_truth.json"
CONFIG_PATH = "backend/astroq/quantum_engine/quantum_weights.json"

# Unified karaka list per domain ordered by decreasing structural importance
# primary_h = houses that alone are sufficient for GP; support_h = contribute partial signal
DOMAIN_CONFIG = {
    "marriage":     {"karakas": ["Venus", "Mercury"],                                 "primary_h": [7],         "support_h": [2]},
    "career":       {"karakas": ["Sun", "Mars", "Saturn", "Jupiter"],                 "primary_h": [10],        "support_h": [6, 2]},
    "career_travel":{"karakas": ["Sun", "Mars", "Saturn", "Rahu", "Jupiter", "Ketu"], "primary_h": [10],        "support_h": [6, 2, 12, 9]},
    "health":       {"karakas": ["Sun", "Mars", "Saturn"],                            "primary_h": [1, 6],      "support_h": [8]},
    "progeny":      {"karakas": ["Jupiter", "Ketu"],                                 "primary_h": [5],         "support_h": []},
    "real_estate":  {"karakas": ["Moon", "Mars", "Saturn"],                          "primary_h": [4],         "support_h": [8]},
    "finance":      {"karakas": ["Jupiter", "Venus", "Mercury"],                     "primary_h": [2, 11],     "support_h": [9]},
}

# For backward-compat — flat lists
DOMAIN_KARAKAS = {k: v["karakas"] for k, v in DOMAIN_CONFIG.items()}
ACTIVE_HOUSES  = {k: v["primary_h"] + v["support_h"] for k, v in DOMAIN_CONFIG.items()}

# Planetary unit weights from LK Quantum MD (income-unit basis)
# Jupiter=11, Saturn=10.5, Sun=10, Moon=9, Mars=8, Mercury=3, Venus=6, Rahu=7, Ketu=6
PLANET_UNITS = {
    "Jupiter": 11, "Saturn": 10.5, "Sun": 10, "Moon": 9,
    "Mars": 8,  "Rahu": 7, "Venus": 6, "Ketu": 6, "Mercury": 3
}

PLANET_MATURITY = {
    "Jupiter": 16, "Sun": 22, "Moon": 24, "Venus": 25, 
    "Mars": 28, "Mercury": 34, "Saturn": 36, "Rahu": 42, "Ketu": 48
}

CYCLE_35_YEAR_RANGES = [
    (1, 6, "Saturn"), (7, 12, "Rahu"), (13, 15, "Ketu"),
    (16, 21, "Jupiter"), (22, 23, "Sun"), (24, 24, "Moon"),
    (25, 27, "Venus"), (28, 33, "Mars"), (34, 35, "Mercury")
]

def get_35_year_ruler(age):
    period = (age - 1) % 35 + 1
    for start, end, planet in CYCLE_35_YEAR_RANGES:
        if start <= period <= end:
            return planet
    return None

def _get_planet_score(planet_data, karaka_name, age):
    """
    Compute the quantum probability score for a single planet.
    Incorporates:
      - Base amplitude (dignity: Exalted=2, Normal=1)
      - Unit weight from LK income table (Jupiter=11, Saturn=10.5 ...)
      - Maturity dampening (pre-maturity age halves the score)
      - 35-Year Cycle awakening boost (only active ruler gets the boost)
      - Pakka Ghar / Exalted EXCEPTION: dignified planets bypass dormancy
    """
    if not planet_data: return 0.0
    amp = planet_data.get("amplitude", 0)
    if amp <= 0: return 0.0

    # Scale by canonical unit weight (normalised to max=1.0)
    unit_weight = PLANET_UNITS.get(karaka_name, 5) / 11.0  # Jupiter=1.0, Mercury≈0.27
    score = amp * unit_weight

    if age != 99:
        # Maturity gate
        maturity_age = PLANET_MATURITY.get(karaka_name, 0)
        if age < maturity_age:
            score *= 0.5

        is_ruler = (get_35_year_ruler(age) == karaka_name)
        # Dignified = Exalted (5.0) or Pakka Ghar (2.2)
        is_dignified = (amp >= 2.2)

        if is_ruler:
            # Awakened: apply full boost
            score += 1.0
        elif is_dignified:
            # Pakka/Exalted exception: always partially awake — never fully dormant
            # The planet's structural dignity makes it permanently observable
            score *= 0.7
        else:
            # SOYI HUI (Dormant): strict suppression for undignified non-rulers
            score *= 0.05

    return score

def is_event_triggered_domain(annual_chart, domain, age):
    """
    Multi-gate confirmation:
    Scans all karakas for the domain. Requires:
      1. At least one karaka individually clears a per-planet minimum score (0.35)
      2. Composite score across all karakas in active houses clears 0.7
    Primary houses give full score weight; support houses give 0.5x.
    """
    config = DOMAIN_CONFIG.get(domain)
    if not config: return False

    karakas        = config["karakas"]
    primary_houses = config["primary_h"]
    support_houses = config["support_h"]
    all_active     = primary_houses + support_houses

    planets_in_houses = annual_chart.get("planets_in_houses", {})

    composite   = 0.0
    best_single = 0.0   # highest individual score

    for karaka in karakas:
        p_data = planets_in_houses.get(karaka)
        if not p_data: continue
        house = p_data.get("house", 0)
        if house not in all_active: continue
        house_weight = 1.0 if house in primary_houses else 0.5
        s = _get_planet_score(p_data, karaka, age) * house_weight
        composite += s
        if s > best_single:
            best_single = s

    # Gate: at least ONE karaka must be active AND composite passes
    # Optimal thresholds from auto-tuner: best_single=0.5, composite=0.9
    return (best_single >= 0.5) and (composite >= 0.9)


def is_natal_promise(natal_chart, domain):
    """Check if any karaka is dignified (Exalted/Pakka) AND sits in an active house."""
    config = DOMAIN_CONFIG.get(domain)
    if not config: return False, None
    planets = natal_chart.get("planets_in_houses", {})
    all_active = config["primary_h"] + config["support_h"]
    for karaka in config["karakas"]:
        p_data = planets.get(karaka)
        if not p_data: continue
        amp   = p_data.get("amplitude", 0)
        house = p_data.get("house", 0)
        if amp >= 2.2 and house in all_active:
            return True, (karaka, house)
    return False, None

def fetch_ground_truth():
    if not os.path.exists(JSON_PATH):
        print(f"Error: {JSON_PATH} not found.")
        return []
        
    with open(JSON_PATH, 'r') as f:
        return json.load(f)

def generate_forensic_report():
    print("Loading Public Figures Data...")
    figures = fetch_ground_truth()
    if not figures: return

    print("Initializing Quantum Engine...")
    base_generator = ChartGenerator()
    quantum_generator = QuantumChartGenerator(CONFIG_PATH)
    
    total_events = 0
    natal_promises = 0
    annual_hits = 0
    
    report_lines = []
    
    report_lines.append("==================================================================")
    report_lines.append("           QUANTUM ENGINE FORENSIC TIMING REPORT                  ")
    report_lines.append("==================================================================\n")

    for fig in figures:
        name = fig.get("name", "Unknown")
        events = fig.get("events", [])
        if not events: continue

        try:
            payload = base_generator.build_full_chart_payload(
                dob_str=fig['dob'], tob_str=fig.get('tob', '12:00'),
                place_name=fig.get('birth_place', 'New Delhi'),
                latitude=fig.get('lat', 28.61), longitude=fig.get('lon', 77.20),
                utc_string=fig.get('tz', '+05:30'),
                chart_system="vedic"
            )
            natal_data = payload["chart_0"]
        except Exception as e:
            continue
            
        timeline = quantum_generator.generate_quantum_timeline(natal_data, max_years=75)
        natal_quantum_chart = timeline.get("chart_0", {})
        
        for ev in events:
            actual_age = ev.get("age")
            domain = ev.get("domain", "").lower()
            desc = ev.get("description", "")
            
            karakas = DOMAIN_KARAKAS.get(domain)
            if not karakas: continue
            total_events += 1
            
            report_lines.append(f"FIGURE: {name} | EVENT: {desc}")
            report_lines.append(f"  -> Ground Truth Age: {actual_age} | Domain: {domain} | Karakas: {karakas}")
            
            # --- Check Natal Promise (primary dignified karaka in active house) ---
            promise, promise_detail = is_natal_promise(natal_quantum_chart, domain)
            if promise:
                natal_promises += 1
                karaka_n, house_n = promise_detail
                report_lines.append(f"  -> Natal Promise: YES (Primary karaka {karaka_n} dignified in house {house_n})")
            else:
                report_lines.append(f"  -> Natal Promise: NO (No primary karaka dignified in active house)")
            
            # --- Multi-gate annual scan ---
            predicted_ages = []
            for age in range(1, 76):
                annual_chart = timeline.get(f"chart_{age}", {})
                if is_event_triggered_domain(annual_chart, domain, age):
                    predicted_ages.append(age)
            
            report_lines.append(f"  -> Predicted Trigger Ages: {predicted_ages}")
            
            # --- Check Match ---
            if actual_age in predicted_ages or (actual_age - 1) in predicted_ages or (actual_age + 1) in predicted_ages:
                annual_hits += 1
                report_lines.append(f"  -> Match with Ground Truth: YES! (Engine successfully hit the window)")
            else:
                report_lines.append(f"  -> Match with Ground Truth: NO.")
                
            report_lines.append("-" * 66)

    # Summary
    report_lines.append("\n==================================================================")
    report_lines.append("                          SUMMARY STATS                           ")
    report_lines.append("==================================================================")
    report_lines.append(f"Total Events Analyzed        : {total_events}")
    report_lines.append(f"Natal Promise Confirmed      : {natal_promises} ({(natal_promises/total_events)*100 if total_events else 0:.2f}%)")
    report_lines.append(f"Accurate Timing Match (+/-1) : {annual_hits} ({(annual_hits/total_events)*100 if total_events else 0:.2f}%)")
    report_lines.append("==================================================================")

    output_file = "autonomous_research/forensic_output.txt"
    with open(output_file, "w") as f:
        f.write("\n".join(report_lines))
        
    print(f"\nDetailed forensic report generated and saved to: {output_file}")
    print("\n" + "\n".join(report_lines[-8:]))

if __name__ == "__main__":
    generate_forensic_report()
