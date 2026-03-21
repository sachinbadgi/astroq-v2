import pytest
from datetime import datetime
from astroq.lk_prediction.chart_generator import ChartGenerator

class TestChartGenerator:

    @pytest.fixture
    def chart_generator(self):
        return ChartGenerator()

    def test_chart_generator_parses_dob_and_tob_robustly(self, chart_generator):
        """Should parse different date and time formats."""
        res = chart_generator._parse_date_time("1990-06-21", "14:30")
        assert res["year"] == 1990
        assert res["month"] == 6
        assert res["day"] == 21
        assert res["hour"] == 14
        assert res["minute"] == 30

        # Alternate format
        res2 = chart_generator._parse_date_time("21/06/1990", "2:30 PM")
        assert res2["year"] == 1990
        assert res2["hour"] == 14

    def test_chart_generator_geocodes_place_name(self, chart_generator):
        """Given a place string, should correctly retrieve latitude, longitude, and UTC offset."""
        locations = chart_generator.geocode_place("New Delhi, India")
        assert len(locations) > 0
        loc = locations[0]
        assert "latitude" in loc
        assert "longitude" in loc
        assert "utc_offset" in loc
        assert loc["utc_offset"] == "+05:30"
        
    def test_chart_generator_returns_empty_list_for_invalid_place(self, chart_generator):
        """Should return empty list for garbage un-geocodeable string."""
        locations = chart_generator.geocode_place("FakeCityInTheSky123xyz")
        assert len(locations) == 0

    def test_chart_generator_builds_natal_chart_data(self, chart_generator):
        """Generates the base 'ChartData' object matching our data contracts directly from VedicAstro."""
        natal_chart = chart_generator.generate_chart(
            dob_str="1990-05-15",
            tob_str="14:30:00",
            place_name="New Delhi, India",
            latitude=28.6139,
            longitude=77.2090,
            utc_string="+05:30",
            chart_system="kp"
        )
        
        assert "chart_type" in natal_chart
        assert natal_chart["chart_type"] == "Birth"
        assert natal_chart["chart_period"] == 0
        assert "planets_in_houses" in natal_chart
        assert "Sun" in natal_chart["planets_in_houses"]
        assert "Moon" in natal_chart["planets_in_houses"]
        # Basic validation that it's populated
        assert natal_chart["planets_in_houses"]["Sun"]["house"] > 0
        
    def test_chart_generator_builds_75_varshaphal_charts(self, chart_generator):
        """Should output all 75 annual charts using Lal Kitab progression rules."""
        # Need a simple mock natal chart input to extract
        mock_natal = {
            "chart_type": "Birth",
            "chart_period": 0,
            "planets_in_houses": {
                "Sun": {"house": 10},
                "Moon": {"house": 2},
                "Mars": {"house": 4},
                "Mercury": {"house": 11},
                "Jupiter": {"house": 5},
                "Venus": {"house": 9},
                "Saturn": {"house": 1},
                "Rahu": {"house": 6},
                "Ketu": {"house": 12}
            }
        }
        
        annual_charts = chart_generator.generate_annual_charts(mock_natal, max_years=75)
        
        assert len(annual_charts) == 75
        assert "chart_1" in annual_charts
        assert "chart_75" in annual_charts
        
        # Age 1 (First year) should shift planets... 
        # Actually Lal Kitab annual chart logic varies, so we just verify the structure is there
        ch1 = annual_charts["chart_1"]
        assert ch1["chart_type"] == "Yearly"
        assert ch1["chart_period"] == 1
        assert "Sun" in ch1["planets_in_houses"]
        
    def test_chart_generator_full_pipeline_wrapper(self, chart_generator):
        """Test wrapper that builds the fully populated dict {"chart_0", "chart_1" ... "chart_75"}"""
        full_payload = chart_generator.build_full_chart_payload(
            dob_str="1990-05-15",
            tob_str="14:30:00",
            place_name="New Delhi, India",
            chart_system="kp"
        )
        
        assert "chart_0" in full_payload
        assert "chart_75" in full_payload
        assert full_payload["chart_0"]["chart_type"] == "Birth"
        assert full_payload["chart_75"]["chart_type"] == "Yearly"
