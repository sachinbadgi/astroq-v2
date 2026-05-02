# AstroQ-v2: Project Context

## The Big Picture
AstroQ-v2 is a high-fidelity, deterministic Lal Kitab predictive engine based on the canonical 1952 Goswami methodology. It aims to achieve 100% logical parity in event classification, timing, and remedy generation.

## Core Objectives
- **Predictive Fidelity**: Minimize false positives in astrological event triggers.
- **Deterministic Logic**: Eliminate "hallucination" by grounding all analysis in a structural rules engine.
- **75-Year Lifecycle Mapping**: Map natal promises (Graha Phal) to annual triggers (Rashi Phal) across a full human lifespan.

## Technology Stack
- **Backend**: Python (Rules Engine, Pattern Fuzzers, Data Pipelines).
- **Frontend**: Next.js / Vite (Premium Astrological Dashboards).
- **Data**: JSON-based chart payloads and rule constants.

## Key Concepts
- **Graha Phal**: Fixed natal fate (Natal Promise).
- **Rashi Phal**: Conditional annual activation (Varshphal Triggers).
- **Masnui Planets**: Artificial planetary conjunctions and their "entanglement" logic.
- **Soyi Hui (Dormancy)**: Rules governing inactive planets and their activation triggers.

## Agent Guidelines
- **Ubiquitous Language**: You MUST use the terminology defined in [ubiquitous_language.md](file:///Users/sachinbadgi/Documents/lal_kitab/astroq-v2/ubiquitous_language.md). Never use synonyms for defined terms (e.g., use "Sudden Strike" instead of "Clash" or "Takkar").
- **Precision First**: Never guess an astrological rule. Reference `lk_pattern_constants.py` or canonical documentation.
- **Evidence-Based**: All predictive claims must be backed by structural rule triggers.
- **Deterministic Validation**: Use the pattern fuzzer and timing engine to verify logic changes.
