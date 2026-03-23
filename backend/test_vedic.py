import sys
sys.path.append('d:/astroq-v2/backend')

from vedicastro.VedicAstro import VedicHoroscopeData

# 1977-11-28 18:30 sangli 
# lat 16.8524, lon 74.5815, tz +05:30
# To match user chart, let's see what vedicastro produces manually
vhd = VedicHoroscopeData(
    year=1977, month=11, day=28,
    hour=18, minute=30, second=0,
    utc="+05:30", latitude=16.8524, longitude=74.5815,
    ayanamsa="Lahiri", house_system="Whole Sign"
)
chart = vhd.generate_chart()
planets = vhd.get_planets_data_from_chart(chart)

for p in planets:
    print(f"{getattr(p, 'Object', 'N/A')}: Sign = {getattr(p, 'SignNr', 'N/A')}, House = {getattr(p, 'HouseNr', 'N/A')}")
