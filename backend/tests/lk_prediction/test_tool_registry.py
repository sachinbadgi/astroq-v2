import pytest
import os
import sys

# Add backend to path
_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

def test_tool_trees_exist():
    from astroq.lk_prediction.agent.tool_registry import TOOL_TREES
    assert "Onboarding_Tree" in TOOL_TREES
    assert "Natal_Tree" in TOOL_TREES
    assert "Temporal_Tree" in TOOL_TREES
    assert "Remedy_Tree" in TOOL_TREES
    assert len(TOOL_TREES["Temporal_Tree"]["tools"]) > 0
    assert "description" in TOOL_TREES["Temporal_Tree"]
