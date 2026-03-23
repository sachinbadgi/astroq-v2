import json
import asyncio
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import google.generativeai as genai
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
DB_PATH = "d:/astroq-v2/backend/data/api_config.db"
DEFAULTS_PATH = "d:/astroq-v2/backend/data/model_defaults.json"
config = ModelConfig(db_path=DB_PATH, defaults_path=DEFAULTS_PATH)
pipeline = LKPredictionPipeline(config)

from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.benchmark_runner import BenchmarkRunner

# Paths for benchmark data
BENCH_DIR = "d:/astroq-v2/backend"
GT_FILE = "d:/astroq-v2/backend/data/public_figures_ground_truth.json"

# Initialize Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
llm_model = genai.GenerativeModel("gemini-1.5-flash")

# In-memory store for charts (mock database)
charts_db = {}
state = {"next_id": 1}

# Initialize Chart Generator and Benchmark Runner
chart_generator = ChartGenerator()
benchmark_runner = BenchmarkRunner(config, BENCH_DIR)

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
    return [
        {"id": cid, "client_name": cdata["name"], "birth_date": cdata["dob"]}
        for cid, cdata in charts_db.items()
    ]

@app.post("/lal-kitab/generate-birth-chart")
async def generate_chart(req: GenerateChartRequest):
    chart_id = state["next_id"]
    state["next_id"] += 1
    
    try:
        payload = chart_generator.build_full_chart_payload(
            dob_str=req.dob,
            tob_str=req.tob,
            place_name=req.pob,
            latitude=req.lat,
            longitude=req.lon,
            chart_system=req.chart_system or "kp"
        )
        # Enrich all charts in the payload with aspects and grammar
        for key in payload:
            if key.startswith("chart_"):
                chart = payload[key]
                # We need an enriched dict for GrammarAnalyser
                # This is a lightweight enrichment just for aspects/grammar
                enriched = {p: {"house": d["house"]} for p, d in chart["planets_in_houses"].items()}
                pipeline.grammar_analyser.apply_grammar_rules(chart, enriched)
                
                # Merge enriched data back into the payload
                for p, ep in enriched.items():
                    if p not in chart["planets_in_houses"]:
                        chart["planets_in_houses"][p] = ep
                    else:
                        chart["planets_in_houses"][p].update(ep)

        natal_chart = payload["chart_0"]
        
        chart_payload = {
            "id": chart_id,
            "name": req.name,
            "dob": req.dob,
            "tob": req.tob,
            "pob": req.pob,
            "planets_in_houses": natal_chart["planets_in_houses"],
            "full_payload": payload # Include full payload for year switching
        }
        charts_db[chart_id] = chart_payload
        return chart_payload
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

@app.api_route("/lal-kitab/birth-charts/{chart_id}", methods=["GET", "DELETE"])
async def handle_chart_item(chart_id: int, request: Request):
    if chart_id not in charts_db:
        raise HTTPException(status_code=404, detail="Chart not found")

    if request.method == "DELETE":
        print(f"DEBUG: Deleting chart {chart_id}")
        del charts_db[chart_id]
        print(f"DEBUG: Chart {chart_id} deleted. Remaining: {len(charts_db)}")
        return {"message": "Chart deleted successfully"}

    # GET logic
    chart = charts_db[chart_id]
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

@app.post("/ask-chart")
async def ask_chart(req: AskChartRequest):
    prompt = f"""
    You are an expert Lal Kitab Astrologer (Oracle). 
    A user is asking: "{req.question}"
    
    Their chart data (planets in houses):
    {json.dumps(req.chart_data.get('planets_in_houses', {}), indent=2)}
    
    Provide a concise, mystical, and accurate answer based on Lal Kitab principles. 
    Focus on the specific question.
    """
    try:
        response = llm_model.generate_content(prompt)
        return {"answer": response.text}
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
            await asyncio.sleep(1.5)
            
        # Final conclusion from Gemini
        prompt = f"""
        You are a Premium Lal Kitab Oracle. 
        User Question: "{req.question}"
        Current Age: {req.current_age or 'Unknown'}
        
        Chart: {json.dumps(req.chart_data.get('planets_in_houses', {}))}
        
        Give a deep, insightful synthesis and final conclusion.
        """
        try:
            response = llm_model.generate_content(prompt)
            yield f"data: {json.dumps({'step': 'CONCLUDE', 'content': response.text})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'step': 'CONCLUDE', 'content': f'Error consulting the stars: {str(e)}'})}\n\n"
            
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
async def get_test_runs():
    try:
        with open(GT_FILE, "r", encoding="utf-8") as f:
            figures = json.load(f)
        
        # Limit to first few for speed if needed, but let's try all
        metrics = benchmark_runner.run_all(figures[:5]) 
        
        runs = []
        for name, res in metrics.results_by_figure.items():
            for ev in res["events_eval"]:
                runs.append({
                    "id": f"{name}_{ev['actual_age']}",
                    "public_figure": name,
                    "event": ev["event"],
                    "actual_age": ev["actual_age"],
                    "predicted_age": ev["predicted_age"],
                    "status": "HIT" if ev["hit"] else "MISS" if ev["offset"] > 5 else "PARTIAL"
                })
        
        return {
            "runs": runs,
            "metrics": {
                "hit_rate": f"{round(metrics.get_hit_rate() * 100, 1)}%",
                "avg_offset": f"+{round(metrics.get_avg_offset(), 1)} yrs",
                "total_tested": metrics.total_events
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
