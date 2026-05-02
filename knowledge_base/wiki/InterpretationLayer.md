# Interpretation Layer

The Interpretation Layer is the final stage of the AstroQ Lal Kitab pipeline. It is responsible for translating technical rule hits and planetary strengths into structured, human-readable astrological data optimized for downstream LLM analysis (NotebookLM).

## Philosophy: High-Depth Interpretation

The AstroQ Interpretation Layer follows "Deep Module" principles. Instead of shallow translation, it consolidates scoring, narrative assembly, timing analysis, and remedy coordination into a single, high-depth component: the `ContextualAssembler`.

### Key Components

- **`contextual_assembler.py`**: The central brain that assembles raw `RuleHit` objects into human-readable `LKPrediction` payloads.
- **`synthesis_vocabulary.json`**: A domain-specific narrative mapping that translates astrological states into high-fidelity prose.
- **`pipeline.generate_full_payload()`**: Aggregates Natal promises and Annual fulfillments into a single coherent timeline JSON for NotebookLM.

## 2. Narrative Vocabulary & State Logic

The `ContextualAssembler` uses a state-aware vocabulary to describe results. Every prediction is composed based on the planet's **Ledger State** and its **Magnitude**:

| State | Narrative Impact | Vocabulary Key |
| :--- | :--- | :--- |
| **Awake** | Steady, predictable growth or results. | `Awake:{Tier}:{Domain}` |
| **Startled** | Sudden, violent, or explosive activation. | `Startled:{Tier}:{Domain}` |
| **Leaking** | Gradual drain or dissipation of energy. | `Leaking:{Tier}:{Domain}` |
| **Burst** | Suppression or total collapse of the house's potential. | `Burst:{Tier}:{Domain}` |

### 2.1 Vocabulary Mapping
The mapping is stored in [synthesis_vocabulary.json](file:///Users/sachinbadgi/Documents/lal_kitab/astroq-v2/backend/astroq/lk_prediction/synthesis_vocabulary.json) and categorized by:
1. **Modifier**: Startled, Awake, Leaking, etc.
2. **Tier**: High (>= 1.5), Medium (>= 0.8), Low (< 0.8).
3. **Domain**: Career, Marriage, Health, etc.

## 3. Optimization for NotebookLM

To ensure the best results when feeding data into NotebookLM or Gemini:

1. **Categorical Clarity**: Events are grouped by canonical domains (Marriage, Career, Health, etc.).
2. **Magnitude Scoring**: Instead of probability, we provide the **Rule Magnitude**. A magnitude of 1.0 represents a canonical rule hit; lower numbers represent diminished strengths or diluted conditions.
3. **Data Grounding**: The payload explicitly links prediction text to the source planets and houses involved, providing "verifiable proofs" for the LLM to cite.

## JSON Data Contracts

The output `sachin_gemini_payload.json` follows a strict "Natal Promise vs. Annual Fulfillment" structure:

```json
{
  "natal_promise_baseline": {
    "planets_in_houses": { ... },
    "key_rule_signatures": [ ... ]
  },
  "annual_fulfillment_timeline": [
    {
      "age": 34,
      "dynamic_rule_activations": [ ... ]
    }
  ]
}
```

This structure allows the LLM to see the "seeds" (Natal) and the "harvest" (Annual) in a chronological sequence without being distracted by statistical noise.
