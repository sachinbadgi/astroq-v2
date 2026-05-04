"""
Tests for CalibrationModule — specifically verifying the _compute_axis_metrics
stub has been replaced with a real implementation.

Run: cd backend && python3 -m pytest tests/test_calibration_module.py -v
"""
import pytest
from astroq.lk_prediction.calibration_module import (
    CalibrationModule,
    CalibrationResult,
    AxisMetrics,
    DomainMetrics,
)


# ---------------------------------------------------------------------------
# AxisMetrics unit tests
# ---------------------------------------------------------------------------
class TestAxisMetrics:

    def test_precision_with_data(self):
        am = AxisMetrics(axis="1-8", tp=83, fp=17)
        assert am.precision == pytest.approx(0.83)

    def test_precision_zero_sample(self):
        am = AxisMetrics(axis="2-6")
        assert am.precision == 0.0

    def test_sample_count(self):
        am = AxisMetrics(axis="4-10", tp=50, fp=30)
        assert am.sample_count == 80

    def test_to_dict_keys(self):
        am = AxisMetrics(axis="1-7", tp=40, fp=60)
        d = am.to_dict()
        assert set(d.keys()) == {"axis", "tp", "fp", "precision", "sample_count"}
        assert d["precision"] == pytest.approx(0.40)


# ---------------------------------------------------------------------------
# _compute_axis_metrics unit tests (directly via a mocked CalibrationModule)
# ---------------------------------------------------------------------------
class TestComputeAxisMetrics:

    def _module(self):
        # CalibrationModule with a fake db path (we won't call calibrate())
        cm = object.__new__(CalibrationModule)
        cm.db_path = ":memory:"
        cm._conn = None
        return cm

    def test_empty_rows_returns_empty_dict(self):
        cm = self._module()
        result = cm._compute_axis_metrics([])
        assert result == {}

    def test_rows_without_dignity_returns_empty_dict(self):
        cm = self._module()
        rows = [
            {"domain": "marriage", "fate_type": "RASHI_PHAL",
             "is_event": 1, "source_planet": "Venus", "target_planet": "Moon",
             "source_dignity": None, "target_dignity": None},
        ]
        result = cm._compute_axis_metrics(rows)
        assert result == {}

    def test_low_low_maps_to_1_8(self):
        """Both planets debilitated (Low×Low) → Takkar axis (1-8)."""
        cm = self._module()
        rows = [
            {"source_dignity": -5.0, "target_dignity": -5.0, "is_event": 1},
            {"source_dignity": -3.0, "target_dignity": -3.0, "is_event": 0},
        ]
        result = cm._compute_axis_metrics(rows)
        assert "1-8" in result
        assert result["1-8"].tp == 1
        assert result["1-8"].fp == 1

    def test_high_medium_maps_to_2_6(self):
        """Source High + Target Medium → Gali Sweet Spot (2-6)."""
        cm = self._module()
        rows = [
            {"source_dignity": 3.0, "target_dignity": 0.0, "is_event": 1},  # High × Medium
        ]
        result = cm._compute_axis_metrics(rows)
        assert "2-6" in result
        assert result["2-6"].tp == 1

    def test_any_high_target_maps_to_1_7(self):
        """Target High → 1-7 Opposition (strong shield)."""
        cm = self._module()
        rows = [
            {"source_dignity": 0.0, "target_dignity": 4.0, "is_event": 0},  # × High
        ]
        result = cm._compute_axis_metrics(rows)
        assert "1-7" in result
        assert result["1-7"].fp == 1

    def test_any_low_target_maps_to_4_10(self):
        """Target Low (and source not Low×Low) → 4-10 Square (weak anvil)."""
        cm = self._module()
        rows = [
            {"source_dignity": 2.0, "target_dignity": -3.0, "is_event": 1},  # High × Low
        ]
        result = cm._compute_axis_metrics(rows)
        assert "4-10" in result
        assert result["4-10"].tp == 1

    def test_other_maps_to_3_11(self):
        """Medium × Medium → 3-11 Support."""
        cm = self._module()
        rows = [
            {"source_dignity": 0.0, "target_dignity": 0.0, "is_event": 0},
        ]
        result = cm._compute_axis_metrics(rows)
        assert "3-11" in result

    def test_multiple_axes_computed_independently(self):
        cm = self._module()
        rows = [
            {"source_dignity": -5.0, "target_dignity": -5.0, "is_event": 1},   # 1-8
            {"source_dignity": 3.0,  "target_dignity": 0.0,  "is_event": 1},   # 2-6
            {"source_dignity": 3.0,  "target_dignity": 0.0,  "is_event": 0},   # 2-6
            {"source_dignity": 0.0,  "target_dignity": 0.0,  "is_event": 1},   # 3-11
        ]
        result = cm._compute_axis_metrics(rows)
        assert "1-8" in result and result["1-8"].tp == 1
        assert "2-6" in result and result["2-6"].tp == 1 and result["2-6"].fp == 1
        assert "3-11" in result and result["3-11"].tp == 1


