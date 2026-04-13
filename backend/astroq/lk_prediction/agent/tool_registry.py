"""
MCP-Style Tool Registry for the Lal Kitab Agent.

Each tool is registered in TOOLS as:
  {
    "name": str,
    "description": str,           # shown to LLM for selection
    "parameters": {...},           # JSON Schema for LLM to fill
    "fn": Callable[[context, params], str]
  }

Tools read/write `context` dict (shared agent state for one turn).
"""

import os
import json
from typing import Dict, Any, List, Optional, Union

# Add backend to path for imports
import sys
_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.pipeline import LKPredictionPipeline
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.api.chart_store import ChartStore
from astroq.lk_prediction.data_contracts import LKPrediction, normalize_planets

CHART_DB_PATH = os.path.abspath(os.path.join(_BACKEND, "data/charts.db"))
RULES_DB_PATH = os.path.abspath(os.path.join(_BACKEND, "data/api_config.db"))
DEFAULTS_PATH = os.path.abspath(os.path.join(_BACKEND, "data/model_defaults.json"))

_chart_store = ChartStore(CHART_DB_PATH)
_chart_gen = ChartGenerator()
_cfg = ModelConfig(db_path=RULES_DB_PATH, defaults_path=DEFAULTS_PATH)
_pipeline = LKPredictionPipeline(_cfg)


# ─────────────────────────────────────────────
# Tool Implementations
# ─────────────────────────────────────────────

def _list_charts(context: Dict, params: Dict) -> str:
    """List all saved client charts from the DB."""
    charts = _chart_store.list_charts()
    if not charts:
        return "No charts saved in the database yet."
    lines = [f"ID {c['id']}: {c['client_name']} (DOB: {c['birth_date']})" for c in charts]
    return "Saved charts:\n" + "\n".join(lines)


def _get_natal_chart(context: Dict, params: Dict) -> str:
    """Load a natal chart by chart_id from SQLite OR local JSON and place in context."""
    user_id = context.get("user_id", "default")
    
    # 1. Local-First Strategy (matches lk_agent.py auto-load)
    local_payload_path = os.path.join(_BACKEND, f"{user_id}_gemini_payload.json")
    if os.path.exists(local_payload_path):
        try:
            with open(local_payload_path, 'r') as f:
                payload = json.load(f)
                natal = payload.get("natal_promise_baseline", {})
                planets = natal.get("planets_in_houses") or payload.get("chart_0")
                context["natal_chart"] = normalize_planets(planets or {})
                context["full_payload"] = payload
                context["client_name"] = payload.get("client_name", user_id)
                
                # Check for sibling predictions file for remedies
                pred_path = os.path.join(_BACKEND, f"{user_id}_predictions.json")
                if os.path.exists(pred_path):
                    with open(pred_path, 'r') as pf:
                        context["predictions_raw"] = json.load(pf)
                
                return f"Successfully loaded local Vedic charts for {context['client_name']}."
        except Exception as e:
            return f"Error loading local payload: {e}"

    # 2. Database Strategy
    raw_id = params.get("chart_id")
    try:
        chart_id = int(raw_id)
    except (ValueError, TypeError):
        return f"Error: Invalid chart_id '{raw_id}'. Must be an integer."
    
    chart = _chart_store.get_chart(chart_id)
    if not chart:
        return f"No chart found with id={chart_id}. Use list_charts to see available IDs."
    
    # Store in context for other tools to use
    raw_natal = chart["full_payload"].get("chart_0", {})
    context["natal_chart"] = normalize_planets(raw_natal)
    context["full_payload"] = chart["full_payload"]
    context["client_name"] = chart["name"]
    context["chart_id"] = chart_id
    
    return f"Loaded natal chart for {chart['name']} (DOB: {chart['dob']})."


def _generate_natal_chart(context: Dict, params: Dict) -> str:
    """Generate a new natal chart from birth details and save it to the DB."""
    name = params.get("name", context.get("user_id", "Client"))
    dob = params.get("dob")
    tob = params.get("tob")
    place = params.get("place")
    
    if not all([dob, tob, place]):
        return "Missing required birth details (dob, tob, or place)."
    chart_system = params.get("chart_system", "vedic")
    annual_basis = params.get("annual_basis", "vedic")

    payload = _chart_gen.build_full_chart_payload(
        dob_str=dob, tob_str=tob, place_name=place,
        chart_system=chart_system, annual_basis=annual_basis
    )
    natal = payload.get("chart_0", {})
    chart_record = {
        "name": name, "dob": dob, "tob": tob, "pob": place,
        "planets_in_houses": natal.get("planets_in_houses", {}),
        "full_payload": payload
    }
    chart_id = _chart_store.save_chart(chart_record)
    
    context["natal_chart"] = normalize_planets(natal)
    context["full_payload"] = payload
    context["client_name"] = name
    context["chart_id"] = chart_id
    context["chart_id"] = chart_id
    
    return f"Generated and saved natal chart for {name} (chart_id={chart_id})."


