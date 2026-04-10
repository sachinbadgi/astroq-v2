"""
Phase 2 Tests: Validator Agent (AutoResearch 2.0)

Tests for: ValidatorAgent.compare_to_events, hit_rate, mean_offset, contradiction detection.
"""

import pytest
from astroq.lk_prediction.data_contracts import LKPrediction, LifeEvent, GapReport
from astroq.lk_prediction.lse_validator import ValidatorAgent


@pytest.fixture
def validator():
    return ValidatorAgent()


def _make_lk(age: int, domain: str, text: str = "Event text") -> LKPrediction:
    return LKPrediction(
        domain=domain,
        event_type="test",
        prediction_text=text,
        confidence="possible",
        polarity="benefic",
        peak_age=age,
        probability=0.8
    )


def _make_le(age: int, domain: str) -> LifeEvent:
    return {
        "age": age,
        "domain": domain,
        "description": f"Known {domain} event",
        "is_verified": True
    }


# --------------------------------------------------------------------------
# Test 1: Exact Hit (offset=0)
# --------------------------------------------------------------------------

def test_validator_exact_hit(validator):
    predictions = [_make_lk(24, "profession")]
    life_events = [_make_le(24, "profession")]
    
    report = validator.compare_to_events(predictions, life_events)
    
    assert report["total"] == 1
    assert report["hits"] == 1
    assert report["hit_rate"] == 1.0
    assert report["mean_offset"] == 0.0
    assert report["entries"][0]["is_hit"] is True
    assert report["entries"][0]["offset"] == 0.0


# --------------------------------------------------------------------------
# Test 2: Near Hit (offset=1.0)
# --------------------------------------------------------------------------

def test_validator_near_hit(validator):
    predictions = [_make_lk(25, "profession")]
    life_events = [_make_le(24, "profession")]
    
    report = validator.compare_to_events(predictions, life_events)
    
    assert report["hits"] == 1
    assert report["entries"][0]["is_hit"] is True
    assert report["entries"][0]["offset"] == 1.0
    assert report["mean_offset"] == 1.0


# --------------------------------------------------------------------------
# Test 3: Miss (offset=2.0)
# --------------------------------------------------------------------------

def test_validator_miss(validator):
    """Offset of 3.0 years is a miss (> 2 year window)."""
    predictions = [_make_lk(27, "profession")]
    life_events = [_make_le(24, "profession")]
    
    report = validator.compare_to_events(predictions, life_events)
    
    assert report["hits"] == 0
    assert report["entries"][0]["is_hit"] is False
    assert report["entries"][0]["offset"] == 3.0


# --------------------------------------------------------------------------
# Test 4: Multiple events matching nearest prediction
# --------------------------------------------------------------------------

def test_validator_multiple_events(validator):
    predictions = [
        _make_lk(22, "profession"),
        _make_lk(35, "health")
    ]
    life_events = [
        _make_le(24, "profession"),
        _make_le(35, "health")
    ]
    
    report = validator.compare_to_events(predictions, life_events)
    
    assert report["total"] == 2
    # Profession: age 22 vs 24 = offset -2.0 (hit with <=2 window)
    # Health: age 35 vs 35 = offset 0.0 (hit)
    assert report["hits"] == 2
    assert report["hit_rate"] == 1.0
    assert report["mean_offset"] == 1.0  # (abs(-2) + abs(0)) / 2


# --------------------------------------------------------------------------
# Test 5: Contradiction Detection (event with no domain match)
# --------------------------------------------------------------------------

def test_validator_contradiction(validator):
    predictions = [_make_lk(20, "education")]
    life_events = [_make_le(25, "profession")]
    
    report = validator.compare_to_events(predictions, life_events)
    
    assert report["total"] == 1
    assert report["hits"] == 0
    # 'profession' normalises to 'career'; contradiction key is canonical 'career'
    assert "career" in report["contradictions"]
    assert report["entries"][0]["predicted_peak_age"] is None


# --------------------------------------------------------------------------
# Test 6: Empty events returns default report
# --------------------------------------------------------------------------

def test_validator_empty_events(validator):
    predictions = [_make_lk(20, "education")]
    report = validator.compare_to_events(predictions, [])
    
    assert report["total"] == 0
    assert report["hit_rate"] == 0.0
    assert report["entries"] == []


# --------------------------------------------------------------------------
# Test 7: Matching logic chooses nearest prediction for domain
# --------------------------------------------------------------------------

def test_validator_nearest_match(validator):
    predictions = [
        _make_lk(18, "profession", "Too early"),
        _make_lk(23, "profession", "Near one"),
        _make_lk(30, "profession", "Too late")
    ]
    life_event = _make_le(24, "profession")
    
    report = validator.compare_to_events(predictions, [life_event])
    
    # 23 vs 24 is the nearest (offset -1.0)
    assert report["entries"][0]["predicted_peak_age"] == 23
    assert report["entries"][0]["offset"] == -1.0
    assert report["entries"][0]["is_hit"] is True


# --------------------------------------------------------------------------
# Test 8: Domain alias — "profession" event matches "career" prediction
# --------------------------------------------------------------------------

def test_validator_profession_matches_career_alias(validator):
    """
    Event domain='profession' normalises to 'career'.
    Prediction domain='career' also normalises to 'career'.
    With matching age, result must be a hit.
    """
    predictions = [_make_lk(36, "career")]
    life_events = [_make_le(36, "profession")]

    report = validator.compare_to_events(predictions, life_events)

    assert report["hits"] == 1
    assert report["hit_rate"] == 1.0
    assert report["entries"][0]["is_hit"] is True
    assert report["entries"][0]["offset"] == 0.0


# --------------------------------------------------------------------------
# Test 9: "General" domain prediction does NOT match "career" event
# --------------------------------------------------------------------------

def test_validator_general_domain_contradiction(validator):
    """
    Predictions tagged 'General' must NOT match a typed event domain
    such as 'career'. The event should appear as a contradiction.
    """
    predictions = [_make_lk(36, "General")]
    life_events = [_make_le(36, "career")]

    report = validator.compare_to_events(predictions, life_events)

    assert report["hits"] == 0
    assert report["entries"][0]["predicted_peak_age"] is None
    assert "career" in report["contradictions"]


# --------------------------------------------------------------------------
# Test 10: Hit window is <= 2 years
# --------------------------------------------------------------------------

def test_validator_hit_window_two_years(validator):
    """Offset of exactly 2.0 years should still be a hit."""
    predictions = [_make_lk(26, "career")]
    life_events = [_make_le(24, "career")]

    report = validator.compare_to_events(predictions, life_events)

    assert report["hits"] == 1
    assert report["entries"][0]["is_hit"] is True
    assert report["entries"][0]["offset"] == 2.0


def test_validator_miss_beyond_two_years(validator):
    """Offset of 3 years must be a miss."""
    predictions = [_make_lk(27, "career")]
    life_events = [_make_le(24, "career")]

    report = validator.compare_to_events(predictions, life_events)

    assert report["hits"] == 0
    assert report["entries"][0]["is_hit"] is False
