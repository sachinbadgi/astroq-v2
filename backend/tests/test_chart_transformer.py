"""
Tests for ChartTransformer — pure transformation logic, no flatlib/ephemeris.

Run: cd backend && python3 -m pytest tests/test_chart_transformer.py -v
"""
import pytest
from astroq.lk_prediction.chart_transformer import (
    ChartTransformer, YEAR_MATRIX, STANDARD_PLANETS, MONTHLY_RULERS
)

# Amitabh-like natal chart fixture (no ephemeris needed)
AMITABH_NATAL = {
    "Sun": 6, "Moon": 9, "Mars": 4, "Mercury": 6,
    "Jupiter": 6, "Venus": 6, "Saturn": 8, "Rahu": 7, "Ketu": 1,
}

def make_natal():
    return ChartTransformer.build_natal_chart_data(
        AMITABH_NATAL, "1942-10-11T16:00:00", "vedic"
    )


# ---------------------------------------------------------------------------
# detect_planet_states
# ---------------------------------------------------------------------------
class TestDetectPlanetStates:

    def test_exalted_sun_h1(self):
        states = ChartTransformer.detect_planet_states("Sun", 1)
        assert "Exalted" in states

    def test_debilitated_saturn_h1(self):
        # Saturn debilitated in H1 per Lal Kitab
        states = ChartTransformer.detect_planet_states("Saturn", 1)
        assert "Debilitated" in states

    def test_fixed_house_lord(self):
        # Jupiter is Fixed House Lord in H2 (Pakka Ghar)
        states = ChartTransformer.detect_planet_states("Jupiter", 2)
        assert "Fixed House Lord" in states

    def test_neutral_house_no_states(self):
        # Sun in H5 should have no special states
        states = ChartTransformer.detect_planet_states("Sun", 5)
        assert states == [] or "Fixed House Lord" not in states


# ---------------------------------------------------------------------------
# build_natal_chart_data
# ---------------------------------------------------------------------------
class TestBuildNatalChartData:

    def test_output_keys(self):
        natal = make_natal()
        assert "chart_type" in natal
        assert "planets_in_houses" in natal
        assert natal["chart_type"] == "Birth"

    def test_standard_planets_included(self):
        natal = make_natal()
        pih = natal["planets_in_houses"]
        for p in STANDARD_PLANETS:
            assert p in pih, f"{p} missing from planets_in_houses"

    def test_non_standard_planet_excluded(self):
        chart = ChartTransformer.build_natal_chart_data(
            {"Sun": 1, "Asc": 3, "Unknown": 5}, "2000-01-01T00:00:00"
        )
        assert "Asc" not in chart["planets_in_houses"]
        assert "Unknown" not in chart["planets_in_houses"]

    def test_house_natal_set_correctly(self):
        natal = make_natal()
        for planet, house in AMITABH_NATAL.items():
            if planet in STANDARD_PLANETS:
                assert natal["planets_in_houses"][planet]["house_natal"] == house

    def test_states_populated(self):
        natal = make_natal()
        for p, data in natal["planets_in_houses"].items():
            assert "states" in data
            assert isinstance(data["states"], list)


