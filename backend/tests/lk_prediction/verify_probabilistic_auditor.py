
import os
import sys
import logging
import json
from langchain_core.messages import HumanMessage
from astroq.lk_prediction.agent.agent_graph import create_lal_kitab_graph

# Set up logging for visibility
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIFY")

def verify_entity_discovery():
    print("\n--- TEST 1: ENTITY DISCOVERY ('MOTHER') ---")
    # Simulate a query about "Mother"
    # We expect the EntityResolver to find Moon and House 4
    initial_state = {
        "messages": [HumanMessage(content="how is my mother's health at age 60")],
        "chart_id": "LOCAL",
        "user_id": "sachinkp",
        "intent": "Health",
        "resolved_context": None,
        "active_tools": []
    }
    
    app = create_lal_kitab_graph()
    results = app.invoke(initial_state)
    
    ctx = results.get("resolved_context")
    if ctx:
        summary = ctx.get('range_summary', {})
        age_60 = summary.get(60, {})
        evidence = age_60.get('discovery_evidence', [])
        
        print(f"Age 60 Result - Belief: {age_60.get('scores', {}).get('belief')}, Uncertainty: {age_60.get('scores', {}).get('uncertainty')}")
        print(f"Evidence Hits Detected: {len(evidence)}")
        
        # Check if any hit mentions Moon or House 4 (Karaka for Mother)
        mother_related = [h for h in evidence if "moon" in h['rule'].lower() or "house 4" in h['rule'].lower()]
        if mother_related:
            print(f"✅ SUCCESS: Found {len(mother_related)} hits related to Mother.")
            for h in mother_related[:2]:
                print(f"   Hit: {h['rule'][:100]}...")
        else:
            print("❌ FAILURE: No Mother-related hits found in evidence.")

    print("\n--- FINAL LLM SYNTHESIS ---")
    print(results["messages"][-1].content)

if __name__ == "__main__":
    verify_entity_discovery()
