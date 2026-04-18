"""
Phase 6: Auto-Research Graph (AutoResearch 2.0)
==============================================
Autonomous iterative research loop using LangGraph.
"""

from typing import TypedDict, List, Optional, Any
from langgraph.graph import StateGraph, START, END

from astroq.lk_prediction.data_contracts import (
    ChartData,
    ChartDNA,
    GapReport,
    LifeEventLog,
    LSESolveResult
)
from astroq.lk_prediction.lse_orchestrator import LSEOrchestrator
from astroq.lk_prediction.config import ModelConfig


class ResearchState(TypedDict):
    """State for the autonomous research loop."""
    figure_id: str
    natal_chart: ChartData
    annual_charts: dict[int, ChartData]
    known_events: LifeEventLog
    current_chart_dna: ChartDNA
    iteration_count: int
    current_accuracy_score: float
    gap_report: Optional[GapReport]
    predictions: List[Any]  # Final predictions from the pipeline
    history: List[dict]  # Track iterations for auditing


def run_baseline(state: ResearchState) -> dict:
    """
    Node: Run the prediction engine with current DNA weights.
    """
    print(f"--- Running Baseline (Iteration {state['iteration_count']}) ---")
    
    # Initialize Config and Orchestrator
    import os
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    db_path = os.path.join(base_path, f"mock_{state['figure_id']}.db")
    defaults_path = os.path.join(base_path, "astroq", "lk_prediction", "data", "model_defaults.json")
    
    cfg = ModelConfig(db_path=db_path, defaults_path=defaults_path)
    orchestrator = LSEOrchestrator(cfg)
    
    # Inject current DNA overrides into config
    dna = state['current_chart_dna']
    if dna.config_overrides:
        for k, v in dna.config_overrides.items():
            # Set as global override in this ephemeral config so RulesEngine finds it
            cfg.set_override(k, v, source="research_loop")
            
    # 1. Run predictions for the ages in known_events
    predictions = orchestrator._run_pipeline(
        state['natal_chart'], 
        state['annual_charts'], 
        state['figure_id']
    )
    
    # 2. Apply DNA Delays/Weights (LSE Personalisation)
    # This is crucial for the research loop to actually see its own adjustments
    from dataclasses import replace
    dna = state['current_chart_dna']
    
    adjusted_predictions = []
    for p in predictions:
        p_adj = replace(p) # Shallow copy via dataclass replace
        for planet in p_adj.source_planets:
            for k, v in dna.delay_constants.items():
                if planet.lower() in k.lower():
                    p_adj.peak_age += float(v)
                    break # Apply first matching delay
        adjusted_predictions.append(p_adj)
    
    return {
        "predictions": adjusted_predictions,
        "history": state.get("history", []) + [{"action": "run_baseline", "predictions_count": len(adjusted_predictions)}]
    }


def calculate_loss(state: ResearchState) -> dict:
    """
    Node: Compare predictions to known events and compute accuracy.
    """
    print(f"--- Calculating Loss (Iteration {state['iteration_count']}) ---")
    
    from astroq.lk_prediction.lse_validator import ValidatorAgent
    validator = ValidatorAgent()
    
    gap_report = validator.compare_to_events(state['predictions'], state['known_events'])
    accuracy = gap_report['hit_rate']
    top3_rate = gap_report.get('top_3_hit_rate', 0.0)
    
    print(f"Accuracy: {accuracy:.4f} | Top-3 Competitive Hit Rate: {top3_rate:.4f}")
    
    return {
        "current_accuracy_score": accuracy,
        "gap_report": gap_report,
        "history": state.get("history", []) + [{"action": "calculate_loss", "accuracy": accuracy, "top3_rate": top3_rate}]
    }


