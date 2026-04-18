import operator
from typing import Annotated, Sequence, List, Optional, TypedDict, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END

import litellm
import json
import os
import logging
import re
from astroq.lk_prediction.agent.intent_router import IntentRouter
from astroq.lk_prediction.agent.tool_registry import TOOL_MAP, TOOL_TREES
from astroq.lk_prediction.prediction_translator import PEOPLE_MAP, ITEMS_MAP
from astroq.lk_prediction.data_contracts import normalize_planets

# Set up logging
logger = logging.getLogger("astroq.agent.graph")

OLLAMA_MODEL = "ollama/gemma4"

class AgentState(TypedDict):
    """
    State for the Lal Kitab Agent.
    Lightweight: contains only IDs and schemas, not heavy objects.
    """
    messages: Annotated[Sequence[BaseMessage], operator.add]
    chart_id: Optional[Any] # Can be int (DB) or str (e.g. "LOCAL")
    birth_year: Optional[int]
    user_id: Optional[str]
    intent: Optional[str] # From IntentRouter
    active_tools: List[Dict[str, Any]]
    selected_tree: Optional[str]
    natal_chart: Optional[Dict[str, Any]]
    full_payload: Optional[Dict[str, Any]]
    resolved_context: Optional[Dict[str, Any]] # Pre-computed facts for synthesis

# ─────────────────────────────────────────────────────────────────────────────
# NODES
# ─────────────────────────────────────────────────────────────────────────────

def check_context(state: AgentState):
    """
    Checks if chart_id is present. If not, sets onboarding tree.
    """
    logger.info("Node: check_context")
    if state.get("chart_id") is None:
        logger.warning("No chart_id found in state.")
        return {"selected_tree": "Onboarding_Tree"}
    
    # If using local payload, skip onboarding
    if str(state.get("chart_id")) == "LOCAL":
        logger.info("Local chart detected, skipping onboarding.")
        return {"selected_tree": None}
        
    return {}

def route_intent(state: AgentState):
    """
    Uses the IntentRouter to select the appropriate Tool Tree.
    """
    logger.info("Node: route_intent")
    # Only route if we haven't already selected onboarding or a specific tree
    if state.get("selected_tree") == "Onboarding_Tree":
        return {"active_tools": TOOL_TREES["Onboarding_Tree"]["tools"], "intent": "Onboarding_Tree"}
        
    last_message = state["messages"][-1].content
    router = IntentRouter()
    result = router.get_intent_and_tools(last_message)
    
    logger.info(f"Routed to intent: {result['intent']}")
    return {"active_tools": result["tools"], "intent": result["intent"]}

# SUBSTANDARD LOGIC REMOVED: Redundant cycle ruler and normalization functions have been deleted.
# The agent now relies on the engine's ground-truth payload.

class EntityResolver:
    """Extracts people and items from query and maps them to planets/houses."""
    def __init__(self):
        self.people = PEOPLE_MAP
        self.items = ITEMS_MAP

    def resolve(self, query: str) -> dict[str, set]:
        query_lower = query.lower()
        active_planets = set()
        active_houses = set()

        # Check People
        for planet, aliases in self.people.items():
            if any(a.lower() in query_lower for a in aliases):
                if planet.startswith("h"):
                    active_houses.add(int(planet[1:]))
                else:
                    active_planets.add(planet)

        # Check Items
        for planet, aliases in self.items.items():
            if any(a.lower() in query_lower for a in aliases):
                if planet.startswith("h"):
                    active_houses.add(int(planet[1:]))
                else:
                    active_planets.add(planet)

        return {"planets": active_planets, "houses": active_houses}