def _get_annual_charts(context: Dict, params: Dict) -> str:
    """Extract annual charts for a given age range from the full payload in context."""
    if "full_payload" not in context:
        return "No chart loaded. Use get_natal_chart or pick_local_payload first."
    
    age_from = int(params.get("age_from", 1))
    age_to = int(params.get("age_to", age_from))
    payload = context["full_payload"]
    
    found = {}
    
    # CASE 1: Timeline List Structure (annual_fulfillment_timeline)
    timeline = payload.get("annual_fulfillment_timeline", [])
    if timeline:
        for entry in timeline:
            age = entry.get("age")
            if age is not None and age_from <= age <= age_to:
                found[age] = entry
    
    # CASE 2: Flat Key Structure (chart_N)
    else:
        for age in range(age_from, age_to + 1):
            key = f"chart_{age}"
            if key in payload:
                found[age] = payload[key]
            
    if not found:
        return f"No annual charts found for ages {age_from}–{age_to}."
    
    if "annual_charts" not in context:
        context["annual_charts"] = {}
    context["annual_charts"].update(found)
    
    summary = {str(a): v.get("planets_in_houses", {}) for a, v in found.items()}
    return f"Loaded {len(found)} annual charts (ages {age_from}–{age_to})."


def _get_chart_object(payload: Dict, age: int, natal_chart: Optional[Dict] = None) -> Optional[Dict]:
    """Helper to resolve a chart object polymorphically across structures."""
    chart = None
    if age == 0:
        chart = natal_chart
    else:
        # 1. Timeline List Structure
        timeline = payload.get("annual_fulfillment_timeline", [])
        if timeline:
            for entry in timeline:
                if entry.get("age") == age:
                    chart = entry
                    break
        
        # 2. Flat Key Structure
        if not chart:
            chart = payload.get(f"chart_{age}")
            
    if chart:
        return chart
    return None


def _get_predictions(context: Dict, params: Dict) -> str:
    """Run LK predictions for a given age chart (or natal if age=0)."""
    if "natal_chart" not in context:
        return "No natal chart in context. Load one first."
    
    age = int(params.get("age", 0))
    payload = context.get("full_payload", {})
    natal_chart = context["natal_chart"]
    
    chart = _get_chart_object(payload, age, natal_chart)
    if not chart:
        return f"Chart for age {age} not found in current payload."

    _pipeline.load_natal_baseline(natal_chart)
    preds = _pipeline.generate_predictions(chart)
    
    # Retrieve Ground Truth Cycle Ruler from engine-populated chart
    ruler = chart.get("35_year_cycle_ruler", "Unknown")
    
    # --- STATISTICAL CORE INTEGRATION ---
    from astroq.lk_prediction.statistical_core import fuse_beliefs, apply_bayesian_prior
    
    # Apply Bayesian Prior from Chart DNA if available
    chart_dna = context.get("chart_dna", {})
    prior_weight = chart_dna.get("prediction_prior", 1.0)
    
    processed_preds = []
    for p in preds:
        if p.confidence == "UNLIKELY":
            continue
            
        # Adjust confidence/polarity based on Bayesian weight
        # (Simplified: in a real loop, we'd adjust the internal rule scores)
        
        processed_preds.append({
            "event": p.event_type,
            "domain": p.domain,
            "confidence": p.confidence,
            "text": p.prediction_text
        })
        
    context[f"predictions_age_{age}"] = processed_preds
    
    # --- DOSHA MAPPING (Enhancement for Golden Set) ---
    # Convert technical indicators into common "Dosha" terms for the LLM
    doshas = []
    rule_ids = [str(p.get("rule_id", "")) for p in processed_preds]
    if any("MANGAL" in r or "MARS_H2" in r or "MARS_H8" in r for r in rule_ids):
        doshas.append("Manglik Presence (Partial/Full)")
    if any("RAHU_SADHE" in r or "SAT_SADHE" in r for r in rule_ids):
        doshas.append("Sadhesati Influence")
    if any("PITRA" in r for r in rule_ids):
        doshas.append("Pitra Rin (Ancestral Debt)")
        
    summary = {
        "age": age,
        "cycle_ruler": ruler, # Injected context
        "predictions": [
            {
                "aphorism": p.get("text"),
                "domain": p.get("domain"),
                "status": _map_score_to_dignity(p.get("score", 0.5))
            } for p in processed_preds
        ],
        "detected_doshas": doshas
    }
    return f"Age {age} Predictions (Cycle Ruler: {ruler}):\n" + json.dumps(summary, indent=2)


