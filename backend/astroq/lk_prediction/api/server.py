import json
import asyncio
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import litellm
import os

from astroq.lk_prediction.pipeline import LKPredictionPipeline
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.data_contracts import ChartData

app = FastAPI(title="AstroQ v2 Backend API")

# Enable CORS for the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the pipeline with correct paths
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/api_config.db"))
DEFAULTS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/model_defaults.json"))
config = ModelConfig(db_path=DB_PATH, defaults_path=DEFAULTS_PATH)
pipeline = LKPredictionPipeline(config)

from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.benchmark_runner import BenchmarkRunner
from astroq.lk_prediction.api.lse_routes import lse_router
from astroq.lk_prediction.api.chart_store import ChartStore
from astroq.lk_prediction.api.tasks import broker, run_benchmark_task, cleanup_expired_charts

# Paths for benchmark data
BENCH_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
GT_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/public_figures_ground_truth.json"))

# Initialize LLM via LiteLLM
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "dummy_gemini_key")
os.environ["GEMINI_API_KEY"] = GEMINI_KEY # Ensure it's in env for litellm
LLM_MODEL = "gemini/gemini-1.5-flash"

# Persistent store for charts
CHART_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/charts.db"))
chart_store = ChartStore(CHART_DB_PATH)

# App Version for traceability
APP_VERSION = "2.1.0-NFR"

# Initialize Chart Generator and Benchmark Runner
chart_generator = ChartGenerator()
benchmark_runner = BenchmarkRunner(config, BENCH_DIR)

# Task storage (simple in-memory for demo)
task_results = {}

@app.on_event("startup")
async def startup_event():
    await broker.startup()
    # Trigger cleanup of expired charts on startup
    await cleanup_expired_charts.kiq(CHART_DB_PATH)

@app.on_event("shutdown")
async def shutdown_event():
    await broker.shutdown()

app.include_router(lse_router)

class LoginRequest(BaseModel):
    username: str
    password: str

class GenerateChartRequest(BaseModel):
    name: str
    dob: str
    tob: str
    pob: str
    lat: float
    lon: float
    gender: str
    chart_system: Optional[str] = "kp"
    chart_type: Optional[str] = "USER"

class AskChartRequest(BaseModel):
    question: str
    chart_data: Any
    current_age: Optional[int] = None
    calibrated_weights: Optional[Dict[str, float]] = None

@app.post("/login")
async def login(req: LoginRequest):
    if req.username == "admin" and req.password == "password":
        return {"access_token": "mock_token_123", "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/search-location")
async def search_location(req: Dict[str, str]):
    # Use real geocoder from chart_generator
    place = req.get("place_name", "")
    try:
        locations = chart_generator.geocode_place(place)
        if locations:
            return {"locations": locations}
    except Exception as e:
        pass
    
    # Fallback to general mock
    return {
        "locations": [
            {
                "display_name": f"{place} (Resolved)",
                "latitude": 28.6139,
                "longitude": 77.2090,
                "utc_offset": "+5.5",
                "timezone": "Asia/Kolkata"
            }
        ]
    }

@app.get("/lal-kitab/birth-charts")
async def list_charts():
    return chart_store.list_charts()

@app.post("/lal-kitab/generate-birth-chart")
async def generate_chart(req: GenerateChartRequest):
    try:
        payload = chart_generator.build_full_chart_payload(
            dob_str=req.dob,
            tob_str=req.tob,
            place_name=req.pob,
            latitude=req.lat,
            longitude=req.lon,
            chart_system=req.chart_system or "kp"
        )
        # Enrichment logic
        for key in payload:
            if key.startswith("chart_"):
                chart = payload[key]
                enriched = {p: {"house": d["house"]} for p, d in chart["planets_in_houses"].items()}
                pipeline.grammar_analyser.apply_grammar_rules(chart, enriched)
                for p, ep in enriched.items():
                    if p not in chart["planets_in_houses"]:
                        chart["planets_in_houses"][p] = ep
                    else:
                        chart["planets_in_houses"][p].update(ep)

        natal_chart = payload["chart_0"]
        chart_payload = {
            "name": req.name,
            "dob": req.dob,
            "tob": req.tob,
            "pob": req.pob,
            "planets_in_houses": natal_chart["planets_in_houses"],
            "full_payload": payload
        }
        chart_id = chart_store.save_chart(chart_payload, chart_type=req.chart_type or "USER")
        chart_payload["id"] = chart_id
        return chart_payload
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

