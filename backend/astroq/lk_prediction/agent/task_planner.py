"""
TaskPlanner — uses LLM to decompose user question into an ordered list of tool calls.
"""
import json
import litellm
import os
from typing import List, Dict

OLLAMA_MODEL = "ollama/gemma4"
litellm.telemetry = False

# Import tools so we can build descriptions
import sys
_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from astroq.lk_prediction.agent.tool_registry import TOOLS

PLANNER_SYSTEM = """\
You are a strategic planning assistant for a Lal Kitab astrological AI Agent.

Your goal is to decompose a user's question into an ordered list of tool calls.

Available tools:
{tool_descriptions}

CRITICAL EXECUTION RULES:
1. CHART CHECK: If 'has_natal_chart' is false in SESSION STATE AND the user HAS NOT provided birth details, you MUST start your plan with 'list_charts' then 'finish'. Explain to the user they must pick a chart or provide birth details.
2. LOADING: If a chart IS already loaded ('has_natal_chart': true), you can jump straight to analysis (annual charts, predictions, etc.).
3. AGE CALCULATION: Use 'client_dob' and 'current_date' from SESSION STATE to calculate the user's age. DO NOT trust your memory for age; use the provided SESSION STATE math. Age = Year_of_Interest - Birth_Year. (Example: 1977 birth, 2025 interest = 48 years old).
4. NO PLACEHOLDERS: Never use strings like 'CLIENT_ID' for integer parameters. If you don't have the ID, list charts first.
5. ORDER: Always Load/Generate chart -> (Optional) Get Annual Charts -> Get Predictions/Scores -> Finish.
6. THEMES: For marriage/career questions, always include 'get_annual_charts' for the relevant age, 'get_domain_scores', AND 'get_predictions'. The 'get_predictions' tool is essential for technical Lal Kitab reasoning.
7. REMEDIES: ONLY include 'get_remedies' if the user explicitly asks for help, remedies, or how to fix a situation.

Output ONLY a valid JSON object with a "plan" key containing an array of objects.
{{
  "plan": [
    {{"tool": "tool_name", "params": {{...}}, "reason": "..."}},
    ...
  ]
}}
"""

def build_tool_descriptions() -> str:
    lines = []
    for t in TOOLS:
        params = json.dumps(t.get("parameters", {}).get("properties", {}))
        line = f"- {t['name']}: {t['description']} | Parameters: {params}"
        lines.append(line)
    return "\n".join(lines)

def plan_tasks(question: str, memory_context: str, context_state: Dict = None) -> List[Dict]:
    """
    Asks the LLM to generate an execution plan for a given question.
    """
    if context_state is None:
        context_state = {"has_natal_chart": False}
        
    tool_descriptions = build_tool_descriptions()
    
    system_prompt = PLANNER_SYSTEM.format(tool_descriptions=tool_descriptions)
    
    user_prompt = f"""
SESSION STATE:
{json.dumps(context_state, indent=2)}

CLIENT MEMORY/CONTEXT:
{memory_context if memory_context else "No active memory for this client."}

USER QUESTION:
{question}

Generate the JSON plan object:
"""

    try:
        response = litellm.completion(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"} # If supported by the local model/provider
        )
        
        content = response.choices[0].message.content.strip()
        
        # Strip markdown fences if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
            
        plan_data = json.loads(content)
        
        # Extract list from dict if needed
        plan = []
        if isinstance(plan_data, list):
            plan = plan_data
        elif isinstance(plan_data, dict):
            if "plan" in plan_data:
                plan = plan_data["plan"]
            elif "steps" in plan_data:
                plan = plan_data["steps"]
            else:
                # If it's a single dict that looks like a tool call, wrap it
                if "tool" in plan_data:
                    plan = [plan_data]
                else:
                    # Last resort: search for a list in values
                    for val in plan_data.values():
                        if isinstance(val, list):
                            plan = val
                            break
        
        if not isinstance(plan, list) or not plan:
            raise ValueError(f"LLM returned non-list or empty plan: {type(plan)}")
            
        return plan
        
    except Exception as e:
        print(f"Error in task planning: {e}")
        # Return a simple fallback plan
        return [
            {"tool": "list_charts", "params": {}, "reason": "Fallback: listing charts to identify user."},
            {"tool": "finish", "params": {"answer": "I encountered an error while planning the analysis. Please check my connection to the local model."}, "reason": "Error fallback"}
        ]