def _map_score_to_dignity(score: float) -> str:
    """Translate numerical scores to simple layman-friendly labels."""
    if score > 0.85: return "Very Strong"
    if score > 0.65: return "Favorable"
    if score > 0.45: return "Neutral / Mixed"
    return "Challenged / Avoid"


def _get_domain_scores(context: Dict, params: Dict) -> str:
    """Get domain scores (marriage, career, health, etc.) for a specific age."""
    if "natal_chart" not in context:
        return "No natal chart in context. Load one first."
    
    age = int(params.get("age", 0))
    payload = context.get("full_payload", {})
    natal_chart = context["natal_chart"]
    
    chart = _get_chart_object(payload, age, natal_chart)
    if not chart:
        return f"Chart for age {age} not found in current payload."

    _pipeline.load_natal_baseline(context["natal_chart"])
    raw_scores = _pipeline.generate_domain_scores(chart)
    
    # --- SCHOLARLY DATA MAPPING ---
    resolved_scores = {}
    scholarly_view = {}
    for domain, score in raw_scores.items():
        # Map decimal to dignity label for the LLM
        dignity = _map_score_to_dignity(score)
        resolved_scores[domain] = score
        scholarly_view[domain] = dignity
    
    context[f"domain_scores_age_{age}"] = resolved_scores
    
    # Enrich with Cycle Ruler
    period = (age - 1) % 35 + 1
    ruler = "Saturn" if 1<=period<=6 else "Rahu" if 7<=period<=12 else "Ketu" if 13<=period<=15 else "Jupiter" if 16<=period<=21 else "Sun" if 22<=period<=23 else "Venus"
    
    view = {
        "age": age,
        "cycle_ruler": ruler,
        "status": scholarly_view
    }
    return f"Domain status for age {age}:\n" + json.dumps(view, indent=2)


def _get_remedies(context: Dict, params: Dict) -> str:
    """Extract remedy hints from predictions already in context."""
    age = int(params.get("age", 0))
    key = f"predictions_age_{age}"
    if key not in context:
        return f"No predictions for age {age} in context. Call get_predictions first."
    
    preds = context[key]
    remedies = [p for p in preds if getattr(p, "remedy_applicable", False)]
    
    if not remedies:
        return f"No specifically indicated remedies for age {age}."
        
    out = []
    for p in remedies:
        hint = p.remedy_hints[0] if p.remedy_hints else "No specific remedy provided."
        planet = p.source_planets[0] if p.source_planets else "General"
        out.append(f"- {p.event_type} ({planet}): {hint}")
        
    return f"Indicated remedies for age {age}:\n" + "\n".join(out)
 
 
