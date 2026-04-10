import sys
import os
import json

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from astroq.lk_prediction.chart_generator import ChartGenerator

def check_pichai():
    generator = ChartGenerator()
    try:
        # Madurai, India approx: 9.9252, 78.1198
        payload = generator.build_full_chart_payload(
            dob_str="1972-06-10",
            tob_str="12:00",
            place_name="Madurai, India",
            latitude=9.9252,
            longitude=78.1198,
            utc_string="+05:30",
            chart_system="kp"
        )
        natal = payload["chart_0"]
        print(json.dumps(natal["planets_in_houses"], indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_pichai()
