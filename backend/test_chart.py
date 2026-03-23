import sys
sys.path.append('d:/astroq-v2/backend')

from astroq.lk_prediction.chart_generator import ChartGenerator

cg = ChartGenerator()
payload = cg.build_full_chart_payload(
    dob_str="28-11-1977",
    tob_str="18:30",
    place_name="sangli maharashtra",
    chart_system="kp"
)

print(payload['chart_0']['planets_in_houses'])
