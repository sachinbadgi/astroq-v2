# Predictive Mathematics (Physics & Probability Engines)

The actual prediction logic mapping astrological placements to life events is driven by two heavy-math layers handling thermodynamic topological modeling and probability sigmoid modeling. 

This document provides explicit details required to reimplement the core algorithmic layer in any language.

## 1. Thermodynamic Graph-Diffusion Model (`PhysicsEngine`)

The Physics Engine runs immediately after the `rules_engine.evaluate_chart()` phase and *before* Dempster-Shafer aggregations. It modifies RuleHits with energy topologies and performs a Laplacian heat-diffusion.

### 1.1 Mutability Priorities
Each `RuleHit` is annotated with a topological `mutability` flag based on a strict deterministic priority cascade (Highest wins):

1. **`FIXED` (Dirichlet Boundary - Infinite Thermal Mass)**
   - **Triggers**: Planet is in Pakka Ghar, or Exaltation/Debilitation house, or tagged as "Fixed House Lord".
   - **Math Result**: Bypasses diffusion scaling. `magnitude` is instantly saturated to `0.9` (so DST aggregation loops receive maximal deterministic mass).
2. **`SYNTHETIC` (Reaction-Diffusion)**
   - **Triggers**: Planet is currently participating in an active Masnui Grahas formation. Attaches a `virtual_planet` pointer.
3. **`SYSTEMIC_LEAK` (Thermodynamic Sink)**
   - **Triggers**: Planet interacts with an active Rin (Karmic Debt) trigger house.
   - **Math Result**: Subtracts `_RIN_DRAIN_RATE = 0.25` from the house diffusion energy. Tags hit with `[COLLECTIVE_ACTIVATION_REQUIRED]`.
4. **`GATED`**
   - **Triggers**: Target planet is sitting in a sleeping house (house state = 0.0), but the planet itself is awake.
5. **`SLEEPING`**
   - **Triggers**: Target planet is tagged specifically with `sleeping_status = 'sleeping'`.
6. **`FLEXIBLE`** (Default baseline state)

### 1.2 Graph Laplacian Diffusion Step
To propagate astrological influence, the engine treats the 12 Astrological Houses as 12 vertices.
1. Computes raw energy vector **`E`** (length 12) by summing planet strengths per house, masking out indices where the house is "Sleeping".
2. Builds adjacency matrix **`A`** (12x12) based on canonical Lal Kitab aspect graphs (e.g. House 1 -> House 7).
3. Computes Degree Matrix **`D`** (diagonal sum of rows in A).
4. **Diffusion Pass**: `E_diffused = E + α(AE - DE)`
   - Constant `α` (Laplacian Alpha/Step Size) = `0.1`
5. Subtracts the `0.25` Rin drain from affected houses.
6. Normalises `E_diffused` cleanly bounds (0.0 to 1.0).
7. Averages the multiplier for a RuleHit's target houses, and mathematically scales the final underlying `RuleHit.magnitude`.

---

## 2. Dynamic Sigmoid Layer (`ProbabilityEngine`)

Once the Physics Engine is done mapping graph magnitudes, the Probability Engine maps the raw magnitudes to accurate Delivery Probabilities (0.05 to 0.95 caps).

The equation structure is:
$$ P = Ea \times 2.0 \times \sigma_{\text{raw}} \times T_{vp} \times D_{corr} $$

### 2.1 The Components

**A. Adaptive Sigmoid K**
- Limits scaling "flattop" cliffs.
- $k = {base\_k} + (|NatalScore| \times 0.5)$
- Maximum capped at `6.0`

**B. Expected Propensity ($E_a$)**
- Computes baseline "karmic likelihood" rooted in natal strength.
- $Ea = 0.25 + (NatalScore \times 0.08)$

**C. Raw Sigmoid Effect ($\sigma_{raw}$)**
- $\sigma = \frac{1}{1 + e^{-k \times AnnualMagnitude}}$

**D. Timing Vector Peak ($T_{vp}$)**
The delivery timing vector contains highly aggressive competitive tie-breaker multipliers designed to heavily isolate specific event years in the Top-3 ranks:
- **Baseline Window**: If current age falls in planet's canonical maturity window (e.g., Jupiter 16-21) -> `x1.2` factor.
- **Penalty Window**: If age is > 10 years past window -> `x0.8` factor.
- **Exact Hit Tie-Breaker**: If exactly the canonical age (+/- 1 year limit) -> `x5.0` multiplier!
- **35-Year Cycle Synergy**: 
   - Ruler matches the planet: `x2.0`
   - Ruler is best friend to planet: `x1.5`
- *Note:* Verified executed remedies append exactly +10% per safe remedy.

**E. Age Decay / Distance Correction ($D_{corr}$)**
- Under age 50: `1.0`. 
- Over age 50: Subtracts `-0.005` factor (0.5%) per year to simulate lifecycle deceleration (max cap at `0.5`).
