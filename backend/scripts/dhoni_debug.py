import os
import sys
import json

sys.path.append(os.path.join(os.getcwd(), "backend"))

from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.natal_fate_view import NatalFateView

generator = ChartGenerator()
fate_view = NatalFateView()

# MS Dhoni data
name = "MS Dhoni"
dob = "1981-07-07"
tob = "11:15:00"
place = "Ranchi, India"
lat, lon, tz = (23.3441, 85.3096, "+05:30")

payload = generator.build_full_chart_payload(
    dob_str=dob, tob_str=tob, place_name=place, 
    latitude=lat, longitude=lon, utc_string=tz, chart_system="vedic"
)

natal_chart = payload.get("chart_0")
fate_entries = fate_view.evaluate(natal_chart)

print(f"=== {name} Natal Fate View ===")
print(fate_view.format_as_table(fate_entries))