def orchestrator_worker(state: AgentState):
    """
    Deterministic Python logic that executes fixed recipes based on intent.
    Includes a HEURISTIC OVERRIDE for temporal ranges (typo-safety).
    """
    logger.info(f"Node: orchestrator_worker (Intent: {state.get('intent')})")
    query = state["messages"][-1].content
    intent = state.get("intent")
    
    # HEURISTIC OVERRIDE: If query contains numbers, it's likely Temporal/Age-based
    import re
    ages = [int(a) for a in re.findall(r'\d+', query)]
    
    if len(ages) >= 1 and intent != "Temporal_Tree":
        logger.info(f"Heuristic Override: Detected ages {ages}. Switching to Temporal_Tree logic.")
        intent = "Temporal_Tree"
    
    if len(ages) < 1:
        return {"resolved_context": None}
    
    start_age = min(ages)
    end_age = max(ages) if len(ages) > 1 else start_age + 5
    
    logger.info(f"Executing TimelineScan recipe for ages {start_age} to {end_age}")
    
    # Context Loading (Ensures worker has data)
    internal_ctx = {
        "full_payload": state.get("full_payload"),
        "natal_chart": state.get("natal_chart"),
        "user_id": state.get("user_id", "default"),
        "chart_id": state.get("chart_id")
    }
    
    # 1. Resolve from File/DB if missing
    if not internal_ctx.get("full_payload") and internal_ctx.get("chart_id"):
        cid = internal_ctx["chart_id"]
        if str(cid) == "LOCAL":
            user_id = internal_ctx["user_id"]
            from astroq.lk_prediction.agent.lk_agent import _BACKEND
            path = os.path.join(_BACKEND, f"{user_id}_gemini_payload.json")
            if os.path.exists(path):
                with open(path, 'r') as f:
                    payload = json.load(f)
                    internal_ctx["full_payload"] = payload
        else:
            from astroq.lk_prediction.agent.tool_registry import _chart_store
            chart = _chart_store.get_chart(cid)
            if chart:
                internal_ctx["full_payload"] = chart["full_payload"]

    # 2. Always extract/normalize natal_chart from payload if we have it
    if internal_ctx.get("full_payload"):
        payload = internal_ctx["full_payload"]
        raw_map = {}
        if "natal_promise_baseline" in payload:
            raw_map = payload["natal_promise_baseline"].get("planets_in_houses", {})
        elif "chart_0" in payload:
            raw_map = payload["chart_0"]
        
        if raw_map:
            # Re-normalize to ensure robust dictionary format (house as dict, not int)
            internal_ctx["natal_chart"] = normalize_planets(raw_map)

    if not internal_ctx.get("full_payload") or not internal_ctx.get("natal_chart"):
        logger.warning(f"Worker could not resolve complete chart context. (Payload: {bool(internal_ctx.get('full_payload'))}, Natal: {bool(internal_ctx.get('natal_chart'))})")
        return {"resolved_context": None}

    # Use internal tool logic via the registry functions
    from astroq.lk_prediction.agent.tool_registry import _get_highest_probability_ages, _get_predictions, _get_remedies, _get_lifecycle_status
    
    # DYNAMIC SEARCH: Find the weakest year and AGGREGATE all years
    timeline = internal_ctx["full_payload"].get("annual_fulfillment_timeline", [])
    range_summary = {}
    
    # 1. Collect existing data from timeline
    for entry in timeline:
        age_val = entry["age"]
        if start_age <= age_val <= end_age:
            range_summary[age_val] = {
                "health_score": round(entry["domain_scores"].get("Health", 1.0), 3),
                "career_score": round(entry["domain_scores"].get("Career", 1.0), 3),
                "status": _get_lifecycle_status(internal_ctx, {"age": age_val}),
                "source": "Pre-computed"
            }

    # 2. GAP FILING: If requested years are missing, GENERATE THEM ON THE FLY 🚀
    missing_ages = [a for a in range(start_age, end_age + 1) if a not in range_summary]
    if missing_ages:
        logger.info(f"Filling data gaps for ages {missing_ages} using Live Prediction Engine.")
        from astroq.lk_prediction.chart_generator import ChartGenerator
        from astroq.lk_prediction.pipeline import LKPredictionPipeline
        from astroq.lk_prediction.config import ModelConfig
        
        # Resolve config paths
        _DIR = os.path.dirname(__file__)
        DB_PATH = os.path.abspath(os.path.join(_DIR, "../../../data/api_config.db"))
        DEFAULTS_PATH = os.path.abspath(os.path.join(_DIR, "../../../data/model_defaults.json"))
        
        generator = ChartGenerator()
        pipeline = LKPredictionPipeline(ModelConfig(db_path=DB_PATH, defaults_path=DEFAULTS_PATH))
        pipeline.load_natal_baseline({"chart_type": "Birth", "planets_in_houses": internal_ctx["natal_chart"]})
        
        # Batch generate all needed years up to the max requested age
        natal_data = {"chart_type": "Birth", "planets_in_houses": internal_ctx["natal_chart"]}
        all_generated = generator.generate_annual_charts(natal_data, max_years=max(end_age, 75))
        
        # IMPORTANT: Inject into internal_ctx so downstream tools like _get_predictions can find them
        if internal_ctx.get("full_payload") is not None:
            internal_ctx["full_payload"].update(all_generated)

        for age in missing_ages:
            live_chart = all_generated.get(f"chart_{age}")
            if not live_chart:
                continue

            # B. Run Pipeline for scores
            scores = pipeline.generate_domain_scores(live_chart)
            status = live_chart.get("35_year_cycle_ruler", "General")
            
            # C. Contextual Selection (Domain-Aware)
            resolver = EntityResolver()
            entities = resolver.resolve(query)
            possible_domains = ["Wealth", "Career", "Marriage", "Health", "Profession", "Travel", "General"]
            detected_domain = "General"
            for d in possible_domains:
                if d.lower() in query.lower():
                    detected_domain = d
                    break
            
            all_hits = pipeline.rules_engine.evaluate_chart(live_chart)
            discovery_hits = []
            for h in all_hits:
                is_general = h.domain.lower() == "general"
                is_intent = h.domain.lower() == detected_domain.lower()
                
                # Karaka Match
                is_entity = any(p in entities["planets"] for p in h.primary_target_planets) or \
                            any(house in entities["houses"] for house in h.target_houses)
                
                if is_general or is_intent or is_entity:
                    discovery_hits.append({
                        "rule": h.description,
                        "domain": h.domain,
                        "magnitude": h.magnitude,
                        "scoring_type": h.scoring_type
                    })

            range_summary[age] = {
                "scores": scores.get(detected_domain, scores), # Fallback to all scores if specific missing
                "status": status,
                "discovery_evidence": discovery_hits,
                "source": "Official Live Gen"
            }

    # 3. Find Global Bottleneck from combined data
    bottleneck_age = None
    min_score = 1.0
    for age, data in range_summary.items():
        # Get the belief score from the intent-specific metrics or fallback to 1.0
        score = data.get("scores", {}).get("belief", 1.0)
        if score < min_score:
            min_score = score
            bottleneck_age = age

    # 4. Get Deep-Dive for the identified Bottleneck (Detailed context for the weakest link)
    if not bottleneck_age:
        preds, remedies, bottleneck_chart = [], [], None
    else:
        # Pass internal_ctx which now contains the generated 'all_generated' charts
        preds_str = _get_predictions(internal_ctx, {"age": bottleneck_age})
        remedies_str = _get_remedies(internal_ctx, {"age": bottleneck_age})
        
        # Try to parse JSON from tool strings if possible, otherwise keep as string
        try:
            preds = json.loads(preds_str.split(":\n", 1)[1])
        except:
            preds = preds_str
            
        try:
            remedies = json.loads(remedies_str.split(":\n", 1)[1])
        except:
            remedies = remedies_str

        bottleneck_chart = internal_ctx.get("full_payload", {}).get(f"chart_{bottleneck_age}")

    resolved = {
        "analysis_type": "TIMELINE_SCAN",
        "requested_range": f"{start_age}-{end_age}",
        "metadata": payload.get("metadata", {}),
        "natal_chart": internal_ctx.get("natal_chart"),
        "range_summary": range_summary,
        "bottleneck_highlight": {
            "age": bottleneck_age,
            "score": round(min_score, 3) if bottleneck_age else None,
            "predictions": preds,
            "remedies": remedies,
            "annual_chart": bottleneck_chart
        },
        "automated_alert": f"CRITICAL BOTTLENECK DETECTED at age {bottleneck_age}. Minimum safety score: {round(min_score, 3)}." if bottleneck_age else None
    }
    
    return {"resolved_context": resolved}

