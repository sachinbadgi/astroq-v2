from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

@dataclass
class RemedyNexus:
    remedy_id: str
    inception_age: int
    recoil_multiplier: float = 2.0
    maintenance_window_years: int = 10

@dataclass
class PlanetaryState:
    base_state: str = "Dormant"
    modifier: str = "None" # None, Startled Malefic, Supported, Blunt, Leaking, Burst
    trauma_points: float = 0.0
    leak_threshold: float = 0.5
    burst_threshold: float = 3.0
    base_burst_threshold: Optional[float] = None
    remedy_count: int = 0
    remedy_active_until: int = 0
    is_manda: bool = False
    is_leaking: bool = False
    is_burst: bool = False
    is_awake: bool = False
    last_awakened_age: Optional[int] = None
    remedy_nexus: Optional[RemedyNexus] = None
    scapegoat_hit_count: int = 0
    SCAPEGOAT_EXHAUSTION_THRESHOLD: int = 3
    sustenance_factor: float = 1.0

class StateLedger:
    def __init__(self):
        self.planets = {p: PlanetaryState() for p in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]}
        for p in self.planets:
            self._update_thresholds(p, init=True)
    
    def _resolve_base(self, name: str) -> str:
        """Resolves Masnui variants to their base archetype."""
        return name.replace("Masnui ", "").split(" (")[0] if name.startswith("Masnui ") else name

    def get_planet_state(self, name: str) -> PlanetaryState:
        base = self._resolve_base(name)
        return self.planets.get(base, PlanetaryState())

    def evolve_state(self, context: Any):
        """
        FORENSIC EVOLUTION: Advances the state of all planets for the current year.
        Handles Lamp House (1,7,9) activation, H2 leakage, and state persistence.
        """
        current_age = context.age
        
        # 1. Age 36 Carry-Over (Mechanical Degradation)
        if current_age == 36:
            self.apply_dirty_start_penalty()

        for planet in self.planets:
            state = self.get_planet_state(planet)
            house = context.get_house(planet)
            
            # 2. Lamp Principle (Swayam Jaagi)
            # Houses 1, 7, 9 are Lamp Houses — always awake.
            if house in [1, 7, 9]:
                state.is_awake = True
                state.base_state = "Awake"
                state.last_awakened_age = current_age
            
            # 3. H2 Leakage Penalty (Blank House 2)
            # If H2 is blank, Lamp-activated planets suffer leakage.
            if state.is_awake and house in [1, 7, 9]:
                h2_occupants = context.chart.get_occupants(2)
                if not h2_occupants:
                    state.sustenance_factor = 0.6 # The "Baseless" Result
                else:
                    state.sustenance_factor = 1.0
            
            # 4. State Persistence (The Mechanical Memory)
            # If a planet was awakened at Age 28, it remains active for Age 29.
            if state.is_awake and state.last_awakened_age is not None:
                if current_age > state.last_awakened_age:
                    # Persistence check: does it stay awake?
                    # In Lal Kitab Forensic Logic, activation is permanent once triggered
                    # unless a massive malefic event "shuts it down" (Burst).
                    if state.is_burst:
                        state.is_awake = False
                        state.base_state = "Dormant"
            
            # 5. Manda (Blunt) Status
            # Trauma > 2.0 makes the planet permanently Blunt.
            if state.trauma_points > 2.0:
                state.is_manda = True
                state.modifier = "Blunt"

            self._update_thresholds(planet)

    def apply_trauma(self, planet: str, points: float, context: Optional[Any] = None):
        """
        Permanent accumulation of trauma (Scarring Model).
        Includes Dignity-Aware Scapegoat Rerouting.
        """
        base = self._resolve_base(planet)
        if base not in self.planets:
            return

        state = self.planets[base]
        
        # ── SCAPEGOAT REROUTING (Dignity-Aware) ─────────────────────────────
        # 1. Check Dignity (Rashi Phal allows rerouting, Graha Phal doesn't)
        fate_type = "RASHI_PHAL"
        if context:
            # We check the dominant karaka domain for this planet to get its fate_type
            from .lk_constants import KARAKA_DOMAIN_MAP
            domains = KARAKA_DOMAIN_MAP.get(base, [])
            if domains:
                fate_type = context.get_fate_type_for_domain(domains[0])
        
        # 2. Determine Rerouting Logic
        # Rashi Phal + Healthy: 100% Scapegoat Impact.
        # Graha Phal: 100% Native Impact.
        # Fatigued/Burst: Double Impact (Native + Scapegoat).
        
        can_reroute = (fate_type == "RASHI_PHAL")
        is_fatigued = (state.trauma_points > 1.5) # Fatigue threshold
        
        from .lk_constants import SCAPEGOATS
        scapegoat_targets = SCAPEGOATS.get(base, {})
        
        if not scapegoat_targets or not can_reroute:
            # Native takes the hit
            state.trauma_points += points
        elif is_fatigued or state.is_burst:
            # Double Hit (Native + Scapegoat)
            state.trauma_points += points
            for sg, weight in scapegoat_targets.items():
                if not self.is_scapegoat_exhausted(sg):
                    self.record_scapegoat_hit(sg, points * weight)
        else:
            # Full Scapegoat Reroute
            for sg, weight in scapegoat_targets.items():
                if not self.is_scapegoat_exhausted(sg):
                    self.record_scapegoat_hit(sg, points * weight)
                else:
                    # Scapegoat exhausted -> Native takes it anyway
                    state.trauma_points += (points * weight)

        self._update_thresholds(base)

    def apply_strike_impact(self, planet: str, points: float, is_startled: bool, context: Optional[Any] = None):
        """
        Deep Module: Encapsulates how a geometric strike (Takkar) affects state.
        Determines if the planet becomes 'Startled Malefic' or just 'Friction'.
        """
        self.apply_trauma(planet, points, context)
        state = self.get_planet_state(planet)
        
        if is_startled:
            state.modifier = "Startled Malefic"
            state.is_awake = True # Strikes wake planets up
        elif state.modifier == "None":
            state.modifier = "Friction"

    def apply_remedy(self, planet: str, age: int, remedy_id: str):
        """Applies a remedy and creates a maintenance nexus."""
        base = self._resolve_base(planet)
        if base in self.planets:
            p = self.planets[base]
            p.remedy_count += 1
            p.remedy_nexus = RemedyNexus(
                remedy_id=remedy_id,
                inception_age=age
            )

    def get_recoil_multiplier(self, planet: str, current_age: int) -> float:
        """Returns the recoil multiplier (Structural Debt) if maintenance window expired."""
        state = self.get_planet_state(planet)
        if not state.remedy_nexus:
            return 1.0
        
        nexus = state.remedy_nexus
        age_gap = current_age - nexus.inception_age
        
        if age_gap > nexus.maintenance_window_years:
            return nexus.recoil_multiplier
            
        return 1.0

    def check_and_fire_recoil(self, planet: str, current_age: int) -> bool:
        """Checks if maintenance window expired. Fires +2.0 trauma once."""
        base = self._resolve_base(planet)
        if base not in self.planets:
            return False
        
        p = self.planets[base]
        if not p.remedy_nexus:
            return False
        
        nexus = p.remedy_nexus
        age_gap = current_age - nexus.inception_age
        
        if age_gap > nexus.maintenance_window_years:
            # FIRE RECOIL (+2.0 trauma per Goswami rules)
            self.apply_trauma(planet, 2.0)
            p.remedy_nexus = None
            return True
        return False

    def record_scapegoat_hit(self, scapegoat_planet: str, points: float = 0.3) -> None:
        """Records absorbed scapegoat hit."""
        base = self._resolve_base(scapegoat_planet)
        if base in self.planets:
            self.planets[base].scapegoat_hit_count += 1
            # Add specific trauma to scapegoat
            self.planets[base].trauma_points += points
            self._update_thresholds(base)

    def is_scapegoat_exhausted(self, scapegoat_planet: str) -> bool:
        """True if scapegoat absorbed >= SCAPEGOAT_EXHAUSTION_THRESHOLD hits."""
        base = self._resolve_base(scapegoat_planet)
        state = self.planets.get(base)
        if not state:
            return False
        return state.scapegoat_hit_count >= state.SCAPEGOAT_EXHAUSTION_THRESHOLD

    def apply_dirty_start_penalty(self) -> None:
        """Age 36 boundary: Mechanical Degradation."""
        for planet, state in self.planets.items():
            if state.trauma_points >= 2.0:
                state.burst_threshold = max(1.0, state.burst_threshold * 0.70)
            elif state.trauma_points >= 0.5:
                state.burst_threshold = max(1.0, state.burst_threshold * 0.85)

    def _update_thresholds(self, planet: str, init: bool = False):
        """Updates Leaking and Burst status."""
        p = self.planets[planet]
        
        if init:
            if planet in ["Moon", "Mercury", "Venus"]:
                p.burst_threshold = 2.0
                p.leak_threshold = 0.3
            elif planet in ["Mars", "Saturn", "Sun", "Rahu", "Ketu"]:
                p.burst_threshold = 4.0
                p.leak_threshold = 0.8
            p.base_burst_threshold = p.burst_threshold
        
        # Dynamically set leak_threshold as a fraction of CURRENT burst_threshold
        # This ensures that if burst_threshold drops, leaking threshold also drops.
        p.leak_threshold = p.burst_threshold * (0.3 / 2.0 if planet in ["Moon", "Mercury", "Venus"] else 0.8 / 4.0)

        if p.trauma_points > p.burst_threshold:
            p.is_burst = True
            p.is_leaking = False
            p.modifier = "Burst"
        elif p.trauma_points >= p.leak_threshold:
            p.is_burst = False
            p.is_leaking = True
            p.modifier = "Leaking"
        else:
            p.is_burst = False
            p.is_leaking = False
            if p.modifier in ["Burst", "Leaking"]:
                p.modifier = "None"

    def get_leakage_multiplier(self, name: str) -> float:
        """Calculates efficiency multiplier."""
        state = self.get_planet_state(name)
        if state.is_burst:
            return 0.0
        if state.modifier == "Startled Malefic":
            return 2.0
        if state.is_leaking:
            return 0.5
        
        base_mult = max(0.0, 1.0 - (0.1 * state.trauma_points))
        # Apply sustenance factor (Blank H2 Penalty)
        return base_mult * state.sustenance_factor
