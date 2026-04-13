"""
LalKitabAgent — The orchestrator of the memory, planning, and tool-execution loop.
Now upgraded to use a functional LangGraph agentic workflow.
"""
import json
import os
import litellm
import logging
from typing import List, Dict, Any, Optional
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

# Add backend to path
_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("astroq.agent")

from astroq.lk_prediction.agent.honcho_memory import HonchoMemory
from astroq.lk_prediction.agent.tool_registry import TOOL_MAP, _chart_store
from astroq.lk_prediction.agent.agent_graph import create_lal_kitab_graph
from astroq.lk_prediction.data_contracts import normalize_planets

OLLAMA_MODEL = "ollama/gemma4"
litellm.telemetry = False

class LalKitabAgent:
    def __init__(self, user_id: str, use_memory: bool = True):
        self.user_id = user_id
        self.use_memory = use_memory
        self.memory = HonchoMemory(user_id) if use_memory else None
        self.context: Dict[str, Any] = {"user_id": self.user_id} # Persistent across the session
        
        # Proactively look for a chart matching this user_id/name
        self._auto_load_chart()

    def _auto_load_chart(self):
        """
        Attempts to load a chart for the current user. 
        Priority: 1. Local Gemini Payload JSON 2. Charts Database
        """
        # 1. Look for Local JSON Payload first (Native Source of Truth)
        local_payload_path = os.path.join(_BACKEND, f"{self.user_id}_gemini_payload.json")
        if os.path.exists(local_payload_path):
            try:
                with open(local_payload_path, 'r') as f:
                    payload = json.load(f)
                    natal = payload.get("natal_promise_baseline", {})
                    planets = natal.get("planets_in_houses") or payload.get("chart_0")
                    self.context["natal_chart"] = normalize_planets(planets or {})
                    self.context["full_payload"] = payload
                    self.context["client_name"] = payload.get("client_name", self.user_id)
                    
                    dob = payload.get("dob", natal.get("dob", ""))
                    if dob and len(dob) >= 4:
                        try: self.context["birth_year"] = int(dob[:4])
                        except: pass
                    
                    logger.info(f"Auto-loaded local JSON payload for user {self.user_id} (Birth Year: {self.context.get('birth_year')})")
                    return # Successfully loaded from local file
            except Exception as e:
                logger.warning(f"Failed to load local payload {local_payload_path}: {e}")

        # 2. Fallback to Load from DB
        charts = _chart_store.list_charts()
        for c in charts:
            # Match by user_id or if it is the only chart and named 'Client'
            if c['client_name'].lower() == self.user_id.lower() or (len(charts) == 1 and str(c['client_name']) == "Client"):
                chart = _chart_store.get_chart(c['id'])
                if chart:
                    raw_natal = chart["full_payload"].get("chart_0", {})
                    self.context["natal_chart"] = normalize_planets(raw_natal)
                    self.context["full_payload"] = chart["full_payload"]
                    self.context["client_name"] = chart["name"]
                    self.context["chart_id"] = c['id']
                    
                    # Extract birth year for date math context
                    dob = chart.get("dob", "")
                    if dob and len(dob) >= 4:
                        try:
                            self.context["birth_year"] = int(dob[:4])
                        except: pass
                        
                    logger.info(f"Auto-loaded chart ID {c['id']} for user {self.user_id} (Birth Year: {self.context.get('birth_year')})")
                    break
                    
    def ask(self, question: str) -> str:
        """
        Processes a user question through the LangGraph agentic workflow.
        """
        logger.info(f"Processing question for user {self.user_id}: {question}")
        
        # 1. Initialize State
        initial_state = {
            "messages": [HumanMessage(content=question)],
            "chart_id": self.context.get("chart_id") or "LOCAL",
            "birth_year": self.context.get("birth_year"),
            "user_id": self.user_id,
            "active_tools": [],
            "selected_tree": None,
            "natal_chart": self.context.get("natal_chart"),
            "full_payload": self.context.get("full_payload")
        }
        
        # 2. Compile and Run Graph
        app = create_lal_kitab_graph()
        
        print(f"\n[ORCHESTRATOR] Routing to Agentic Graph...")
        
        final_state = app.invoke(initial_state)
        
        # 3. Extract final answer from messages
        final_answer = ""
        for msg in reversed(final_state["messages"]):
            # Check for the result of the 'finish' tool
            if isinstance(msg, ToolMessage):
                # The 'finish' tool returns the answer as content
                final_answer = msg.content
                break
            # Fallback to AIMessage content
            if isinstance(msg, AIMessage) and msg.content:
                final_answer = msg.content
                break
            # Fallback to tool call arguments if LLM called finish but didn't execute node
            if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls"):
                for tc in msg.tool_calls:
                    if tc["name"] == "finish":
                        final_answer = tc["args"].get("answer", "")
                        break
                if final_answer: break
        
        # 4. Final Memory Update (Session Persistence)
        if self.memory:
            self.memory.add_message("user", question)
            self.memory.add_message("assistant", final_answer or "Analysis complete.")
            
        print("\n" + "="*50 + "\n")
        print(final_answer or "[No synthesis provided by graph]")
        print("\n" + "="*50)

        return final_answer