# ---------------------------------------------------------------------------
# generate_annual_charts
# ---------------------------------------------------------------------------
class TestGenerateAnnualCharts:

    def test_generates_75_charts(self):
        natal = make_natal()
        charts = ChartTransformer.generate_annual_charts(natal, max_years=75)
        assert len(charts) == 75
        assert "chart_1" in charts
        assert "chart_75" in charts

    def test_chart_1_uses_year_matrix_row_1(self):
        natal = make_natal()
        charts = ChartTransformer.generate_annual_charts(natal, 1)
        chart1 = charts["chart_1"]
        mapping = YEAR_MATRIX[1]
        # Ketu natal H1 → mapping[1] = 1
        ketu_natal_h = AMITABH_NATAL["Ketu"]
        expected_h = mapping[ketu_natal_h]
        assert chart1["planets_in_houses"]["Ketu"]["house"] == expected_h

    def test_chart_type_is_yearly(self):
        natal = make_natal()
        charts = ChartTransformer.generate_annual_charts(natal, 3)
        for k, c in charts.items():
            assert c["chart_type"] == "Yearly"

    def test_period_dates_populated_when_birth_time_given(self):
        natal = make_natal()
        charts = ChartTransformer.generate_annual_charts(natal, 2)
        assert "period_start" in charts["chart_1"]
        assert "period_end" in charts["chart_1"]

    def test_natal_house_not_mutated(self):
        natal = make_natal()
        original_ketu_house = natal["planets_in_houses"]["Ketu"]["house"]
        ChartTransformer.generate_annual_charts(natal, 75)
        assert natal["planets_in_houses"]["Ketu"]["house"] == original_ketu_house


# ---------------------------------------------------------------------------
# Sub-chart generation
# ---------------------------------------------------------------------------
class TestSubChartGeneration:

    def _annual(self):
        natal = make_natal()
        charts = ChartTransformer.generate_annual_charts(natal, 30)
        return charts["chart_30"]

    def test_monthly_chart_has_metadata(self):
        annual = self._annual()
        monthly = ChartTransformer.generate_monthly_chart(annual, month_number=3)
        assert monthly["chart_type"] == "Monthly"
        assert monthly["monthly_ruler"] == MONTHLY_RULERS[2]
        assert monthly["chart_period_month"] == 3

    def test_monthly_ruler_house_becomes_h1(self):
        annual = self._annual()
        for month in [1, 4, 7, 12]:
            monthly = ChartTransformer.generate_monthly_chart(annual, month)
            ruler = monthly["monthly_ruler"]
            # After rotation the ruler should be in H1
            assert monthly["planets_in_houses"][ruler]["house"] == 1

    def test_daily_chart_has_metadata(self):
        annual = self._annual()
        monthly = ChartTransformer.generate_monthly_chart(annual, 1)
        daily = ChartTransformer.generate_daily_chart(monthly, days_elapsed=5)
        assert daily["chart_type"] == "Daily"
        assert daily["chart_period_day"] == 5

    def test_hourly_chart_has_metadata(self):
        annual = self._annual()
        monthly = ChartTransformer.generate_monthly_chart(annual, 1)
        daily = ChartTransformer.generate_daily_chart(monthly, 1)
        hourly = ChartTransformer.generate_hourly_chart(daily, hour=6)
        assert hourly["chart_type"] == "Hourly"
        assert hourly["chart_period_hour"] == 6

    def test_all_houses_in_range_1_to_12(self):
        annual = self._annual()
        monthly = ChartTransformer.generate_monthly_chart(annual, 1)
        for planet, data in monthly["planets_in_houses"].items():
            h = data["house"]
            assert 1 <= h <= 12, f"{planet} has invalid house {h} in monthly chart"


# ---------------------------------------------------------------------------
# YEAR_MATRIX integrity
# ---------------------------------------------------------------------------
class TestYearMatrix:

    def test_year_1_to_75_all_present(self):
        for y in range(1, 76):
            assert y in YEAR_MATRIX, f"YEAR_MATRIX missing year {y}"

    def test_each_row_has_12_entries(self):
        for year, mapping in YEAR_MATRIX.items():
            assert len(mapping) == 12, f"Year {year} has {len(mapping)} entries (expected 12)"

    def test_each_row_is_a_permutation_of_1_to_12(self):
        for year, mapping in YEAR_MATRIX.items():
            assert sorted(mapping.values()) == list(range(1, 13)), \
                f"Year {year} is not a permutation of 1-12"

    def test_all_houses_used_as_keys(self):
        for year, mapping in YEAR_MATRIX.items():
            assert set(mapping.keys()) == set(range(1, 13)), \
                f"Year {year} has unexpected keys: {set(mapping.keys())}"
