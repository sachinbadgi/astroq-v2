"""
Validation tests for Lal Kitab Time Division Charts (Goswami 1952).

Covers:
1. Annual (Varshphal) chart planetary rotation logic.
2. Monthly chart Sun-based rotation.
3. Daily chart Mars-based progression.
4. Hourly chart Jupiter-based progression.
"""

import pytest
from astroq.lk_prediction.chart_generator import ChartGenerator

class TestTimeDivisionCharts:

    @pytest.fixture
    def cg(self):
        return ChartGenerator()

    @pytest.fixture
    def mock_natal(self):
        """Standard Birth Chart for validation."""
        return {
            "chart_type": "Birth",
            "chart_period": 0,
            "planets_in_houses": {
                "Sun":     {"house": 10},
                "Moon":    {"house": 2},
                "Mars":    {"house": 4},
                "Mercury": {"house": 11},
                "Jupiter": {"house": 5},
                "Venus":   {"house": 9},
                "Saturn":  {"house": 1},
                "Rahu":    {"house": 6},
                "Ketu":    {"house": 12}
            }
        }

    def test_annual_chart_rotation_logic(self, cg, mock_natal):
        """Validate Varshphal placement using YEAR_MATRIX for Year 4."""
        # Year 4 matrix mapping: {10: 7} for Sun.
        # Natal House 10 -> Annual House 7.
        annual_charts = cg.generate_annual_charts(mock_natal, max_years=5)
        year_4 = annual_charts["chart_4"]
        
        sun_annual = year_4["planets_in_houses"]["Sun"]["house"]
        # From YEAR_MATRIX[4]: 10 maps to 7
        assert sun_annual == 7
        
        # Natal House 2 (Moon) -> Annual House 8
        # From YEAR_MATRIX[4]: 2 maps to 8
        moon_annual = year_4["planets_in_houses"]["Moon"]["house"]
        assert moon_annual == 8

    def test_monthly_chart_rotation(self, cg, mock_natal):
        """Monthly chart: Rotating Annual chart so that Sun's house becomes H1."""
        # Step 1: Get Annual Year 4 (Sun in H7)
        year_4 = cg.generate_annual_charts(mock_natal, max_years=4)["chart_4"]
        assert year_4["planets_in_houses"]["Sun"]["house"] == 7
        
        # Step 2: Generate Monthly chart 1
        month_1 = cg.generate_monthly_chart(year_4, month_number=1)
        
        # Sun must now be in House 1
        assert month_1["planets_in_houses"]["Sun"]["house"] == 1
        
        # Rotation calculation: (SunHouse - 1) = (7 - 1) = 6.
        # Planet in Annual House A moves to Monthly House ((A-1 - 6)%12)+1.
        # Let's check Moon. In Year 4, Moon is in H8.
        # Monthly H = ((8-1-6)%12)+1 = (1%12)+1 = 2.
        assert month_1["planets_in_houses"]["Moon"]["house"] == 2

    def test_daily_chart_progression(self, cg, mock_natal):
        """Daily chart: Counting days from Mars's house in Monthly chart."""
        year_4 = cg.generate_annual_charts(mock_natal, max_years=4)["chart_4"]
        month_1 = cg.generate_monthly_chart(year_4, month_number=1)
        mars_monthly = month_1["planets_in_houses"]["Mars"]["house"]
        assert mars_monthly == 7
        
        # Day 17 progression (Additive shift: 16 positions)
        day_17 = cg.generate_daily_chart(month_1, days_elapsed=17)
        
        # Mars should move from H7 by 16 positions: ((7-1 + 16)%12)+1 = (22%12)+1 = 11.
        assert day_17["planets_in_houses"]["Mars"]["house"] == 11
        
        # Sun was H1 in Monthly. Daily H = ((1-1+16)%12)+1 = 5.
        assert day_17["planets_in_houses"]["Sun"]["house"] == 5

    def test_hourly_chart_progression(self, cg, mock_natal):
        """Hourly chart: Counting hours from Jupiter's house in Daily chart."""
        year_1 = cg.generate_annual_charts(mock_natal, max_years=1)["chart_1"]
        month_1 = cg.generate_monthly_chart(year_1, month_number=1)
        day_1 = cg.generate_daily_chart(month_1, days_elapsed=1)
        
        # Jupiter pos in Day 1 (Month 1/Year 1):
        # Natal Jup H5 -> Year 1 Matrix[1][5] = H5.
        # Annual Sun (Natal H10) -> Year 1 Matrix[1][10] = H12.
        # Monthly (Sun H12 -> H1, rotation 11) -> Monthly Jup: ((5-1-11)%12)+1 = 6.
        # Day 1 shift 0 -> Daily Jup H6.
        assert day_1["planets_in_houses"]["Jupiter"]["house"] == 6
        
        # Hour 6 progression (Additive shift: 5 positions)
        hour_6 = cg.generate_hourly_chart(day_1, hour=6)
        
        # Jupiter should move from H6 by 5 positions: ((6-1 + 5)%12)+1 = 11.
        assert hour_6["planets_in_houses"]["Jupiter"]["house"] == 11
        
        # Sun in Day 1 was H1 (rotation on Annual Sun H12).
        # Hour 6 Sun: ((1-1+5)%12)+1 = 6.
        assert hour_6["planets_in_houses"]["Sun"]["house"] == 6