def generate_hypothesis(state: ResearchState) -> dict:
    """
    Node: Invoke LLM to generate a hypothesis (DNA patch) based on gaps.
    """
    print(f"--- Generating Hypothesis (Iteration {state['iteration_count']}) ---")
    
    import litellm
    from astroq.lk_prediction.agent.prompts import RESEARCHER_PROMPT
    import json
    import re
    
    # Construct context for the LLM
    # We include natal chart, gap report, and the previous history for trend analysis
    context = {
        "natal_chart": state['natal_chart'],
        "gap_report": state['gap_report'],
        "iteration": state['iteration_count'],
        "history": state['history'][-2:] if state['history'] else [] # Last few steps
    }
    
    prompt = f"{RESEARCHER_PROMPT}\n\n### CURRENT STATE:\n{json.dumps(context, indent=2)}"
    
    print(f"Calling LLM (gemini-2.0-flash) for research hypothesis...")
    try:
        response = litellm.completion(
            model="gemini/gemini-2.0-flash",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        match = re.search(r'\{.*\}', content, re.DOTALL)
        patch = json.loads(match.group()) if match else json.loads(content)
            
    except Exception as e:
        print(f"LLM Failed or Key Invalid ({e}). Falling back to Deterministic Aggressive Optimizer...")
        
        # AGGREGATE DETERMINISTIC OPTIMIZER (FULL POWER)
        adjustments = []
        gap_report = state['gap_report']
        
        # 1. TIMING RECOVERY (Fix Hits/Misses)
        for entry in gap_report.get('entries', []):
            if not entry['is_hit'] and entry['offset'] is not None:
                planet = entry['source_planets'][0] if entry['source_planets'] else "Sun"
                house = entry['source_houses'][0] if entry['source_houses'] else 1
                key = f"delay.{planet.lower()}_h{house}"
                shift = -entry['offset']
                adjustments.append({
                    "type": "delay", "key": key, "value": shift,
                    "rationale": f"Closing {shift}y gap."
                })
        
        # 2. FALSE POSITIVE SUPPRESSION (Mute noisy rules)
        # We target ALL contributing rule IDs for each false positive
        fp_list = gap_report.get('false_positives', [])
        for fp_text in fp_list:
            import re
            match = re.search(r'\[(.*?)\]', fp_text)
            if match:
                # Split by space as we joined them with space in validator
                rule_ids = match.group(1).split()
                for rule_id in rule_ids:
                    if rule_id != "NO_ID":
                        adjustments.append({
                            "type": "weight",
                            "key": f"weight.{rule_id}",
                            "value": 0.0,
                            "rationale": f"Muting contributing rule {rule_id} for FP suppression."
                        })
        
        patch = {"adjustments": adjustments}
    
    return {
        "history": state.get("history", []) + [{"action": "generate_hypothesis", "patch": patch}]
    }


def apply_patch(state: ResearchState) -> dict:
    """
    Node: Apply the LLM's suggested patch to the current ChartDNA.
    """
    print(f"--- Applying Patch (Iteration {state['iteration_count']}) ---")
    
    # Get last patch from history
    last_hypothesis = next((h for h in reversed(state['history']) if h['action'] == "generate_hypothesis"), None)
    if not last_hypothesis:
        return {}
        
    patch = last_hypothesis['patch']
    dna = state['current_chart_dna']
    
    for adj in patch.get("adjustments", []):
        if adj['type'] == "delay":
            dna.delay_constants[adj['key']] = adj['value']
        elif adj['type'] == "weight":
            dna.config_overrides[adj['key']] = adj['value']
            
    return {
        "current_chart_dna": dna,
        "iteration_count": state['iteration_count'] + 1,
        "history": state.get("history", []) + [{"action": "apply_patch", "patch_applied": True}]
    }


def should_continue(state: ResearchState):
    """
    Router: Decide whether to loop or end.
    """
    # TARGET: Hit Rate > 0.8 AND False Positives < 100
    hit_rate = state['current_accuracy_score']
    fp_count = len(state['gap_report'].get('false_positives', [])) if state['gap_report'] else 1000
    
    if state['iteration_count'] >= 20:
        print(f"--- Max Iterations Reached (20). Current FP: {fp_count} ---")
        return END
        
    if hit_rate >= 0.80 and fp_count < 100:
        print(f"--- TARGET REACHED: HR={hit_rate:.2f}, FP={fp_count} ---")
        return END
        
    return "generate_hypothesis"


# Initial setup logic
def create_research_graph():
    workflow = StateGraph(ResearchState)
    
    workflow.add_node("run_baseline", run_baseline)
    workflow.add_node("calculate_loss", calculate_loss)
    workflow.add_node("generate_hypothesis", generate_hypothesis)
    workflow.add_node("apply_patch", apply_patch)
    
    workflow.set_entry_point("run_baseline")
    
    workflow.add_edge("run_baseline", "calculate_loss")
    
    workflow.add_conditional_edges(
        "calculate_loss",
        should_continue,
        {
            "generate_hypothesis": "generate_hypothesis",
            END: END
        }
    )
    
    workflow.add_edge("generate_hypothesis", "apply_patch")
    workflow.add_edge("apply_patch", "run_baseline")
    
    return workflow.compile() # Default recursion limit handled in .invoke()


def run_research(figure_id: str) -> LSESolveResult:
    """
    Runner for a single figure research session.
    """
    print(f"=== Starting Research Session for FIGURE: {figure_id} ===")
    
    # Connect to ground truth DB to get events
    # Important: Re-fetch events from the research_ground_truth.db
    import sqlite3
    import os
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    db_path = os.path.join(base_path, "astroq", "lk_prediction", "research_ground_truth.db")
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT age, domain, description FROM public_figure_events WHERE figure_id = ?", (figure_id,))
    events = [{"age": row[0], "domain": row[1], "description": row[2]} for row in cur.fetchall()]
    conn.close()
    
    if not events:
        print(f"No events found for {figure_id}. Skipping.")
        return None

    from astroq.lk_prediction.agent.chart_loader import get_research_setup
    natal_chart, annual_charts = get_research_setup(figure_id)
    
    if not natal_chart:
        print(f"Could not load enriched chart for {figure_id}. Falling back to default.")
        natal_chart = {"planets_in_houses": {"Sun": {"house": 1}}}
        annual_charts = {age: natal_chart for age in range(1, 80)}
    
    # 2. Setup Initial State
    initial_dna = ChartDNA(figure_id=figure_id, back_test_hit_rate=0.0, mean_offset_years=0.0, iterations_run=0)
    initial_state = {
        "figure_id": figure_id,
        "natal_chart": natal_chart,
        "annual_charts": annual_charts,
        "known_events": events,
        "current_chart_dna": initial_dna,
        "iteration_count": 0,
        "current_accuracy_score": 0.0,
        "gap_report": None,
        "predictions": [],
        "history": []
    }
    
    # 3. Run Graph
    app = create_research_graph()
    final_state = app.invoke(initial_state, config={"recursion_limit": 150})
    
    print(f"=== Completed Research for {figure_id} (Accuracy: {final_state['current_accuracy_score']}) ===")
    
    # Promote to LSESolveResult
    return LSESolveResult(
        chart_dna=final_state['current_chart_dna'],
        iterations_run=final_state['iteration_count'],
        converged=final_state['current_accuracy_score'] >= 0.90,
        gap_report=final_state['gap_report']
    )