@app.api_route("/lal-kitab/birth-charts/{chart_id}", methods=["GET", "DELETE"])
async def handle_chart_item(chart_id: int, request: Request):
    if request.method == "DELETE":
        success = chart_store.delete_chart(chart_id)
        if not success:
            raise HTTPException(status_code=404, detail="Chart not found")
        return {"message": "Chart deleted successfully"}

    # GET logic
    chart = chart_store.get_chart(chart_id)
    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    pipeline.load_natal_baseline(chart)
    predictions = pipeline.generate_predictions(chart)
    enriched_planets = pipeline._natal_baseline
    
    grammar_marks = [
        {"rule": "Dharmi Teva", "status": chart.get("dharmi_kundli_status", "Normal"), "score": 15 if chart.get("dharmi_kundli_status") == "Dharmi Teva" else 0, "impact": "Protective"},
        {"rule": "Mangal Badh", "status": chart.get("mangal_badh_status", "Inactive"), "score": -20 if chart.get("mangal_badh_status") == "Active" else 0, "impact": "Malefic"},
    ]
    for debt in chart.get("lal_kitab_debts", []):
        grammar_marks.append({"rule": debt, "status": "Active", "score": -10, "impact": "Karmic Debt"})
    
    return {
        **chart,
        "pipeline_output": {
            "predictions": [p.__dict__ if hasattr(p, '__dict__') else p for p in predictions],
            "enriched_planets": enriched_planets,
            "grammar_marks": grammar_marks
        }
    }

def _summarize_chart_for_llm(chart: Dict[str, Any]) -> str:
    """Generate a token-efficient summary of the chart."""
    planets = chart.get("planets_in_houses", {})
    summary_parts = []
    for p, data in planets.items():
        h = data.get("house")
        tags = data.get("grammar_tags", [])
        tag_str = f" ({', '.join(tags)})" if tags else ""
        summary_parts.append(f"{p} in H{h}{tag_str}")
    
    status_parts = []
    if chart.get("mangal_badh_status") == "Active": status_parts.append("Mangal Badh Active")
    if chart.get("dharmi_kundli_status") == "Dharmi Teva": status_parts.append("Dharmi Teva")
    
    return "Planets: " + "; ".join(summary_parts) + ". Status: " + ", ".join(status_parts)

@app.post("/ask-chart")
async def ask_chart(req: AskChartRequest):
    summary = _summarize_chart_for_llm(req.chart_data)
    prompt = f"""
    Expert Lal Kitab Oracle. 
    Question: "{req.question}"
    Simplified Chart: {summary}
    Provide a concise, mystical, and accurate answer.
    """
    try:
        response = litellm.completion(model=LLM_MODEL, messages=[{"role": "user", "content": prompt}])
        return {"answer": response.choices[0].message.content}
    except Exception as e:
        return {"answer": f"The cosmic energies are hazy: {str(e)}"}

@app.post("/ask-chart-premium/stream")
async def ask_chart_premium_stream(req: AskChartRequest):
    async def event_generator():
        steps = [
            ("ANALYZE", "Ingesting planetary positions and house strengths..."),
            ("ANALYZE", "Evaluating Lal Kitab grammar and planetary aspects..."),
            ("REASON", "Synthesizing annual chart transit impacts..."),
            ("REASON", "Calculating remedial shift potential..."),
        ]
        
        for step_type, content in steps:
            yield f"data: {json.dumps({'step': step_type, 'content': content})}\n\n"
            await asyncio.sleep(1.2)
            
        summary = _summarize_chart_for_llm(req.chart_data)
        prompt = f"""
        Premium Lal Kitab Oracle. 
        Question: "{req.question}"
        Age: {req.current_age or 'N/A'}
        Chart Summary: {summary}
        Deep, insightful synthesis and final conclusion.
        """
        try:
            response = litellm.completion(model=LLM_MODEL, messages=[{"role": "user", "content": prompt}])
            yield f"data: {json.dumps({'step': 'CONCLUDE', 'content': response.choices[0].message.content})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'step': 'CONCLUDE', 'content': f'Error: {str(e)}'})}\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/simulate-remedies")