def reasoning_llm(state: AgentState):
    """
    Invokes the LLM with the constrained toolset and Master Synthesis Prompt.
    """
    logger.info("Node: reasoning_llm")
    from astroq.lk_prediction.agent.prompts import MASTER_SYNTHESIS_PROMPT
    
    # Format messages for LiteLLM
    session_context = f"\nACTIVE SESSION CONTEXT:\n- Current Chart ID: {state.get('chart_id')}\n- Birth Year: {state.get('birth_year')}\n- Current User: {state.get('user_id', 'Unknown')}\n"
    messages = [{"role": "system", "content": MASTER_SYNTHESIS_PROMPT + session_context}]
    
    # If orchestrator has resolved context, inject it and downgrade LLM to synthesis mode
    if state.get("resolved_context"):
        logger.info("Injecting resolved_context into LLM prompt.")
        messages.append({
            "role": "system", 
            "content": f"RESOLVED ANALYTICAL CONTEXT:\n{json.dumps(state['resolved_context'], indent=2)}\n\nIMPORTANT: Use ONLY this data for your response. Do not call tools. Do not invent scores."
        })
        # For simplicity in synthesis mode, we don't pass tools to LiteLLM
        openai_tools = None
        tool_choice = None
    else:
        # Standard tool-using mode (for simple queries)
        tool_choice = "auto"
        openai_tools = []
        for t in state["active_tools"]:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["parameters"]
                }
            })

    for msg in state["messages"]:
        if isinstance(msg, HumanMessage): role = "user"
        elif isinstance(msg, AIMessage): role = "assistant"
        elif isinstance(msg, ToolMessage): role = "tool"
        else: role = "user"
        
        entry = {"role": role, "content": msg.content}
        if role == "tool":
            entry["tool_call_id"] = msg.tool_call_id
        messages.append(entry)

    response = litellm.completion(
        model=OLLAMA_MODEL,
        messages=messages,
        tools=openai_tools if openai_tools else None,
        tool_choice=tool_choice if openai_tools else None
    )

    msg = response.choices[0].message
    
    # Convert back to LangChain format
    if hasattr(msg, "tool_calls") and msg.tool_calls:
        logger.info(f"LLM produced {len(msg.tool_calls)} native tool calls.")
        tool_calls = []
        for tc in msg.tool_calls:
            # LangChain expects 'name' and 'args' at top level
            tool_calls.append({
                "name": tc.function.name,
                "args": json.loads(tc.function.arguments),
                "id": tc.id,
                "type": "tool_call"
            })
        return {"messages": [AIMessage(content=msg.content or "", tool_calls=tool_calls)]}
    
    # --- MANUAL PARSING FALLBACK for Gemma 4 ---
    if msg.content and ("{" in msg.content):
        try:
            # Try to extract JSON from content
            match = re.search(r'\{.*\}', msg.content, re.DOTALL)
            if match:
                data = json.loads(match.group())
                # Expanded formats for Gemma 4
                # 1. {"function_call": {"name": "...", "arguments": {...}}}
                # 2. {"name": "...", "arguments": {...}}
                # 3. {"function": "...", "params": {...}}
                
                inner = data.get("function_call") or data
                fname = inner.get("name") or inner.get("function")
                fargs = inner.get("arguments") or inner.get("params") or inner.get("args")
                
                if isinstance(fname, dict): # Double nested case
                    fargs = fname.get("arguments") or fname.get("params")
                    fname = fname.get("name")

                if fname and fargs:
                    logger.info(f"Manually parsed tool call: {fname}")
                    tool_calls = [{
                        "name": fname,
                        "args": fargs,
                        "id": "manual_call",
                        "type": "tool_call"
                    }]
                    return {"messages": [AIMessage(content="", tool_calls=tool_calls)]}
        except Exception as e:
            logger.warning(f"Failed to manually parse tool call structure: {e}")

    logger.info("LLM provided final text response.")
    return {"messages": [AIMessage(content=msg.content)]}

