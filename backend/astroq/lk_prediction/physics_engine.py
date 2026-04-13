"""
Lal Kitab Energetic Physics Engine
====================================
Pre-processing layer called by pipeline.py AFTER rules_engine.evaluate_chart()
and BEFORE the Dempster-Shafer aggregation loop.

Annotates RuleHit objects with:
  - mutability: "FLEXIBLE" | "FIXED" | "SYNTHETIC" | "SYSTEMIC_LEAK" | "SLEEPING" | "GATED"
  - virtual_planet: dict | None
  - structural_status: dict | None

Does NOT modify the RuleHit dataclass definition. Uses setattr() to attach
extra attributes dynamically. Does NOT re-derive data already computed
by GrammarAnalyser -- reads chart["masnui_grahas_formed"],
chart["house_status"], chart["lal_kitab_debts"], and enriched[p]["sleeping_status"].

Mutability priority (highest wins):
  FIXED > SYNTHETIC > SYSTEMIC_LEAK > GATED > SLEEPING > FLEXIBLE
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import numpy as np

from astroq.lk_prediction.data_contracts import RuleHit
from astroq.lk_prediction.lk_constants import (
    HOUSE_ASPECT_TARGETS,
    PLANET_DEBILITATION,
    PLANET_EXALTATION,
    PLANET_PAKKA_GHAR,
)

logger = logging.getLogger("astroq.physics_engine")

# Mutability priority (lower index = higher priority)
_PRIORITY: list[str] = ["FIXED", "SYNTHETIC", "SYSTEMIC_LEAK", "GATED", "SLEEPING", "FLEXIBLE"]

# Constants
_FIXED_MAGNITUDE: float = 0.9       # Saturate DST evidence for FIXED nodes (Dirichlet Option B)
_RIN_DRAIN_RATE: float = 0.25       # Subtracted from house energy multiplier for Rin-affected houses
_LAPLACIAN_ALPHA: float = 0.1       # Step size for heat-diffusion pass (small = stable)
_RIN_SENTINEL: str = "[COLLECTIVE_ACTIVATION_REQUIRED]"


def _higher_priority(current: str, candidate: str) -> str:
    """Return whichever mutability label has higher priority."""
    return candidate if _PRIORITY.index(candidate) < _PRIORITY.index(current) else current


class PhysicsEngine:
    """
    Annotates RuleHits with energetic topology flags and applies
    Graph Laplacian diffusion scaling to rule magnitudes.

    Usage::

        annotated_hits = PhysicsEngine().process(chart, rule_hits, enriched)

    All passes run in a fixed order.  The mutability priority table ensures
    that higher-priority tags always win (e.g. FIXED always overrides SLEEPING).
    """

    def process(
        self,
        chart: Dict[str, Any],
        rule_hits: List[RuleHit],
        enriched: Dict[str, Any],
    ) -> List[RuleHit]:
        """
        Main entry point.  Annotates and scales rule_hits in-place, returns list.

        Parameters
        ----------
        chart     : ChartData dict (grammar-analysed, contains house_status,
                    masnui_grahas_formed, lal_kitab_debts, planets_in_houses)
        rule_hits : RuleHit objects from rules_engine.evaluate_chart()
        enriched  : EnrichedPlanet dicts from strength_engine + grammar_analyser
                    (contains sleeping_status, states, house, strength_total)
        """
        if not rule_hits:
            return rule_hits

        # ── Pass 0: Initialise dynamic attrs on every hit ─────────────────────
        for hit in rule_hits:
            setattr(hit, "mutability", "FLEXIBLE")
            setattr(hit, "virtual_planet", None)
            setattr(hit, "structural_status", None)
            # remedy_hints: RuleHit doesn't have this field; attach dynamically
            if not hasattr(hit, "remedy_hints"):
                setattr(hit, "remedy_hints", [])

        # ── Pass 1: Build Petri Net house state array ─────────────────────────
        house_states = self._build_house_states(chart)

        # ── Pass 2: SLEEPING planet / GATED house ─────────────────────────────
        self._tag_sleeping_gated(rule_hits, enriched, house_states)

        # ── Pass 3: FIXED — Pakka Ghar / Exaltation / Debilitation ───────────
        self._tag_fixed(rule_hits, enriched)

        # ── Pass 4: SYNTHETIC — Masnui conjunctions ───────────────────────────
        self._tag_synthetic(rule_hits, chart)

        # ── Pass 5: SYSTEMIC_LEAK — Rin / Karmic Debt ─────────────────────────
        self._tag_rin(rule_hits, chart)

        # ── Pass 6: Graph Laplacian diffusion — scale magnitudes ──────────────
        house_multipliers = self._compute_laplacian_multipliers(chart, enriched, house_states)
        self._apply_laplacian_scaling(rule_hits, house_multipliers)

        return rule_hits

    # ──────────────────────────────────────────────────────────────────────────
    # Pass 1: Petri Net house state array
    # ──────────────────────────────────────────────────────────────────────────

    def _build_house_states(self, chart: Dict[str, Any]) -> np.ndarray:
        """
        Returns np.ndarray shape (12,): 1.0 = awake, 0.0 = sleeping.
        Source: chart["house_status"] populated by GrammarAnalyser.
        """
        states = np.ones(12, dtype=float)
        house_status = chart.get("house_status", {})
        for h_idx in range(12):
            if house_status.get(str(h_idx + 1), "").lower() == "sleeping house":
                states[h_idx] = 0.0
        return states

    # ──────────────────────────────────────────────────────────────────────────
    # Pass 2: SLEEPING / GATED tagging
    # ──────────────────────────────────────────────────────────────────────────

    def _tag_sleeping_gated(
        self,
        rule_hits: List[RuleHit],
        enriched: Dict[str, Any],
        house_states: np.ndarray,
    ) -> None:
        """
        SLEEPING: primary target planet's sleeping_status contains "sleeping".
        GATED:    primary target planet sits in a house with state == 0.0
                  (but planet itself is not sleeping).
        Does not override a higher-priority mutability already set.
        """
        for hit in rule_hits:
            current = getattr(hit, "mutability")
            for planet in hit.primary_target_planets:
                ep = enriched.get(planet, {})
                h = ep.get("house", 0)
                sleeping_status = ep.get("sleeping_status", "Awake")
                if sleeping_status and "sleeping" in sleeping_status.lower():
                    current = _higher_priority(current, "SLEEPING")
                elif h and 1 <= h <= 12 and house_states[h - 1] == 0.0:
                    current = _higher_priority(current, "GATED")
            setattr(hit, "mutability", current)

    # ──────────────────────────────────────────────────────────────────────────
    # Pass 3: FIXED tagging (Dirichlet boundary)
    # ──────────────────────────────────────────────────────────────────────────

    def _tag_fixed(self, rule_hits: List[RuleHit], enriched: Dict[str, Any]) -> None:
        """
        FIXED: planet is in Pakka Ghar, Exaltation, Debilitation, or has
        "Fixed House Lord" state flag from GrammarAnalyser.
        When FIXED, magnitude is saturated to _FIXED_MAGNITUDE (0.9) so DST
        receives maximum evidence mass — the Dirichlet "infinite thermal mass" analog.
        """
        for hit in rule_hits:
            is_fixed = False
            for planet in hit.primary_target_planets:
                ep = enriched.get(planet, {})
                house = ep.get("house", 0)
                if not house:
                    continue
                if PLANET_PAKKA_GHAR.get(planet) == house:
                    is_fixed = True
                    break
                if house in PLANET_EXALTATION.get(planet, []):
                    is_fixed = True
                    break
                if house in PLANET_DEBILITATION.get(planet, []):
                    is_fixed = True
                    break
                if any("fixed house lord" in s.lower() for s in ep.get("states", [])):
                    is_fixed = True
                    break
            if is_fixed:
                setattr(hit, "mutability", _higher_priority(getattr(hit, "mutability"), "FIXED"))
                hit.magnitude = _FIXED_MAGNITUDE

    # ──────────────────────────────────────────────────────────────────────────
    # Pass 4: SYNTHETIC tagging (Masnui / Reaction-Diffusion)
    # ──────────────────────────────────────────────────────────────────────────

    def _tag_synthetic(self, rule_hits: List[RuleHit], chart: Dict[str, Any]) -> None:
        """
        SYNTHETIC: rule's primary planet is a component of an active Masnui
        formation.  Reads chart["masnui_grahas_formed"] — pre-computed by
        GrammarAnalyser.detect_masnui().  Attaches virtual_planet dict.
        Does not fire for FIXED hits (FIXED wins per priority table).
        """
        masnuis = chart.get("masnui_grahas_formed", [])
        if not masnuis:
            return

        # Build lookup: lowercase planet name -> list of Masnui dicts
        parent_to_masnui: dict[str, list[dict]] = {}
        for m in masnuis:
            for comp in m.get("components", []):
                parent_to_masnui.setdefault(comp.lower(), []).append(m)

        for hit in rule_hits:
            if getattr(hit, "mutability") == "FIXED":
                continue
            for planet in hit.primary_target_planets:
                matches = parent_to_masnui.get(planet.lower(), [])
                if matches:
                    m = matches[0]
                    setattr(hit, "mutability",
                            _higher_priority(getattr(hit, "mutability"), "SYNTHETIC"))
                    setattr(hit, "virtual_planet", {
                        "name": m.get("masnui_graha_name", "Unknown"),
                        "type": "MASNUI",
                        "magnitude": float(m.get("magnitude", 1.0)),
                    })
                    break  # one Masnui per hit is sufficient

    # ──────────────────────────────────────────────────────────────────────────
    # Pass 5: SYSTEMIC_LEAK tagging (Rin / Thermodynamic Sink)
    # ──────────────────────────────────────────────────────────────────────────

    def _tag_rin(self, rule_hits: List[RuleHit], chart: Dict[str, Any]) -> None:
        """
        SYSTEMIC_LEAK: rule's target house is an active Rin-affected house.
        Reads chart["lal_kitab_debts"] — pre-computed by GrammarAnalyser.
        Attaches structural_status and appends [COLLECTIVE_ACTIVATION_REQUIRED]
        to remedy_hints.  Does not modify RemedyEngine.
        FIXED hits are skipped.
        """
        debts = chart.get("lal_kitab_debts", [])
        if not debts:
            return

        # Build lookup: house -> debt_name for all active debts
        active_debt_houses: dict[int, str] = {}
        for debt in debts:
            if not debt.get("active", False):
                continue
            debt_name = debt.get("debt_name", "Unknown Rin")
            for h in debt.get("trigger_houses", []):
                active_debt_houses[h] = debt_name

        if not active_debt_houses:
            return

        for hit in rule_hits:
            current = getattr(hit, "mutability")
            if current == "FIXED":
                continue
            for h in hit.target_houses:
                if h in active_debt_houses:
                    setattr(hit, "mutability",
                            _higher_priority(current, "SYSTEMIC_LEAK"))
                    setattr(hit, "structural_status", {
                        "is_rina": True,
                        "debt_type": active_debt_houses[h],
                        "drain_rate": -_RIN_DRAIN_RATE,
                    })
                    remedy_hints = getattr(hit, "remedy_hints", [])
                    if _RIN_SENTINEL not in remedy_hints:
                        remedy_hints.append(_RIN_SENTINEL)
                        setattr(hit, "remedy_hints", remedy_hints)
                    break  # one Rin per hit is sufficient

    # ──────────────────────────────────────────────────────────────────────────
    # Pass 6: Graph Laplacian diffusion
    # ──────────────────────────────────────────────────────────────────────────

    def _build_house_energy_vector(
        self,
        enriched: Dict[str, Any],
        house_states: np.ndarray,
    ) -> np.ndarray:
        """
        12-element raw energy vector: sum of planet strength_totals per house,
        masked by the Petri Net house_states array.
        """
        energy = np.zeros(12, dtype=float)
        for ep in enriched.values():
            h = ep.get("house", 0)
            if 1 <= h <= 12:
                energy[h - 1] += max(0.0, float(ep.get("strength_total", 0.0)))
        energy *= house_states
        return energy

    def _compute_laplacian_multipliers(
        self,
        chart: Dict[str, Any],
        enriched: Dict[str, Any],
        house_states: np.ndarray,
    ) -> np.ndarray:
        """
        Computes per-house energy multipliers (shape: 12, values: 0.0–1.0).

        Algorithm:
          1. Build raw house energy vector E from planet strengths
          2. Build symmetric 12x12 adjacency matrix A from HOUSE_ASPECT_TARGETS
          3. Compute degree matrix D (diagonal of row sums)
          4. One heat-diffusion step: E' = E + α*(A @ E - D @ E)
          5. Apply Rin drain (-_RIN_DRAIN_RATE) to Rin-affected houses
          6. Normalise to [0.0, 1.0]

        Multipliers are used to *scale* existing rule magnitudes (Option B),
        not to replace them.
        """
        E = self._build_house_energy_vector(enriched, house_states)

        # Build symmetric adjacency matrix from Lal Kitab aspect targets
        A = np.zeros((12, 12), dtype=float)
        for h, targets in HOUSE_ASPECT_TARGETS.items():
            if not (1 <= h <= 12):
                continue
            for t in targets:
                if 1 <= t <= 12:
                    A[h - 1][t - 1] = 1.0
                    A[t - 1][h - 1] = 1.0  # symmetrise

        D = np.diag(A.sum(axis=1))
        E_diffused = E + _LAPLACIAN_ALPHA * (A @ E - D @ E)

        # Apply Rin drain to active debt houses
        for debt in chart.get("lal_kitab_debts", []):
            if not debt.get("active", False):
                continue
            for h in debt.get("trigger_houses", []):
                if 1 <= h <= 12:
                    E_diffused[h - 1] = max(0.0, E_diffused[h - 1] - _RIN_DRAIN_RATE)

        # Normalise to 0–1
        max_val = float(E_diffused.max())
        if max_val > 0.0:
            multipliers = np.clip(E_diffused / max_val, 0.0, 1.0)
        else:
            multipliers = np.ones(12, dtype=float)

        return multipliers

    def _apply_laplacian_scaling(
        self, rule_hits: List[RuleHit], multipliers: np.ndarray
    ) -> None:
        """
        Scale each RuleHit's magnitude by the MEAN of its target houses' multipliers.
        FIXED hits are skipped (already saturated to _FIXED_MAGNITUDE).
        Hits with no valid target houses are left unchanged.
        """
        for hit in rule_hits:
            if getattr(hit, "mutability") == "FIXED":
                continue
            if not hit.target_houses:
                continue
            valid = [multipliers[h - 1] for h in hit.target_houses if 1 <= h <= 12]
            if not valid:
                continue
            scale = float(np.mean(valid))
            hit.magnitude = round(float(hit.magnitude) * scale, 4)
