import sys
import os

# Add backend to path
sys.path.append(r'd:\astroq-v2\backend')

from astroq.lk_prediction.chart_generator import ChartGenerator

def verify():
    gen = ChartGenerator()
    # Steve Jobs: Feb 24, 1955, 19:15, San Francisco
    # Tropical Sun in late Aquarius (~305°) -> House 11
    # Tropical Jupiter in early Cancer (~110°) -> House 4
    # Tropical Saturn in late Scorpio (~231°) -> House 8
    
    try:
        # Now defaults to Tropical and Sign-as-House
        natal = gen.generate_chart(
            dob_str="1955-02-24",
            tob_str="19:15",
            place_name="San Francisco",
            latitude=37.7749,
            longitude=-122.4194,
            utc_string="-08:00",
            chart_system="vedic" 
        )
    except Exception as e:
        print(f"Error generating chart: {e}")
        return

    planets = natal["planets_in_houses"]
    
    print("Verifying Test Case: Steve Jobs (Tropical / Sayana)")
    
    sun_h = planets.get("Sun", {}).get("house")
    jup_h = planets.get("Jupiter", {}).get("house")
    sat_h = planets.get("Saturn", {}).get("house")
    
    print(f"Sun House: {sun_h} (Expected: 11)")
    print(f"Jupiter House: {jup_h} (Expected: 4)")
    print(f"Saturn House: {sat_h} (Expected: 8)")
    
    if sun_h == 11 and jup_h == 4 and sat_h == 8:
        print("\nSUCCESS: Lal Kitab Fixed Zodiac (Sayana) verified.")
    else:
        print("\nFAILURE: House mapping mismatch.")

if __name__ == "__main__":
    verify()