def _get_highest_probability_ages(context: Dict, params: Dict) -> str:
    """Scan an age range to find the top 3 ages with highest probability for a domain."""
    if "full_payload" not in context:
        return "No chart loaded. Use get_natal_chart first."
    
    domain = params.get("domain", "Marriage")
    start_age = int(params.get("start_age", 20))
    end_age = int(params.get("end_age", 45))
    
    payload = context["full_payload"]
    _pipeline.load_natal_baseline(context["natal_chart"])
    
    # Normalization: map common business terms to JSON keys
    search_domain = domain
    if domain.lower() in ["business", "trade", "commerce"]:
        search_domain = "Career"
        
    results = []
    for age in range(start_age, end_age + 1):
        chart = _get_chart_object(payload, age, context.get("natal_chart"))
        if chart:
            # Use pipeline to get domain scores
            scores = _pipeline.generate_domain_scores(chart)
            # Domain specific score
            processed_score = scores.get(search_domain, scores.get(domain, 0))
            results.append({"age": age, "score": processed_score})
            
    if not results:
        return f"No data found for domain '{domain}' in the specified age range."
        
    # Sort and take top 3
    top_3 = sorted(results, key=lambda x: x["score"], reverse=True)[:3]
    
    # --- VOLATILITY SCANNER ---
    all_scores = [r["score"] for r in results]
    min_score = min(all_scores) if all_scores else 1.0
    max_score = max(all_scores) if all_scores else 0.0
    bottleneck_age = next((r["age"] for r in results if r["score"] == min_score), None)
    
    volations = []
    if min_score < 0.6:
        volations.append(f"CRITICAL BOTTLENECK DETECTED at Age {bottleneck_age} (Score: {min_score:.2f}). This year requires immediate remedial focus.")
    
    if max_score - min_score > 0.3:
        volations.append("HIGH VOLATILITY DETECTED: The range shows significant fluctuations. Do not smooth or average the data.")

    out = {
        "domain": domain,
        "scan_range": f"{start_age}-{end_age}",
        "top_peaks": top_3,
        "weakest_link": {"age": bottleneck_age, "score": min_score},
        "volatility_alerts": volations
    }
    
    return f"Analytical Range Scan for {domain}:\n" + json.dumps(out, indent=2)


def _get_domain_comparison(context: Dict, params: Dict) -> str:
    """Compare multiple domains at a specific age to determine relative strengths."""
    age = int(params.get("age", 0))
    domains = params.get("domains", ["Marriage", "Career", "Income", "Wealth", "Health"])
    
    # Internal call to get all scores
    scores_str = _get_domain_scores(context, {"age": age})
    if "Error" in scores_str:
        return scores_str
        
    resolved_scores = context.get(f"domain_scores_age_{age}", {})
    comparison = {d: resolved_scores.get(d, 0) for d in domains}
    
    # Sort for ranking
    ranked = sorted(comparison.items(), key=lambda x: x[1], reverse=True)
    
    return f"Domain Comparison for age {age}:\n" + json.dumps({
        "comparison": comparison,
        "ranking": [f"{i+1}. {d} ({s:.4f})" for i, (d, s) in enumerate(ranked)]
    }, indent=2)


def _get_lifecycle_status(context: Dict, params: Dict) -> str:
    """Get planetary maturity status and 35-year cycle ruler for a specific age."""
    age = int(params.get("age", 0))
    if age <= 0:
        return "Lifecycle status is only applicable for ages 1-120."
        
    payload = context.get("full_payload", {})
    natal_chart = context.get("natal_chart", {})
    chart = _get_chart_object(payload, age, natal_chart)
    ruler = "Unknown"
    if chart:
        ruler = chart.get("35_year_cycle_ruler", "Unknown")
    
    period = (age - 1) % 35 + 1
    # Maturity ages
    maturity = {
        16: "Jupiter", 22: "Sun", 24: "Moon", 25: "Venus",
        28: "Mars", 34: "Mercury", 36: "Saturn", 42: "Rahu", 48: "Ketu"
    }
    
    status = []
    current_matures = [p for a, p in maturity.items() if a <= age]
    if current_matures:
        status.append(f"Mature Planets: {', '.join(current_matures)}")
    
    peak_planet = maturity.get(age)
    if peak_planet:
        status.append(f"CRITICAL MATURITY PEAK: {peak_planet} matures this year (Age {age}).")
        
    return json.dumps({
        "age": age,
        "cycle_period": period,
        "current_cycle_ruler": ruler,
        "maturity_status": status,
        "IMPORTANT_INSTRUCTION_FOR_AGENT": f"The period is currently ruled by {ruler}. You MUST now call get_predictions(age=0) and look at specifically how {ruler} is performing in the NATAL chart to give accurate lifecycle advice."
    }, indent=2)


