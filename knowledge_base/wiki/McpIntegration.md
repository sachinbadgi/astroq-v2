# MCP Server Integration (Model Context Protocol)

This document details how the AstroQ v2 backend integrates with external Model Context Protocol (MCP) clients (such as Claude Desktop, local Gemma, etc.) while preserving the exact mathematical and deterministic routing constraints built into the system.

## The Threat Vector: LLM Hallucinated Tool Calls

Originally, the system's tools (`tool_registry.py`) were designed to be flattened into a typical agent interface. However, directly exposing raw astrological calculation tools (like `get_domain_scores`, `generate_monthly_chart`, `simulate_remedies`) to an external MCP client is dangerous.

**Why?** Because the external LLM must act as the orchestrator to decide *which* tool to call and *when*. It might try to call `simulate_remedies` before fetching `get_predictions`, or try to evaluate a Daily chart without generating a Monthly chart. It introduces non-deterministic reasoning into a strictly governed process.

## The Solution: "Encapsulated Graph" MCP Pattern

To neutralize LLM hallucination and ensure absolute determinism, the AstroQ MCP Server (`backend/astroq/lk_prediction/agent/mcp_server.py`) uses an **Encapsulated Pattern**.

### 1. Single External Tool
The MCP Server exposes exactly **one** macro-tool over the protocol:
- **`consult_lal_kitab_oracle(query: str, user_id: str)`**

### 2. Deep Deterministic Proxying
When an external LLM invokes `consult_lal_kitab_oracle`, it simply passes the conversational prompt. The backend then entirely takes over using native Python execution:

1. **`LalKitabAgent`**: Bootstraps the session and triggers the graph.
2. **`IntentRouter`**: Uses a `sentence-transformers` vector model (`all-MiniLM-L6-v2`) to mathematically calculate the cosine similarity of the query against predefined `TOOL_TREES` (Natal_Tree, Temporal_Tree, Remedy_Tree, etc.).
3. **`Agent Graph (LangGraph)`**: Rigidly executes the allowed tools in the correct deterministic order based exclusively on the router's decision.

### 3. Stateless Tool Adapters
Because MCP demands stateless interactions (no shared memory dicts passing between requests), we developed `StatelessToolAdapter` inside `tool_registry.py`. The internal agent graph invokes these adapters, which spin up isolated memory contexts for the duration of the query interpretation, safely terminating when the graph concludes.

## How to Run the Server

If you are using an external frontend or Claude Desktop setup, you map the MCP Server command to run in `stdio` mode:
```json
{
  "command": "/absolute/path/to/venv/bin/python3",
  "args": [
    "/absolute/path/to/astroq-v2/backend/astroq/lk_prediction/agent/mcp_server.py"
  ]
}
```

## Summary
The external LLM acts strictly as a conversational presentation UI. All intent, routing, sequence orchestration, and mathematical astrology calculations are strictly locked inside the graph server behind the single MCP tool interface.
