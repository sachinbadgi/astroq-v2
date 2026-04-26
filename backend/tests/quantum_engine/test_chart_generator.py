from astroq.quantum_engine.chart_generator import QuantumChartGenerator

def test_generate_120_year_matrix():
    qcg = QuantumChartGenerator()
    natal_data = {
        "planets_in_houses": {
            "Sun": {"house": 1},
            "Venus": {"house": 2}
        }
    } 
    
    result = qcg.generate_quantum_timeline(natal_data, max_years=5)
    
    # Check that it returns dicts correctly mapped
    assert "chart_0" in result # Natal
    assert "chart_5" in result # Age 5
    
    # Sun was in House 1. Let's see where it is at age 2 (should be House 4 per YEAR_MATRIX mock)
    # The chart generator output should probably be StateVectors or dicts. Let's assume it returns dicts to match the pipeline.
    # We mocked YEAR_MATRIX in matrix_models to only have age 2 right now.
    age_2_chart = result["chart_2"]
    # Check if we can parse the amplitude back out, or if it just returns houses.
    # Since we want to interface with existing code or research loop, let's say it returns houses and amplitudes.
    sun_info = age_2_chart["planets_in_houses"].get("Sun", {})
    assert sun_info.get("house") == 4
    assert "amplitude" in sun_info