async def simulate_remedies(req: Dict[str, Any]):
    chart_data = req.get("chart_data", {})
    proposed_shifts = req.get("proposed_shifts", {})
    current_age = req.get("current_age", 1)
    
    birth_chart = chart_data.get("chart_0")
    if not birth_chart:
        # Fallback if chart_data structure is different
        birth_chart = chart_data
        
    annual_charts = {
        int(k.split("_")[1]): v 
        for k, v in chart_data.items() 
        if k.startswith("chart_") and k != "chart_0"
    }
    
    applied_remedies = []
    for planet, val in proposed_shifts.items():
        # If val is -1 or explicit house, apply it across relevant years
        for age, ann_chart in annual_charts.items():
            if age < current_age:
                continue
            # Logic: If val is -1 (suggested by UI), we pick the best safe match for that age
            if val == -1:
                options = pipeline.remedy_engine.get_year_shifting_options(birth_chart, ann_chart, age)
                res = options.get(planet)
                if res and res.safe_matches:
                    applied_remedies.append({"planet": planet, "age": age, "is_safe": True})
            else:
                # Explicit house shift
                applied_remedies.append({"planet": planet, "age": age, "is_safe": True})

    # Analyze potential
    summaries = pipeline.remedy_engine.analyze_life_area_potential(
        birth_chart, annual_charts, applied_remedies, current_age=current_age
    )
    
    simulation_matrix = []
    for area, summary in summaries.items():
        # Scale for UI (0-100)
        baseline = min(100, int(summary.fixed_fate / max(1, len(annual_charts)) * 10))
        simulated = min(100, int((summary.fixed_fate + summary.current_remediation) / max(1, len(annual_charts)) * 10))
        simulation_matrix.append({
            "aspect": area,
            "baseline_health": baseline,
            "simulated_health": simulated,
            "delta": f"+{round(summary.remediation_efficiency, 1)}%"
        })
        
    # Lifetime projection
    projection = pipeline.remedy_engine.simulate_lifetime_strength(birth_chart, annual_charts, applied_remedies)
    timeline = []
    for i, age in enumerate(projection.ages):
        total_strength = sum(p_data["remedy"][i] for p_data in projection.planets.values())
        avg_strength = total_strength / max(1, len(projection.planets))
        timeline.append({
            "age": age,
            "probability": min(100, int(avg_strength * 10))
        })
        
    return {
        "simulation_matrix": simulation_matrix,
        "lifetime_timeline": timeline
    }

@app.get("/metrics/test-runs")
async def trigger_test_runs():
    try:
        with open(GT_FILE, "r", encoding="utf-8") as f:
            figures = json.load(f)
        
        # Limit to first few as before
        subset = figures[:5]
        
        # Trigger the task with metadata (Phase 7 traceability)
        task = await run_benchmark_task.kiq(
            config_params={"db_path": DB_PATH, "defaults_path": DEFAULTS_PATH},
            bench_dir=BENCH_DIR,
            figures=subset
        )
        
        # In a real setup, we would also log the task metadata to a 'benchmarks' table
        print(f"DEBUG: Triggered benchmark task {task.task_id} with app version {APP_VERSION}")
        
        return {"task_id": task.task_id, "message": "Benchmark started in background"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics/task-status/{task_id}")
async def get_task_status(task_id: str):
    # Actually, with InMemoryBroker, we can't easily poll from a separate process,
    # but since everything is in one process here, we can use the result backend 
    # if we configured one. For now, we'll wait for the task result in a simple way
    # or just assume the frontend will poll.
    
    # Using taskiq's built-in result polling (if backend exists)
    # Since we used InMemoryBroker without a backend, we'll mock it for now.
    # In a real Redis setup, this would be: await broker.result_backend.get_result(task_id)
    
    # For now, we'll just return a mock "COMPLETED" state with data if it was fast,
    # or "RUNNING" otherwise. This is a placeholder for the Redis implementation.
    return {"status": "SUCCESS", "message": "Task result polling requires Redis/RabbitMQ. Currently running in-process."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
