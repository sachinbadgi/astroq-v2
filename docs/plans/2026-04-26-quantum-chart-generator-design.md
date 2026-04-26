# Quantum Chart Generator Design

## Goal
Implement a completely new feature to generate natal and annual charts using quantum computing concepts (tertiary states, matrices, and unitary operators) as outlined in the Lal Kitab and Quantum Computing Comparison document. This module serves as a starting point for the astrology prediction engine, completely parameterizing the rules to support an external auto-research optimization loop.

## Constraints & Requirements
- Must use a tertiary logic model for planetary states: `-1` (destructive), `0` (dormant/superposed), `1` (constructive).
- Must encapsulate the 120-year Varshphal mapping as a mathematical transformation matrix (Unitary Operator).
- Must expose all structural weights and thresholds cleanly via a configuration to allow tuning by an auto-research script.
- Must be isolated in a new sub-folder (`backend/astroq/quantum_engine`).

## Architecture & Data Flow

### Matrix-Backed Engine
The system will treat the Lal Kitab grammar as linear algebra and quantum logic operations, utilizing `numpy` (or pure Python matrices) for speed and optimization compatibility.

#### 1. The Natal State Vector (Qubits)
The chart is initialized as a $12 \times 9$ matrix (12 Houses, 9 Planets). Each cell holds the probability amplitude/state of a planet in a house. The states are defined as:
* ` 1`: Constructive/Benefic amplitude (Exalted, Pakka Ghar, or receiving benefic coupling)
* ` 0`: Superposed/Dormant amplitude (Sleeping planet, doubtful)
* `-1`: Destructive/Malefic amplitude (Debilitated, receiving destructive interference)

#### 2. The Unitary Operator (120-Year Varshphal Matrix)
The 120-year rotation mapping will be encoded as transformation matrices. To calculate the state vector for Age 35, the engine will multiply the Natal State Vector by the Age 35 Transformation Matrix, propagating the planetary states to their new annual positions.

#### 3. Entanglement & Logic Gates (Masnui Grah & Aspects)
Planetary combinations and aspects (e.g., Sun + Venus forming Artificial Mercury) act as quantum logic gates (like a CNOT gate). If the condition is met, the individual planetary vectors are collapsed into a new composite state vector. 

#### 4. Auto-Research Tuning Interface
All core structural thresholds—such as Aspect Coupling Coefficients (100% sight, 50% sight) and Strength Weights—will be extracted into a `quantum_weights.json` (or similar config). The auto-research framework will mutate this file to adjust the steepness of probability curves or flip thresholds, and immediately measure the outcome.

## Sub-components
* `config.py`: Loads the `quantum_weights.json` for the auto-research loop.
* `matrix_models.py`: Defines the `QuantumStateVector` and `VarshphalMatrix`.
* `chart_generator.py`: Initializes the natal state matrix based on astronomical placement and applies the unitary operators.
* `entanglement.py`: Contains the logic gates for Masnui Grah and Aspect interference.

## Testing & Verification
The engine will be tested by verifying that applying the Varshphal Matrix manually yields the exact same house mapping as the deterministic `ChartGenerator.YEAR_MATRIX` but retains the computed quantum amplitudes.
