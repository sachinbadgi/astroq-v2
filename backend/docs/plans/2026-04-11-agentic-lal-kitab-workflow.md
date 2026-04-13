# Design Document: Agentic Lal Kitab Workflow

## Overview
This document defines the architecture for transforming the Lal Kitab astrological engine into a deterministic, agentic system. The goal is to separate linguistic synthesis (handled by the LLM) from technical calculation and belief resolution (handled by a specialized Python backend).

## Architecture: Hybrid Determinism

### 1. The Deterministic State Machine (LangGraph)
We use a functional `StateGraph` (not `create_react_agent`) to enforce a strict lifecycle for every user query. This prevent the LLM from taking uncontrolled actions.

**Lightweight AgentState:**
* `messages`: The conversation history.
* `chart_id`: The integer ID of the active user chart.
* `active_tools`: A list of names of tools available for the current node.
* **Note:** The state does NOT pass full JSON charts. Nodes must query the database independently.

**Nodes:**
* **Node A: Context Gatekeeper:** Verifies if a `chart_id` is present.
* **Node B: Intent Router:** Uses Semantic Tool RAG to categorize the query.
* **Node C: Reasoning LLM:** Synthesizes an answer using a constrained tool set.
* **Node D: Tool Executor:** Executes heavy Python logic (DST, Fuzzy, Bayesian).

### 2. Semantic Tool RAG (Intent Router)
To prevent "tool bloat," queries are mapped to one of four **Semantic Tool Trees**:
* **Onboarding Tree:** For first-time setup and chart listing.
* **Natal Tree:** For "Who am I?" style character analysis (Age 0).
* **Temporal Tree:** For specific years, Varshaphal, and timing.
* **Remedy Tree:** For crises and Lal Kitab Upayas (remedies).

We use `sentence-transformers` to vectorize the user's query and perform cosine similarity matching against the tree descriptions.

### 3. Statistical Core (Heavy Lift)
All technical interpretation happens in the Python backend (`lse_orchestrator.py`). The LLM only sees the *resolved* JSON results.

* **Bayesian Priors:** Prediction probabilities are weighted using the user's personalized **Chart DNA**.
* **Dempster-Shafer (DST) Fusion:** Resolves contradictions when rules trigger both positive and negative magnitudes in the same domain.
* **Fuzzy Inference System (FIS):** Aggregates precise numerical `aspect_strength` (0-100) into finalized `domain_scores` (0.0-1.0).

## Success Criteria
1. The LLM never hallucinates planetary positions (it only reports results).
2. The LLM never picks tools outside its assigned Tree.
3. Complex astrological contradictions are resolved mathematically before the agent synthesizes the response.
