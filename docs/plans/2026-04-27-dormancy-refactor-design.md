# Design Document: Dormancy (Soyi Hui) Logic Refactor
**Date**: 2026-04-27
**Topic**: High-Fidelity 1952 Methodology Dormancy Engine

## Overview
This document outlines the architectural refactor of the Lal Kitab Dormancy (Soyi Hui) logic. The goal is to move from a static, fragmented implementation to a unified, thermodynamic "Sachin Graph" engine that captures the nuances of the 1952 Goswami methodology.

## Design Principles
1. **Absolute Awakening (Lamp Houses)**: Planets in Houses 1, 7, and 9 are "Swayam Jaagi" (Self-Awakened). Their presence forces house activation regardless of dignity.
2. **The Leakage Principle (House 2 Sustenance)**: House 2 acts as the "Roof" (Chhat). If H2 is blank or afflicted, the energy of an awake planet "leaks," leading to a confidence/magnitude penalty in predictions.
3. **Impact-Driven Awakening (Dynamic State)**: Dormancy is not just a static pre-calculation. It can be dynamically flipped via external triggers like **Takkar (Sudden Strike)** or **Buniyad (Foundation)**.

## Architectural Components

### 1. `DormancyEngine` (The Authority)
- **Static Check**: Evaluates Standard Dormancy (Rule 1: Forward, Rule 2: Aspects) + Lamp Houses + Munsif Rule.
- **Dynamic Check**: Evaluates Takkar (Collision) and Buniyad (Foundation) to "startle" dormant planets awake.
- **Sustenance Evaluation**: Checks House 2 state to calculate the `Sustenance_Factor`.

### 2. `VarshphalTimingEngine` (The Consumer)
- Replaces internal `_is_planet_dormant` with calls to `DormancyEngine`.
- Integrates the `Sustenance_Factor` into confidence scoring.

## Mathematical Logic

### Sustenance Factor (H2)
- **Occupied by Friend/Pakka**: 1.2x (Multiplied success)
- **Blank**: 0.6x (Leakage penalty)
- **Occupied by Enemy**: 0.4x (Malefic interference)

### Result Integrity Formula
$$Result\_Integrity = (Activation\_Potential) \times (Sustenance\_Factor_{H2})$$
- *Activation_Potential*: 1.0 if Awake, 0.0 if Dormant.

## Execution Flow
1. **Step 1: Static Dormancy Mapping** (Base year state).
2. **Step 2: Impact Identification** (Takkar & Buniyad).
3. **Step 3: Dynamic State Flip** (Startled Awakening).
4. **Step 4: Sustenance Calculation** (H2 Filter).
5. **Step 5: Final Scoring** (Prediction Output).

## Quality of Wakefulness
- **Startled Malefic (Bhadka Hua)**: Planets awakened by Takkar deliver results with initial friction/jerk.
- **Supportive Awakening**: Planets awakened by Buniyad deliver results with stability.
