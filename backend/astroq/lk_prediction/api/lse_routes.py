"""
Phase 6: LSE API Routes (AutoResearch 2.0) - FastAPI version

APIRouter for AutoResearch 2.0 (LSE) solve operations.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from astroq.lk_prediction.lse_orchestrator import LSEOrchestrator
from astroq.lk_prediction.config import ModelConfig
import os

lse_router = APIRouter(prefix="/api/lk/lse", tags=["LSE"])

class LSESolveRequest(BaseModel):
    birth_chart: Dict[str, Any]
    annual_charts: Optional[Dict[str, Any]] = {}
    life_events: Optional[List[Dict[str, Any]]] = []
    figure_id: str

@lse_router.post("/solve")
async def solve_lse(req: LSESolveRequest):
    """
    POST /api/lk/lse/solve
    
    Inputs: birth_chart, annual_charts, life_events, figure_id
    Outputs: chart_dna, future_predictions, converged, iterations_run
    """
    # Convert annual_charts keys to int
    annual_charts = {}
    for age_str, chart in req.annual_charts.items():
        try:
            annual_charts[int(age_str)] = chart
        except ValueError:
            continue
            
    try:
        # Resolve paths relative to project root
        project_root = "d:/astroq-v2"
        db_path = os.path.join(project_root, "backend/data/api_config.db")
        defaults_path = os.path.join(project_root, "backend/data/model_defaults.json")
        
        # Load Config
        config = ModelConfig(db_path=db_path, defaults_path=defaults_path)
        orchestrator = LSEOrchestrator(config)
        
        result = orchestrator.solve_chart(
            birth_chart=req.birth_chart,
            annual_charts=annual_charts,
            life_event_log=req.life_events,
            figure_id=req.figure_id
        )
        
        # Format response
        def serialize_lse(obj, memo=None):
            if memo is None: memo = set()
            if id(obj) in memo: return "<Circular>"
            
            # Special check for Mocks in tests
            if "Mock" in type(obj).__name__:
                return str(obj)

            if hasattr(obj, "__dict__"):
                memo.add(id(obj))
                out = {}
                for k, v in obj.__dict__.items():
                    if k.startswith("_"): continue
                    out[k] = serialize_lse(getattr(obj, k), memo)
                return out
            elif isinstance(obj, (list, tuple)):
                return [serialize_lse(i, memo) for i in obj]
            elif isinstance(obj, dict):
                return {str(k): serialize_lse(v, memo) for k, v in obj.items()}
            return obj

        return serialize_lse(result)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
