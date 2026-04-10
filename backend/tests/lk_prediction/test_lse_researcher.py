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
    """
    Takrav at age=36 (Sun H1 vs Saturn H7): alignment=36 is within ±2yr → Alignment type.
    """
    gap_report: GapReport = {
        "entries": [{
            "life_event": {"age": 36, "domain": "profession"},
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
    assert h["type"] == "Alignment"
    assert h["value"] == 36
    assert "Takrav" in h["rationale"]
    assert "sun" in h["key"].lower()


# --------------------------------------------------------------------------
# Test 2: Mars H8 Badh Rationale
# --------------------------------------------------------------------------

def test_researcher_mars_h8_rationale(researcher):
    """
    Mars H8 vs Sun H1 clash: when actual_age (28) is near Mars maturity (28),
    alignment to 28 is generated.
    """
    gap_report: GapReport = {
        "entries": [{
            "life_event": {"age": 28, "domain": "profession"},
            "predicted_peak_age": 22,
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
    # |28-28| < |22-28| → alignment=28 should be returned
    assert any(h["value"] == 28 for h in hypotheses)


# --------------------------------------------------------------------------
# Test 3: Soya Ghar Lord Malefic Rationale
# --------------------------------------------------------------------------

def test_researcher_soya_ghar_malefic_rationale(researcher):
    """
    Soya Ghar (H10 sleeping) with Saturn H8: alignment=36 with actual_age=36 → Alignment.
    """
    gap_report: GapReport = {
        "entries": [{
            "life_event": {"age": 36, "domain": "profession"},
            "predicted_peak_age": 22,
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
    assert any(h["value"] == 36 for h in hypotheses)


# --------------------------------------------------------------------------
# Test 4: Guru-Chandal Rationale (Jup + Rahu)
# --------------------------------------------------------------------------

def test_researcher_guru_chandal_rationale(researcher):
    """
    Jupiter+Rahu in same house: alignment=42 with actual_age=42 → Alignment at Rahu maturity.
    """
    gap_report: GapReport = {
        "entries": [{
            "life_event": {"age": 42, "domain": "profession"},
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
    assert any(h["value"] == 42 for h in hypotheses)


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
    
    # Since no rationale is found, no alignment hypothesis should be generated
    assert len([h for h in hypotheses if h["type"] == "Alignment"]) == 0


# --------------------------------------------------------------------------
# Test 6: Career contradiction → routes through H10 (DOMAIN_HOUSE_MAP)
# --------------------------------------------------------------------------

def test_researcher_career_contradiction_routes_h10(researcher):
    """
    When a 'career' contradiction exists (no matching prediction domain),
    the researcher should look at H10 planets and generate a delay hypothesis.
    """
    gap_report: GapReport = {
        "entries": [],
        "contradictions": ["career"]
    }
    birth_chart: ChartData = {
        "planets_in_houses": {
            "Saturn": {"house": 10},
            "Sun":    {"house": 1},
        }
    }

    hypotheses = researcher.generate_hypotheses(gap_report, birth_chart)

    # Saturn sits in H10 (primary house for career) → delay.saturn_h10
    keys = [h["key"] for h in hypotheses]
    assert any("saturn_h10" in k for k in keys), f"Expected saturn_h10 hypothesis, got: {keys}"
    h = next(h for h in hypotheses if "saturn_h10" in h["key"])
    assert h["type"] == "Delay"
    assert h["target_age"] == 36   # Saturn canonical maturity


# --------------------------------------------------------------------------
# Test 7: Health contradiction → routes through H1, then H6, H8
# --------------------------------------------------------------------------

def test_researcher_health_contradiction_routes_h1(researcher):
    """
    'health' contradiction should generate hypotheses for planets in H1, H6, H8.
    """
    gap_report: GapReport = {
        "entries": [],
        "contradictions": ["health"]
    }
    birth_chart: ChartData = {
        "planets_in_houses": {
            "Mars": {"house": 1},
        }
    }

    hypotheses = researcher.generate_hypotheses(gap_report, birth_chart)

    keys = [h["key"] for h in hypotheses]
    assert any("mars_h1" in k for k in keys), f"Expected mars_h1 hypothesis, got: {keys}"


# --------------------------------------------------------------------------
# Test 8: "profession" contradiction is alias-resolved to "career" → H10
# --------------------------------------------------------------------------

def test_researcher_profession_alias_resolves_to_career(researcher):
    """
    'profession' (alias for 'career') contradiction should still route
    through H10 via DOMAIN_ALIASES normalisation.
    """
    gap_report: GapReport = {
        "entries": [],
        "contradictions": ["profession"]
    }
    birth_chart: ChartData = {
        "planets_in_houses": {
            "Jupiter": {"house": 10},
        }
    }

    hypotheses = researcher.generate_hypotheses(gap_report, birth_chart)

    keys = [h["key"] for h in hypotheses]
    assert any("jupiter_h10" in k for k in keys), f"Expected jupiter_h10 hypothesis, got: {keys}"
