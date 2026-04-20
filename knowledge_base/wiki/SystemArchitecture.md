# System Architecture

The AstroQ v2 Lal Kitab backend is structured as a predictive astrological physics engine with a robust agentic orchestration layer. 

## Core Engines
The predictive analysis relies on two primary deterministic engines:
- **`rules_engine.py` & `remedy_engine.py`**: Executes Lal Kitab grammar rules and recommends canonical planetary remedies based on House positions.
- **`strength_engine.py`**: Assesses planetary dignities, Lal Kitab strength coefficients (Manda/Nek), and status flags (Dharmi, Kaayam, Sleeping).
- **`grammar_analyser.py`**: Applies the complex Lal Kitab linguistic and positional grammar to enrich raw chart data prior to rule evaluation.

## Agent / Orchestration (LSE Suite)
The system leverages an automated domain-based workflow (Lal Kitab Software Engineer or "LSE"):
- **`lse_orchestrator.py`**: Coordinates the entire workflow, manages back-testing suites, hypothesis generation, and convergence logic.
- **`lse_researcher.py` & `lse_validator.py`**: Work in tandem to parse ground-truth events against generated charts to measure fidelity, eliminating false positives for a given public figure.
- **`pipeline.py` & `prediction_translator.py`**: Handle data ingestion, payload enrichment, and translating engine outputs into human-readable rationale.

## Data & Constants
- **`lk_constants.py`**: The centralized, canonical module representing astrological reference data (karmic debt, 35-year cycle rules, maturity ages).
- **`lse_chart_dna.py`**: Manages generated chart data payload representations for deterministic audits.

*This wiki page is auto-compiled from the `/backend/astroq/lk_prediction/` source directory.*