def _normalize_planets(planets_data: Dict[str, Any]) -> Dict[str, Any]:
    # Redirect to shared utility
    return normalize_planets(planets_data)

def tool_executor(state: AgentState):
    """
    Executes the requested tools and applies statistical resolving.
    """
    logger.info("Node: tool_executor")
    last_msg = state["messages"][-1]
    tool_messages = []
    
    # NEW: Automatically re-load chart context into the turn-based 'context'
    # to follow the "Lightweight State" constraint while giving tools data.
    cid = state.get("chart_id")
    context = {"chart_id": cid}
    
    if cid:
        if str(cid) == "LOCAL":
            # Attempt to resolve local payload for this tool execution turn
            user_id = state.get("user_id", "default")
            from astroq.lk_prediction.agent.lk_agent import _BACKEND
            path = os.path.join(_BACKEND, f"{user_id}_gemini_payload.json")
            if os.path.exists(path):
                with open(path, 'r') as f:
                    payload = json.load(f)
                    context["full_payload"] = payload
                    
                    # Normalize Natal Chart
                    natal_map = payload.get("natal_promise_baseline", {}).get("planets_in_houses", {})
                    context["natal_chart"] = normalize_planets(natal_map or payload.get("chart_0", {}))
                    
                    context["client_name"] = payload.get("client_name", user_id)
                    logger.info("Context resolved from Local JSON")
        else:
            from astroq.lk_prediction.agent.tool_registry import _chart_store
            chart = _chart_store.get_chart(cid)
            if chart:
                raw_natal = chart["full_payload"].get("chart_0", {})
                context["natal_chart"] = normalize_planets(raw_natal)
                context["full_payload"] = chart["full_payload"]
                context["client_name"] = chart["name"]
                logger.info(f"Context auto-loaded for Chart ID: {cid}")
    
    for tool_call in last_msg.tool_calls:
        tool_name = tool_call["name"]
        params = tool_call["args"]
        
        logger.info(f"Executing tool: {tool_name} with params: {params}")
        tool_info = TOOL_MAP.get(tool_name)
        if tool_info:
            try:
                result = tool_info["fn"](context, params)
            except Exception as e:
                result = f"Error executing {tool_name}: {str(e)}"
        else:
            result = f"Error: Tool {tool_name} not found."
            
        tool_messages.append(ToolMessage(
            content=result, 
            tool_call_id=tool_call["id"]
        ))
        
    return {"messages": tool_messages}

