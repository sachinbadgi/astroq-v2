import sys
import os
from datetime import datetime

# Add backend to path
sys.path.append(os.getcwd())

from vedicastro.VedicAstro import VedicHoroscopeData

def test_systems():
    # Sample data: Sachin Tendulkar
    # DOB: 1973-04-24, TOB: 16:20, POB: Mumbai
    # lat: 19.0760, lon: 72.8777
    
    systems = ["kp", "vedic"]
    for sys_name in systems:
        print(f"\n--- System: {sys_name.upper()} ---")
        ayanamsa = "Krishnamurti" if sys_name == "kp" else "Lahiri"
        house_system = "Placidus" if sys_name == "kp" else "Whole Sign"
        
        calc = VedicHoroscopeData(
            year=1973, month=4, day=24,
            hour=16, minute=20, second=0,
            utc="+05:30", latitude=19.0760, longitude=72.8777,
            ayanamsa=ayanamsa, house_system=house_system
        )
        
        chart = calc.generate_chart()
        planets = calc.get_planets_data_from_chart(chart)
        
        for p in planets:
            name = getattr(p, "Object", "N/A")
            if name in ["Sun", "Moon", "Asc"]:
                lon = getattr(p, "LonDecDeg", 0.0)
                house = getattr(p, "House", "N/A")
                print(f"Planet: {name:7} | Lon: {lon:8.2f} | House: {house}")

if __name__ == "__main__":
    test_systems()
