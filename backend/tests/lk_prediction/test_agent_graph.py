import pytest
from typing import Annotated, Sequence, List, Optional, TypedDict
from langchain_core.messages import BaseMessage, HumanMessage

def test_agent_graph_transitions():
    from astroq.lk_prediction.agent.agent_graph import create_lal_kitab_graph
    
    # Initialize state
    initial_state = {
        "messages": [HumanMessage(content="Will I get married at 30?")],
        "chart_id": None,
        "active_tools": []
    }
    
    app = create_lal_kitab_graph()
    
    # Run a single step to see where it goes
    # Since chart_id is None, it should hit the 'check_context' node 
    # and then possibly 'onboarding' or 'intent_router'
    
    # For TDD, we just check if it's a valid graph
    assert app is not None
    assert "check_context" in app.nodes
    assert "route_intent" in app.nodes
