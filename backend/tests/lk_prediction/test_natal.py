import os
import sys

# Add the project root to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from astroq.lk_prediction.chart_generator import ChartGenerator

gen = ChartGenerator()
dob = '1973-04-24'
tob = '00:15'
place = 'Bombay, India'
lat = 18.9750
lon = 72.8258
utc_string = '+05:30'

def print_chart(system):
    print(f"\n{system.upper()} Chart:")
    chart = gen.generate_chart(dob, tob, place, lat, lon, utc_string, system)
    for p, d in sorted(chart['planets_in_houses'].items()):
        print(f"  {p}: {d['house']}")

print_chart('vedic')
print_chart('kp')
