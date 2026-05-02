import pytest
import json
import os
from unittest.mock import MagicMock
from astroq.lk_prediction.data_contracts import RuleHit, LKPrediction
from astroq.lk_prediction.contextual_assembler import ContextualAssembler
from astroq.lk_prediction.state_ledger import StateLedger

@pytest.fixture
def assembler():
    return ContextualAssembler()

@pytest.fixture
def ledger():
    return StateLedger()

def test_gravity_sorting(assembler):
    # Mock two RuleHits
    hit_low = RuleHit(
        rule_id="general_gain",
        domain="Money",
        description="Minor gain",
        verdict="Benefic",
        magnitude=0.5,
        scoring_type="boost"
    )
    hit_high = RuleHit(
        rule_id="health_strike",
        domain="Health",
        description="Major hit",
        verdict="Malefic",
        magnitude=-2.0,
        scoring_type="penalty",
        target_houses=[1]
    )
    
    # We need a dummy state ledger for context
    mock_ledger = MagicMock()
    mock_ledger.get_planet_state.return_value.modifier = "Awake"
    mock_ledger.get_recoil_multiplier.return_value = 1.0
    
    predictions = assembler.assemble([hit_low, hit_high], chart={"chart_period": 30}, ledger=mock_ledger)
    
    # High gravity (Health) should be first
    assert predictions[0].domain == "Health"
    assert predictions[0].gravity_score > predictions[1].gravity_score

def test_hybrid_narrative_assembly(assembler):
    hit = RuleHit(
        rule_id="saturn_takkar",
        domain="Health",
        description="Saturn strikes H1",
        verdict="Malefic",
        magnitude=-1.5,
        scoring_type="penalty",
        primary_target_planets=["Saturn"],
        target_houses=[1]
    )
    
    mock_ledger = MagicMock()
    mock_ledger.get_planet_state.return_value.modifier = "Startled"
    mock_ledger.get_recoil_multiplier.return_value = 1.0
    
    predictions = assembler.assemble([hit], chart={"chart_period": 30}, ledger=mock_ledger)
    p = predictions[0]
    
    # Check for forensic proof and layman result
    assert "Saturn strikes H1" in p.forensic_proof
    assert "manifests as a sharp, sudden blow" in p.prediction_text
    assert "personal identity and health" in p.prediction_text

def test_recoil_multiplier_impact(assembler):
    hit = RuleHit(
        rule_id="saturn_strike",
        domain="General",
        description="Saturn hit",
        verdict="Malefic",
        magnitude=-1.0,
        scoring_type="penalty",
        primary_target_planets=["Saturn"]
    )
    
    # Ledger with active recoil
    mock_ledger = MagicMock()
    mock_ledger.get_planet_state.return_value.modifier = "Awake"
    mock_ledger.get_recoil_multiplier.return_value = 2.0
    
    predictions = assembler.assemble([hit], chart={"chart_period": 45}, ledger=mock_ledger)
    p = predictions[0]
    
    # Magnitude and Gravity should be affected by recoil (2x)
    # Base magnitude is -1.0, recoil is 2.0 -> final impact should reflect this
    assert p.visual_manifest["friction_intensity"] >= 1.0
