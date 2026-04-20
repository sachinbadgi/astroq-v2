# Interpretation Layer

The Interpretation Layer is the final stage of the AstroQ Lal Kitab pipeline. It is responsible for translating technical rule hits and planetary strengths into structured, human-readable astrological data optimized for downstream LLM analysis (NotebookLM).

## Philosophy: Rule-to-Payload Mapping

Unlike modern probabilistic systems, the AstroQ Interpretation Layer operates on a **High-Fidelity Deterministic** model. It assumes that if a Lal Kitab rule is "hit," it must be reported with its canonical description and associated planetary magnitude.

### Key Components

- **`prediction_translator.py`**: Maps raw `RuleHit` objects (from the Rules Engine) into `LKPrediction` objects.
- **`pipeline.generate_llm_payload()`**: Aggregates Natal promises and Annual fulfillments into a single coherent timeline JSON.

## Optimization for NotebookLM

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
