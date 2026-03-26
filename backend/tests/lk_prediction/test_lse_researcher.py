"""
Phase 3 Tests (Enhanced): Researcher Agent (AutoResearch 2.0)

Tests for rationale-based hypothesis generation.
"""

import pytest
from unittest.mock import MagicMock
from astroq.lk_prediction.lse_researcher import ResearcherAgent, Hypothesis
from astroq.lk_prediction.data_contracts import ChartData, GapReport, RuleHit


@pytest.fixture
def researcher():
    return ResearcherAgent()


# --------------------------------------------------------------------------
# Test 1: Takrav Rationale (Sun H1 vs Saturn H7)
# --------------------------------------------------------------------------

def test_researcher_takrav_rationale(researcher):
    gap_report: GapReport = {
        "entries": [{
            "life_event": {"age": 26, "domain": "profession"},
            "predicted_peak_age": 22,
            "is_hit": False,
        }],
        "contradictions": []
    }
    
    # Chart with Sun H1 and Saturn H7 (Takrav)
    birth_chart: ChartData = {
        "planets_in_houses": {
            "Sun": {"house": 1},
            "Saturn": {"house": 7}
        }
    }
    
    hypotheses = researcher.generate_hypotheses(gap_report, birth_chart)
    
    assert len(hypotheses) > 0
    h = hypotheses[0]
    assert h["type"] == "Delay"
    assert h["value"] == 4.5
    assert "Takrav" in h["rationale"]
    assert "sun" in h["key"].lower()


# --------------------------------------------------------------------------
# Test 2: Mars H8 Badh Rationale
# --------------------------------------------------------------------------

def test_researcher_mars_h8_rationale(researcher):
    gap_report: GapReport = {
        "entries": [{
            "life_event": {"age": 25, "domain": "profession"},
            "predicted_peak_age": 22.5,
            "is_hit": False,
        }],
        "contradictions": []
    }
    
    # Chart with Sun H1 and Mars H8
    birth_chart: ChartData = {
        "planets_in_houses": {
            "Sun": {"house": 1},
            "Mars": {"house": 8}
        }
    }
    
    hypotheses = researcher.generate_hypotheses(gap_report, birth_chart)
    
    assert len(hypotheses) > 0
    assert any("Mars H8" in h["rationale"] for h in hypotheses)
    assert any(h["value"] == 2.5 for h in hypotheses)


# --------------------------------------------------------------------------
# Test 3: Soya Ghar Lord Malefic Rationale
# --------------------------------------------------------------------------

def test_researcher_soya_ghar_malefic_rationale(researcher):
    gap_report: GapReport = {
        "entries": [{
            "life_event": {"age": 42, "domain": "profession"},
            "predicted_peak_age": 36,
            "is_hit": False,
        }],
        "contradictions": []
    }
    
    # H10 sleeping, lord Saturn in H8 (malefic)
    birth_chart: ChartData = {
        "planets_in_houses": {
            "Saturn": {"house": 8}
        },
        "house_status": {"10": "Sleeping House"}
    }
    
    hypotheses = researcher.generate_hypotheses(gap_report, birth_chart)
    
    assert any("Soya Ghar" in h["rationale"] for h in hypotheses)
    assert any(h["value"] == 6.0 for h in hypotheses)


# --------------------------------------------------------------------------
# Test 4: Guru-Chandal Rationale (Jup + Rahu)
# --------------------------------------------------------------------------

def test_researcher_guru_chandal_rationale(researcher):
    gap_report: GapReport = {
        "entries": [{
            "life_event": {"age": 21, "domain": "profession"},
            "predicted_peak_age": 16,
            "is_hit": False,
        }],
        "contradictions": []
    }
    
    # Jupiter and Rahu in the same house
    birth_chart: ChartData = {
        "planets_in_houses": {
            "Jupiter": {"house": 2},
            "Rahu": {"house": 2}
        }
    }
    
    hypotheses = researcher.generate_hypotheses(gap_report, birth_chart)
    
    assert any("Guru-Chandal" in h["rationale"] for h in hypotheses)
    assert any(h["value"] == 5.0 for h in hypotheses)


# --------------------------------------------------------------------------
# Test 5: No Rationale -> No Delay Hypothesis
# --------------------------------------------------------------------------

def test_researcher_no_rationale_no_hypothesis(researcher):
    gap_report: GapReport = {
        "entries": [{
            "life_event": {"age": 30, "domain": "profession"},
            "predicted_peak_age": 25,
            "is_hit": False,
        }],
        "contradictions": []
    }
    
    # Clean chart (no Takrav, no Badh)
    birth_chart: ChartData = {
        "planets_in_houses": {
            "Sun": {"house": 12},
            "Jupiter": {"house": 11}
        }
    }
    
    hypotheses = researcher.generate_hypotheses(gap_report, birth_chart)
    
    # Since no rationale is found, no delay hypothesis should be generated
    # instead of just guessing offset.
    assert len([h for h in hypotheses if h["type"] == "Delay"]) == 0
