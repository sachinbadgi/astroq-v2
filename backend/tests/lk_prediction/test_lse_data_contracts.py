"""
Phase 1 Tests: LSE Data Types (AutoResearch 2.0)

Tests for: LifeEvent, GapEntry, GapReport, ChartDNA, LSEPrediction, LSESolveResult
"""

import pytest
from astroq.lk_prediction.data_contracts import (
    LKPrediction,
    LifeEvent,
    GapEntry,
    GapReport,
    ChartDNA,
    LSEPrediction,
    LSESolveResult,
)


# --------------------------------------------------------------------------
# Test 1: LifeEvent dict can be constructed and accessed
# --------------------------------------------------------------------------

def test_life_event_construction():
    ev: LifeEvent = {
        "age": 24,
        "domain": "profession",
        "description": "First job in finance",
        "is_verified": True,
    }
    assert ev["age"] == 24
    assert ev["domain"] == "profession"
    assert ev["is_verified"] is True


# --------------------------------------------------------------------------
# Test 2: GapReport has required keys
# --------------------------------------------------------------------------

def test_gap_report_fields():
    entry: GapEntry = {
        "life_event": {"age": 24, "domain": "profession"},
        "predicted_peak_age": 22,
        "offset": -2.0,
        "is_hit": False,
        "matched_prediction_text": "Career advancement expected",
    }
    report: GapReport = {
        "entries": [entry],
        "hit_rate": 0.0,
        "mean_offset": 2.0,
        "total": 1,
        "hits": 0,
        "contradictions": [],
    }
    assert report["hit_rate"] == 0.0
    assert report["total"] == 1
    assert report["hits"] == 0
    assert len(report["entries"]) == 1
    assert report["entries"][0]["is_hit"] is False


# --------------------------------------------------------------------------
# Test 3: ChartDNA construction and confidence formula
# --------------------------------------------------------------------------

def test_chart_dna_confidence_formula_perfect_hit():
    """100% hit rate + 0 offset + all verified = 1.0."""
    dna = ChartDNA(
        figure_id="test_figure",
        back_test_hit_rate=1.0,
        mean_offset_years=0.0,
        iterations_run=3,
    )
    score = dna.compute_confidence(verified_event_ratio=1.0)
    assert score == pytest.approx(1.0, abs=0.001)


def test_chart_dna_confidence_formula_partial():
    """Hit rate 0.75, offset 2yr, all verified."""
    dna = ChartDNA(
        figure_id="test_figure_2",
        back_test_hit_rate=0.75,
        mean_offset_years=2.0,
        iterations_run=10,
    )
    score = dna.compute_confidence(verified_event_ratio=1.0)
    # 0.75*0.70 + (1-2/5)*0.20 + 1.0*0.10 = 0.525 + 0.12 + 0.10 = 0.745
    assert score == pytest.approx(0.745, abs=0.001)


def test_chart_dna_delay_constants_default_empty():
    dna = ChartDNA(
        figure_id="f1", back_test_hit_rate=0.5, mean_offset_years=1.0, iterations_run=1
    )
    assert dna.delay_constants == {}
    assert dna.grammar_overrides == {}


# --------------------------------------------------------------------------
# Test 4: LSEPrediction.from_lk_prediction promotes correctly
# --------------------------------------------------------------------------

def _make_lk(peak_age=22, domain="profession") -> LKPrediction:
    return LKPrediction(
        domain=domain,
        event_type="career",
        prediction_text="Career event",
        confidence="possible",
        polarity="benefic",
        peak_age=peak_age,
        probability=0.75,
    )


def test_lse_prediction_from_lk_no_dna():
    lk = _make_lk(peak_age=22)
    lse = LSEPrediction.from_lk_prediction(lk, dna=None, delay=0.0)
    assert lse.personalised is False
    assert lse.confidence_source == "generic"
    assert lse.raw_peak_age == 22
    assert lse.adjusted_peak_age == 22.0
    assert lse.peak_age == 22


def test_lse_prediction_from_lk_with_delay():
    lk = _make_lk(peak_age=22)
    dna = ChartDNA(
        figure_id="fig1", back_test_hit_rate=1.0, mean_offset_years=0.0, iterations_run=5,
        delay_constants={"delay.mars_h8": 2.5}
    )
    lse = LSEPrediction.from_lk_prediction(lk, dna=dna, delay=2.5)
    assert lse.personalised is True
    assert lse.raw_peak_age == 22
    assert lse.adjusted_peak_age == pytest.approx(24.5)
    assert lse.peak_age == 24       # int(24.5)
    assert lse.confidence_source == "back_test_100pct"


def test_lse_prediction_partial_hit_rate():
    lk = _make_lk(peak_age=30)
    dna = ChartDNA(
        figure_id="fig2", back_test_hit_rate=0.75, mean_offset_years=1.5, iterations_run=8
    )
    lse = LSEPrediction.from_lk_prediction(lk, dna=dna, delay=0.0)
    assert lse.confidence_source == "back_test_partial"


# --------------------------------------------------------------------------
# Test 5: LSESolveResult defaults
# --------------------------------------------------------------------------

def test_lse_solve_result_defaults():
    dna = ChartDNA(figure_id="f", back_test_hit_rate=0.0, mean_offset_years=0.0, iterations_run=0)
    result = LSESolveResult(chart_dna=dna)
    assert result.converged is False
    assert result.iterations_run == 0
    assert result.future_predictions == []