def _get_karaka_comparison(context: Dict, params: Dict) -> str:
    """Compare two sets of planetary karakas (e.g. Saturn for Job vs Mercury for Business) at a specific age."""
    age = int(params.get("age", 0))
    set_a = params.get("set_a", [])
    set_b = params.get("set_b", [])
    label_a = params.get("label_a", "Option A")
    label_b = params.get("label_b", "Option B")
    
    if not set_a or not set_b:
        return "Error: Both planet sets must be provided for comparison."
        
    payload = context.get("full_payload", {})
    natal_chart = context.get("natal_chart")
    
    chart = _get_chart_object(payload, age, natal_chart)
    if not chart:
        return f"Chart for age {age} not found."
        
    # Calculate strengths
    natal_chart = context.get("natal_chart") if age > 0 else None
    strengths = _pipeline.strength_engine.calculate_chart_strengths(chart, natal_chart=natal_chart)
    
    # Merge with natal if annual
    if age > 0 and natal_chart:
        natal_strengths = _pipeline.strength_engine.calculate_chart_strengths(natal_chart)
        strengths = _pipeline.strength_engine.merge_natal_annual(natal_strengths, strengths)
    
    from astroq.lk_prediction.statistical_core import aggregate_fuzzy_scores
    
    scores_a = [strengths.get(p, {}).get("strength_total", 0.0) for p in set_a]
    scores_b = [strengths.get(p, {}).get("strength_total", 0.0) for p in set_b]
    
    agg_a = aggregate_fuzzy_scores(scores_a)
    agg_b = aggregate_fuzzy_scores(scores_b)
    
    winner = label_a if agg_a > agg_b else label_b if agg_b > agg_a else "Tied"
    
    return json.dumps({
        "age": age,
        "comparison": {
            label_a: {"planets": set_a, "score": round(agg_a, 4)},
            label_b: {"planets": set_b, "score": round(agg_b, 4)}
        },
        "verdict": winner,
        "recommendation": f"Based on planetary favorability, {winner} is the stronger path."
    }, indent=2)


def _finish_tool(context: Dict, params: Dict) -> str:
    """Special tool to signal completion and return the final synthesis."""
    return params.get("answer", "Analysis complete.")


# ─────────────────────────────────────────────
# Tool Registry
# ─────────────────────────────────────────────

TOOLS = [
    {
        "name": "list_charts",
        "description": "List all client charts saved in the database. Use this to find a chart_id if not known.",
        "parameters": {
            "type": "object",
            "properties": {}
        },
        "fn": _list_charts
    },
    {
        "name": "get_natal_chart",
        "description": "Load an existing natal chart from the database into the agent context.",
        "parameters": {
            "type": "object",
            "properties": {
                "chart_id": {"type": "integer", "description": "The ID of the chart to load."}
            },
            "required": ["chart_id"]
        },
        "fn": _get_natal_chart
    },
    {
        "name": "generate_natal_chart",
        "description": "Generate a new natal chart (and its annual charts) and save it to the database.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Client name"},
                "dob": {"type": "string", "description": "Date of birth (YYYY-MM-DD)"},
                "tob": {"type": "string", "description": "Time of birth (HH:MM)"},
                "place": {"type": "string", "description": "Place of birth (City, Country)"},
                "chart_system": {"type": "string", "enum": ["vedic", "kp"], "default": "vedic"},
                "annual_basis": {"type": "string", "enum": ["vedic", "kp"], "default": "vedic"}
            },
            "required": ["name", "dob", "tob", "place"]
        },
        "fn": _generate_natal_chart
    },
    {
        "name": "get_annual_charts",
        "description": "Retrieve Varshaphal (annual) charts for a specific age range from the current payload.",
        "parameters": {
            "type": "object",
            "properties": {
                "age_from": {"type": "integer", "description": "Starting age"},
                "age_to": {"type": "integer", "description": "Ending age"}
            },
            "required": ["age_from", "age_to"]
        },
        "fn": _get_annual_charts
    },
    {
        "name": "get_predictions",
        "description": "Generate Lal Kitab predictions for a specific age chart (use 0 for natal).",
        "parameters": {
            "type": "object",
            "properties": {
                "age": {"type": "integer", "description": "Age for which to generate predictions (0 for natal chart)."}
            },
            "required": ["age"]
        },
        "fn": _get_predictions
    },
    {
        "name": "get_domain_scores",
        "description": "Calculate domain-specific scores (Marriage, Career, etc.) for a specific age.",
        "parameters": {
            "type": "object",
            "properties": {
                "age": {"type": "integer", "description": "Age for which to calculate scores (0 for natal chart)."}
            },
            "required": ["age"]
        },
        "fn": _get_domain_scores
    },
    {
        "name": "get_remedies",
        "description": "Extract remedies for a specific age based on previously generated predictions.",
        "parameters": {
            "type": "object",
            "properties": {
                "age": {"type": "integer", "description": "Age for which to extract remedies."}
            },
            "required": ["age"]
        },
        "fn": _get_remedies
    },
    {
        "name": "get_highest_probability_ages",
        "description": "Scan a range of ages (e.g., 20 to 45) to find the top 3 ages with the highest statistical probability for a specific domain like Marriage or Career.",
        "parameters": {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "enum": ["Marriage", "Career", "Income", "Wealth", "Health"], "description": "The life domain to scan."},
                "start_age": {"type": "integer", "description": "Start age for scan.", "default": 20},
                "end_age": {"type": "integer", "description": "End age for scan.", "default": 45}
            },
            "required": ["domain"]
        },
        "fn": _get_highest_probability_ages
    },
    {
        "name": "get_domain_comparison",
        "description": "Compare multiple life domains (e.g., Career vs Wealth) for a specific age to determine which is more prominent or favorable.",
        "parameters": {
            "type": "object",
            "properties": {
                "age": {"type": "integer", "description": "The age to analyze."},
                "domains": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["Marriage", "Career", "Income", "Wealth", "Health"]},
                    "description": "List of domains to compare."
                }
            },
            "required": ["age"]
        },
        "fn": _get_domain_comparison
    },
    {
        "name": "get_lifecycle_status",
        "description": "Identify the 35-year cycle ruler and planetary maturity status for a specific age.",
        "parameters": {
            "type": "object",
            "properties": {
                "age": {"type": "integer", "description": "The age to check."}
            },
            "required": ["age"]
        },
        "fn": _get_lifecycle_status
    },
    {
        "name": "get_karaka_comparison",
        "description": "Perform a deep-dive comparison between two specific astrological paths (e.g., Job vs. Business) by analyzing the underlying planetary Karakas.",
        "parameters": {
            "type": "object",
            "properties": {
                "age": {"type": "integer", "description": "The age to analyze."},
                "set_a": {"type": "array", "items": {"type": "string"}, "description": "Planet Karakas for first option (e.g., ['Saturn'] for Jobs)."},
                "set_b": {"type": "array", "items": {"type": "string"}, "description": "Planet Karakas for second option (e.g., ['Mercury'] for Business)."},
                "label_a": {"type": "string", "description": "Label for first option."},
                "label_b": {"type": "string", "description": "Label for second option."}
            },
            "required": ["age", "set_a", "set_b", "label_a", "label_b"]
        },
        "fn": _get_karaka_comparison
    },
    {
        "name": "finish",
        "description": "Signal that the analysis is complete and provide the final synthesis to the user.",
        "parameters": {
            "type": "object",
            "properties": {
                "answer": {"type": "string", "description": "The final detailed astrological response including interpretation and remedies."}
            },
            "required": ["answer"]
        },
        "fn": _finish_tool # Special tool handled by the agent loop
    }
]

