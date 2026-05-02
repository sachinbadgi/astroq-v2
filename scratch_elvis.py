import json
from backend.astroq.lk_prediction.chart_generator import ChartGenerator

figures = json.load(open("backend/data/public_figures_ground_truth.json"))
elvis = [f for f in figures if f['name'] == 'Elvis Presley'][0]

generator = ChartGenerator()
payload = generator.build_full_chart_payload(
    dob_str=elvis['dob'], tob_str=elvis.get('tob', '12:00'),
    place_name=elvis.get('birth_place', 'New Delhi'),
    latitude=elvis.get('lat', 28.61), longitude=elvis.get('lon', 77.20),
    utc_string=elvis.get('tz', '+05:30')
)

natal = payload['chart_0']['planets_in_houses']
print(json.dumps(natal, indent=2))
