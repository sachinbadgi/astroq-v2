import json
from backend.astroq.quantum_engine.chart_generator import QuantumChartGenerator
from backend.astroq.lk_prediction.chart_generator import ChartGenerator

figures = json.load(open("backend/data/public_figures_ground_truth.json"))
dhoni = [f for f in figures if f['name'] == 'MS Dhoni'][0]

base_gen = ChartGenerator()
payload = base_gen.build_full_chart_payload(
    dob_str=dhoni['dob'], tob_str=dhoni.get('tob', '12:00'),
    place_name=dhoni.get('birth_place', 'New Delhi'),
    latitude=dhoni.get('lat', 28.61), longitude=dhoni.get('lon', 77.20),
    utc_string=dhoni.get('tz', '+05:30'),
    chart_system="vedic"
)
natal_base = payload['chart_0']

q_gen = QuantumChartGenerator("backend/astroq/quantum_engine/quantum_weights.json")
timeline = q_gen.generate_quantum_timeline(natal_base, max_years=1)

natal_quantum = timeline['chart_0']
print("BASE CHART MARS:", natal_base['planets_in_houses'].get('Mars'))
print("QUANTUM CHART MARS:", natal_quantum['planets_in_houses'].get('Mars'))
