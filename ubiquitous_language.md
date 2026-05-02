# AstroQ-v2: Ubiquitous Language

This document defines the core terminology used across the AstroQ-v2 codebase and documentation. To prevent ambiguity and "agent drift," all communication, PRDs, and code comments must strictly adhere to these definitions.

| Term | Definition | Category | Code Reference / Pattern |
| :--- | :--- | :--- | :--- |
| **Aspect Strength** | The numerical value of the influence one planet exerts on another based on house position. | Astrology | `ASPECT_STRENGTH_DATA` |
| **BilMukabil** | "Face to Face" or direct 1/7 house aspect interaction. | Astrology | `GrammarAnalyser` |
| **Dormancy** | A state (Soyi Hui) where a planet is inactive until its "sleeper" condition is met. | Astrology | `Soyi Hui` logic |
| **Doubtful Fate** | Outcomes that are conditional and can be altered by remedies or Varshphal triggers. | Astrology | `Rashi Phal` |
| **Entanglement** | The logical coupling of planets in conjunction, specifically regarding Masnui creation. | System | `entanglement.py` |
| **Fixed Fate** | The natal promise (Natal Chart) that is unchangeable and guaranteed. | Astrology | `Graha Phal` |
| **Fuzzer** | A deterministic validation tool that runs thousands of permutations to verify logic. | System | `pattern_validation_fuzzer.py` |
| **Goswami 1952** | The canonical Lal Kitab methodology serving as the source of truth for all logic. | Domain | `GEMINI.md` |
| **Graha Phal** | Fixed natal fate; the core "promise" of the birth chart. | Astrology | `StrengthEngine` |
| **Grammar** | The structural ruleset (Aspects, Strength, Dignity) governing planetary interactions. | System | `GrammarAnalyser` |
| **Lamp Principle** | The rule that annual rotation "lights the lamp" of a dormant natal planet. | Astrology | `VarshphalTimingEngine` |
| **Masnui** | Artificial planets created by the conjunction of two base planets. | Astrology | `MASNUI_PLANETS` |
| **Munsif Rule** | The decisive filter (House 1 vs. House 7) that prevents false-positive activation. | Astrology | `RashiPhalEvaluator` |
| **Pakka Ghar** | The "Permanent House" or "House of Power" for a specific planet. | Astrology | `PLANET_PAKKA_GHAR` |
| **Rashi Phal** | Conditional annual activation; the "doubtful" triggers found in Varshphal. | Astrology | `RashiPhalEvaluator` |
| **Remedy Shifting** | The process of moving a planet's influence to a safe Pakka Ghar to mitigate malefic results. | Astrology | `RemedyEngine` |
| **Scapegoat** | A planet that takes the "hit" or malefic influence on behalf of another. | Astrology | `SCAPEGOATS_INFO` |
| **Scheduled Sign** | The target house in the Annual Chart where a natal planet "arrives" to give its results. | Astrology | `VarshphalTimingEngine` |
| **Shifting Option** | A specific house/planet combination proposed as a remedy. | System | `ShiftingOption` contract |
| **Sudden Strike** | A specific clash (Takkar) between houses (e.g., 1/8, 2/12) that triggers immediate events. | Astrology | `SUDDEN_STRIKE_HOUSE_SETS` |
| **Timing Engine** | The core logic responsible for mapping triggers to specific ages/years. | System | `VarshphalTimingEngine` |
| **Startled State** | An explosive or sudden activation of a planet due to a specific strike (e.g., Rahu to Sun). | Astrology | `ContextualAssembler` |
| **Awake State** | The normal, steady state of a planet that is not dormant. | Astrology | `StateLedger` |
| **Leaking State** | A condition where a planet's energy is being drained by a malefic conjunction. | Astrology | `synthesis_vocabulary.json` |
| **Timing Confidence** | A high-fidelity score (High/Medium/Low) determining the certainty of a predicted event occurring in a specific year. | System | `VarshphalTimingEngine` |
| **Ubiquitous Language** | This document; the mandatory terminology for AI-Human collaboration. | Process | `ubiquitous_language.md` |
| **Varshphal** | The Annual Chart that rotates planetary positions based on current age. | Astrology | `VarshphalTimingEngine` |
