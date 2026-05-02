from dataclasses import dataclass, field
from typing import Dict, Optional

@dataclass
class RemedyNexus:
    remedy_id: str
    inception_age: int
    recoil_multiplier: float = 2.0
    maintenance_window_years: int = 10

@dataclass
class PlanetaryState:
    base_state: str = "Dormant"
    modifier: str = "None" # None, Startled Malefic, Supported
    trauma_points: float = 0.0
    leak_threshold: float = 0.5
    burst_threshold: float = 3.0
    remedy_count: int = 0
    remedy_active_until: int = 0
    is_manda: bool = False
    is_leaking: bool = False
    is_burst: bool = False
    remedy_nexus: Optional[RemedyNexus] = None
    scapegoat_hit_count: int = 0
    SCAPEGOAT_EXHAUSTION_THRESHOLD: int = 3

class StateLedger:
    def __init__(self):
        self.planets = {p: PlanetaryState() for p in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]}
    
    def get_planet_state(self, name: str) -> PlanetaryState:
        # C-2 FIX: Strip "Masnui " prefix before lookup so Masnui planets resolve
        # to the same PlanetaryState as their base archetype. Return a default
        # PlanetaryState (rather than raising KeyError) for completely unknown names.
        base = name.replace("Masnui ", "") if name.startswith("Masnui ") else name
        return self.planets.get(base, PlanetaryState())

    def apply_trauma(self, planet: str, points: float):
        """Permanent accumulation of trauma (Scarring Model)."""
        p = self.planets[planet]
        p.trauma_points += points
        self._update_thresholds(planet)

    def apply_strike_impact(self, planet: str, points: float, is_startled: bool):
        """
        Deep Module: Encapsulates how a geometric strike (Takkar) affects state.
        Determines if the planet becomes 'Startled Malefic' or just 'Friction'.
        """
        self.apply_trauma(planet, points)
        state = self.get_planet_state(planet)
        
        # If the strike causes awakening or hits an awake planet
        if is_startled:
            state.modifier = "Startled Malefic"
        elif state.modifier == "None":
            state.modifier = "Friction"

    def apply_remedy(self, planet: str, age: int, remedy_id: str):
        """Applies a remedy and creates a maintenance nexus."""
        p = self.planets[planet]
        p.remedy_count += 1
        p.remedy_nexus = RemedyNexus(
            remedy_id=remedy_id,
            inception_age=age
        )

    def get_recoil_multiplier(self, planet: str, current_age: int) -> float:
        """Returns the recoil multiplier (Structural Debt) if maintenance window expired."""
        p = self.planets[planet]
        if not p.remedy_nexus:
            return 1.0
        
        nexus = p.remedy_nexus
        age_gap = current_age - nexus.inception_age
        
        if age_gap > nexus.maintenance_window_years:
            return nexus.recoil_multiplier
            
        return 1.0

    def check_and_fire_recoil(self, planet: str, current_age: int) -> bool:
        """
        Checks if maintenance window expired. If so, fires +2.0 trauma once
        and clears the nexus. Returns True if recoil fired.
        """
        p = self.planets[planet]
        if not p.remedy_nexus:
            return False
        
        nexus = p.remedy_nexus
        age_gap = current_age - nexus.inception_age
        
        if age_gap > nexus.maintenance_window_years:
            # FIRE RECOIL
            self.apply_trauma(planet, 2.0)
            p.remedy_nexus = None # Nexus cleared after recoil fire
            return True
        return False

    def record_scapegoat_hit(self, scapegoat_planet: str) -> None:
        """Records absorbed scapegoat hit + minor trauma (0.3 pts)."""
        base = scapegoat_planet.replace("Masnui ", "") if scapegoat_planet.startswith("Masnui ") else scapegoat_planet
        if base in self.planets:
            self.planets[base].scapegoat_hit_count += 1
            self.apply_trauma(base, 0.3)

    def is_scapegoat_exhausted(self, scapegoat_planet: str) -> bool:
        """True if scapegoat absorbed >= SCAPEGOAT_EXHAUSTION_THRESHOLD hits."""
        base = scapegoat_planet.replace("Masnui ", "") if scapegoat_planet.startswith("Masnui ") else scapegoat_planet
        state = self.planets.get(base)
        if not state:
            return False
        return state.scapegoat_hit_count >= state.SCAPEGOAT_EXHAUSTION_THRESHOLD

    def apply_dirty_start_penalty(self) -> None:
        """
        Called at Age 35→36 cycle boundary.
        Reduces burst_threshold for traumatized planets — implements
        'Mechanical Degradation' into Cycle 2 (cite: 2176, 2179).
        Planets with > 2.0 trauma get 30% lower threshold (burst faster).
        Planets with 0.5-2.0 trauma get 15% lower threshold.
        Clean planets (< 0.5 trauma) are unaffected.
        """
        for planet, state in self.planets.items():
            if state.trauma_points >= 2.0:
                state.burst_threshold = max(1.0, state.burst_threshold * 0.70)
            elif state.trauma_points >= 0.5:
                state.burst_threshold = max(1.0, state.burst_threshold * 0.85)
            # else: clean — no change

    def _update_thresholds(self, planet: str):
        """Updates Leaking and Burst status based on cumulative trauma and dynamic thresholds."""
        p = self.planets[planet]
        
        # Natural Resilience Modifiers (Lower threshold = faster bursting)
        # Moon/Mercury/Venus are softer; Mars/Saturn/Sun are tougher
        if planet in ["Moon", "Mercury", "Venus"]:
            p.leak_threshold = 0.3
            p.burst_threshold = 2.0
        elif planet in ["Mars", "Saturn", "Sun", "Rahu", "Ketu"]:
            p.leak_threshold = 0.8
            p.burst_threshold = 4.0
        # Jupiter remains baseline (0.5 / 3.0)
        
        if p.trauma_points > p.burst_threshold:
            p.is_burst = True
            p.is_leaking = False
            p.modifier = "Burst"
        elif p.trauma_points >= p.leak_threshold:
            p.is_burst = False
            p.is_leaking = True
            p.modifier = "Leaking"

    def get_leakage_multiplier(self, name: str) -> float:
        """
        Calculates the efficiency multiplier based on trauma state.
        Burst: 0.0 (Totally malefic/suppressed)
        Leaking: 0.5 (50% efficiency)
        Startled Malefic: 2.0 (High friction)
        """
        p = self.planets[name]
        if p.is_burst:
            return 0.0
        if p.modifier == "Startled Malefic":
            return 2.0
        if p.is_leaking:
            return 0.5
        
        # Base multiplier (Standard decay if any trauma exists but below Leaking threshold)
        return max(0.0, 1.0 - (0.1 * p.trauma_points))