# ---------------------------------------------------------------------------
# _derive_recommendations: verifies real data changes thresholds
# ---------------------------------------------------------------------------
class TestDeriveRecommendations:

    def _module(self):
        cm = object.__new__(CalibrationModule)
        cm.db_path = ":memory:"
        cm._conn = None
        return cm

    def test_empty_axis_metrics_returns_default_note(self):
        cm = self._module()
        recs = cm._derive_recommendations({}, {})
        assert "No dignity data" in recs["aspect_evaluator"]["note"]

    def test_high_takkar_precision_lowers_low_threshold(self):
        """If Takkar axis precision > 0.75 with n>50, LOW_THRESHOLD should be raised."""
        cm = self._module()
        axis_metrics = {"1-8": AxisMetrics(axis="1-8", tp=80, fp=20)}  # precision=0.80, n=100
        recs = cm._derive_recommendations({}, axis_metrics)
        assert recs["aspect_evaluator"]["low_threshold"] == pytest.approx(-1.5)

    def test_low_takkar_precision_tightens_low_threshold(self):
        """If Takkar axis precision < 0.40 with n>50, LOW_THRESHOLD should be lowered."""
        cm = self._module()
        axis_metrics = {"1-8": AxisMetrics(axis="1-8", tp=30, fp=70)}  # precision=0.30, n=100
        recs = cm._derive_recommendations({}, axis_metrics)
        assert recs["aspect_evaluator"]["low_threshold"] == pytest.approx(-2.5)

    def test_high_gali_precision_lowers_high_threshold(self):
        """If Gali Sweet Spot precision > 0.85 with n>50, HIGH_THRESHOLD should be lowered."""
        cm = self._module()
        axis_metrics = {"2-6": AxisMetrics(axis="2-6", tp=90, fp=10)}  # precision=0.90, n=100
        recs = cm._derive_recommendations({}, axis_metrics)
        assert recs["aspect_evaluator"]["high_threshold"] == pytest.approx(2.0)

    def test_axes_used_reported(self):
        cm = self._module()
        axis_metrics = {
            "1-8": AxisMetrics(axis="1-8", tp=10, fp=5),
            "2-6": AxisMetrics(axis="2-6", tp=20, fp=10),
        }
        recs = cm._derive_recommendations({}, axis_metrics)
        assert recs["aspect_evaluator"]["axes_used"] == ["1-8", "2-6"]

    def test_timing_engine_thresholds_always_present(self):
        cm = self._module()
        recs = cm._derive_recommendations({}, {})
        te = recs["timing_engine"]
        assert "rashi_phal_medium_threshold" in te
        assert "graha_phal_high_threshold" in te


# ---------------------------------------------------------------------------
# End-to-end calibration run against real DB (skipped if DB has no dignity data)
# ---------------------------------------------------------------------------
class TestCalibrationEndToEnd:

    def test_calibrate_with_real_db(self):
        import os
        db_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "public_figures.db"
        )
        if not os.path.exists(db_path):
            pytest.skip("public_figures.db not available")

        cm = CalibrationModule(db_path)
        result = cm.calibrate()

        # domain_metrics populated from engine_metrics table (10 rows)
        assert isinstance(result.domain_metrics, dict)

        # axis_metrics may be empty if dignity columns not populated yet
        # — but must be a dict (not None, not a stub "Low")
        assert isinstance(result.axis_metrics, dict)

        # recommended_thresholds must always have all three keys
        assert "fidelity_gate" in result.recommended_thresholds
        assert "aspect_evaluator" in result.recommended_thresholds
        assert "timing_engine" in result.recommended_thresholds

        # aspect_evaluator must always have a 'note' (not silently empty)
        note = result.recommended_thresholds["aspect_evaluator"].get("note", "")
        assert len(note) > 0, "aspect_evaluator.note must not be empty"

        # Print report must not crash
        report = cm.print_report(result)
        assert "CALIBRATION REPORT" in report