TOOL_MAP = {t["name"]: t for t in TOOLS}

TOOL_TREES = {
    "Onboarding_Tree": {
        "description": "Use this for managing client records, listing available charts, creating new profiles, or generating a new natal chart from birth details (DOB, TOB, POB).",
        "tools": [TOOL_MAP["list_charts"], TOOL_MAP["generate_natal_chart"], TOOL_MAP["finish"]]
    },
    "Natal_Tree": {
        "description": "Use this for foundational analysis of the birth chart only. Evaluates core destiny, static birth-time promise, and permanent house positions at the moment of birth (Age 0). Not for age-specific predictions.",
        "tools": [TOOL_MAP["get_natal_chart"], TOOL_MAP["get_domain_scores"], TOOL_MAP["get_predictions"], TOOL_MAP["finish"]]
    },
    "Temporal_Tree": {
        "description": "Use this for annual charts (Varshaphal), specific ages, age ranges, timelines, and time-periods (e.g. results for age 48 or 48-52). Analyze temporal changes, peaks, and peaks over time.",
        "tools": [TOOL_MAP["get_natal_chart"], TOOL_MAP["get_annual_charts"], TOOL_MAP["get_domain_scores"], TOOL_MAP["get_predictions"], TOOL_MAP["get_highest_probability_ages"], TOOL_MAP["get_domain_comparison"], TOOL_MAP["get_karaka_comparison"], TOOL_MAP["get_lifecycle_status"], TOOL_MAP["finish"]]
    },
    "Remedy_Tree": {
        "description": "Use this to extract Lal Kitab Upayas (remedies) or solutions for specific planetary afflictions, bad luck, or crises occurring at a particular age or in the natal chart.",
        "tools": [TOOL_MAP["get_natal_chart"], TOOL_MAP["get_predictions"], TOOL_MAP["get_remedies"], TOOL_MAP["finish"]]
    }
}
