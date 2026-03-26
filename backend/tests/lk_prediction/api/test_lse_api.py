import json
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from astroq.lk_prediction.api.server import app

@pytest.fixture
def client():
    return TestClient(app)


def test_lse_solve_api_success(client):
    """Test successful LSE solve request."""
    # Mock data
    payload = {
        "birth_chart": {"planets_in_houses": {"Sun": {"house": 1}}},
        "annual_charts": {"24": {"planets_in_houses": {}}},
        "life_events": [
            {"age": 24, "domain": "profession", "description": "Job"}
        ],
        "figure_id": "test_user_123"
    }
    
    # Mock result using real dataclasses
    from astroq.lk_prediction.data_contracts import LSESolveResult, ChartDNA, LSEPrediction
    
    dna = ChartDNA(
        figure_id="test_user_123",
        back_test_hit_rate=1.0,
        mean_offset_years=0.0,
        iterations_run=1,
        delay_constants={"delay.sun_h1": 2.0},
        confidence_score=0.95
    )
    
    pred = LSEPrediction(
        domain="profession",
        event_type="test",
        prediction_text="Career success",
        confidence="possible",
        polarity="benefic",
        peak_age=24,
        probability=0.8,
        personalised=True,
        chart_dna_applied=dna,
        raw_peak_age=22,
        adjusted_peak_age=24.0,
        confidence_source="back_test_100pct"
    )
    
    mock_result = LSESolveResult(
        chart_dna=dna,
        future_predictions=[pred],
        iterations_run=1,
        converged=True
    )
    
    with patch("astroq.lk_prediction.api.lse_routes.LSEOrchestrator") as MockOrch:
        instance = MockOrch.return_value
        instance.solve_chart.return_value = mock_result
        
        response = client.post(
            "/api/lk/lse/solve",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["converged"] is True
        assert data["chart_dna"]["figure_id"] == "test_user_123"
        assert len(data["future_predictions"]) == 1


def test_lse_solve_api_missing_fields(client):
    """Test 400 on missing required fields."""
    response = client.post(
        "/api/lk/lse/solve",
        json={"figure_id": "test"}
    )
    assert response.status_code == 422 # FastAPI returns 422 for pydantic validation error


def test_lse_solve_api_invalid_json(client):
    """Test 422 on invalid JSON (FastAPI/Pydantic)."""
    response = client.post(
        "/api/lk/lse/solve",
        content="not json",
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 400 or response.status_code == 422
