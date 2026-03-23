import pytest
from astroq.lk_prediction.chart_generator import ChartGenerator

def test_chart_system_differentiation():
    cg = ChartGenerator()
    
    # Pune profile that we know has a Mercury shift
    dob = "1990-01-01"
    tob = "12:00"
    lat = 18.5204
    lon = 73.8567
    utc = "+05:30"
    
    # 1. Generate Vedic
    vedic = cg.generate_chart(dob, tob, "Pune", lat, lon, utc, "vedic")
    v_planets = vedic["planets_in_houses"]
    
    # 2. Generate KP
    kp = cg.generate_chart(dob, tob, "Pune", lat, lon, utc, "kp")
    k_planets = kp["planets_in_houses"]
    
    # Verify Asc is always 1
    assert v_planets["Asc"]["house"] == 1
    assert k_planets["Asc"]["house"] == 1
    
    # Verify Mercury shift (based on our diagnostic)
    assert v_planets["Mercury"]["house"] == 11
    assert k_planets["Mercury"]["house"] == 10
    
    # Verify Sun remains same (but different lon, though house is same)
    assert v_planets["Sun"]["house"] == 10
    assert k_planets["Sun"]["house"] == 10
    
    print("Differentiation test passed successfully.")

def test_chart_system_invalid_choice():
    cg = ChartGenerator()
    with pytest.raises(ValueError):
        cg.generate_chart("1990-01-01", "12:00", "Pune", 18.5, 73.8, "+05:30", "invalid")