def should_continue(state: AgentState):
    """
    Router to decide if we exit or execute tools.
    """
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tool_executor"
    return END

def check_finish(state: AgentState):
    """
    Decides if we should return to LLM or finish.
    If 'finish' was called, we stop.
    """
    last_msg = state["messages"][-2] # The AIMessage that triggered the tools
    if hasattr(last_msg, "tool_calls") and any(tc["name"] == "finish" for tc in last_msg.tool_calls):
        return END
    return "reasoning_llm"

# ─────────────────────────────────────────────────────────────────────────────
# GRAPH BUILDING
# ─────────────────────────────────────────────────────────────────────────────

def create_lal_kitab_graph():
    """
    Builds the functional StateGraph.
    """
    workflow = StateGraph(AgentState)
    
    workflow.add_node("check_context", check_context)
    workflow.add_node("route_intent", route_intent)
    workflow.add_node("orchestrator_worker", orchestrator_worker)
    workflow.add_node("reasoning_llm", reasoning_llm)
    workflow.add_node("tool_executor", tool_executor)
    
    workflow.set_entry_point("check_context")
    
    # Deterministic Path
    workflow.add_edge("check_context", "route_intent")
    workflow.add_edge("route_intent", "orchestrator_worker")
    workflow.add_edge("orchestrator_worker", "reasoning_llm")
    
    # Reasoning Loop (Used if orchestrator didn't resolve everything)
    workflow.add_conditional_edges(
        "reasoning_llm",
        should_continue,
        {
            "tool_executor": "tool_executor",
            END: END
        }
    )
    
    # After tool execution, check if we should stop
    workflow.add_conditional_edges(
        "tool_executor",
        check_finish,
        {
            "reasoning_llm": "reasoning_llm",
            END: END
        }
    )
    
    return workflow.compile()
    
    return workflow.compile()
