import logging
from dataclasses import dataclass
from typing import Dict, Tuple, Any
from .lk_constants import HOUSE_ASPECT_TARGETS, ENEMIES, PLANET_PAKKA_GHAR, HOUSE_ASPECT_DATA, get_35_year_ruler

@dataclass
class DormancyState:
    is_awake: bool
    wake_reason: str
    sustenance_factor: float
    is_startled: bool

logger = logging.getLogger(__name__)

class DormancyEngine:
    """
    DEEP MODULE: Encapsulates all canonical logic for planetary activation.
    Implements:
    1. Standard Dormancy (Rule 1: Forward Planets, Rule 2: Aspects)
    2. Munsif Rule (House 1 vs House 7 suppression)
    3. Lamp Principle (House 1, 7, 9 Force-Activation)
    4. House 2 Sustenance (The Leakage Principle)
    """

    FORCE_ACTIVATE_HOUSES = {1, 7, 9}

    def is_awake(self, planet: str, house: int, ppos: Dict[str, int], current_age: int = None) -> bool:
        """
        Determines if a planet is active for a specific annual chart state.
        Returns True if awake, False if dormant.
        """
        state = self.get_complex_state(planet, house, ppos, current_age)
        return state.is_awake

    def get_complex_state(self, planet: str, house: int, ppos: Dict[str, int], current_age: int = None) -> DormancyState:
        """
        Calculates the full activation state, including sustenance and dynamic triggers.
        Returns a DormancyState object.
        """
        if not house:
            return DormancyState(is_awake=False, wake_reason="None", sustenance_factor=0.0, is_startled=False)

        res = DormancyState(
            is_awake=False,
            wake_reason="Dormant",
            sustenance_factor=self.get_sustenance_factor(planet, house, ppos),
            is_startled=False
        )
        
        # 0. The 35-Year Cycle Ruler Override
        if current_age is not None:
            cycle_ruler = get_35_year_ruler(current_age)
            # Handle Masnui/Base planet comparison
            base_planet = planet.split(" ")[-1] if "Masnui" in planet else planet
            if base_planet == cycle_ruler:
                logger.debug(f"Cycle Ruler: {planet} is force-activated for age {current_age}.")
                res.is_awake = True
                res.wake_reason = "Cycle Ruler Active"
                return res

        # 1. The Munsif Rule (The Decisive Filter)
        if house == 7:
            is_h1_active = any(h == 1 for h in ppos.values())
            if not is_h1_active:
                logger.debug(f"Munsif Rule: {planet} in House 7 suppressed by blank House 1.")
                res.is_awake = False
                res.wake_reason = "Munsif Suppression"
                return res

        # 2. The Lamp Principle (Force-Activation)
        if house in self.FORCE_ACTIVATE_HOUSES:
            logger.debug(f"Lamp Principle: {planet} in House {house} force-activated.")
            res.is_awake = True
            res.wake_reason = "Lamp Principle"
            return res

        # 3. Dynamic Awakening (The Startle Triggers)
        # These are prioritized over standard rules to capture the 'Ghatna' (Incident).
        for p, p_data in ppos.items():
            if p == planet:
                continue
            
            h = p_data.get("house") if isinstance(p_data, dict) else p_data
            if h is None:
                continue
            if isinstance(h, list) and len(h) > 0:
                h = h[0]
            try:
                h = int(h)
            except (ValueError, TypeError):
                continue
            aspect_data = HOUSE_ASPECT_DATA.get(h, {})
            
            # Takkar (Confrontation)
            confrontation_target = aspect_data.get("Confrontation")
            if confrontation_target == house:
                res.is_awake = True
                res.wake_reason = "Startled (Takkar)"
                res.is_startled = True
                return res
            
            # Buniyad (Foundation)
            foundation_target = aspect_data.get("Foundation")
            if foundation_target == house:
                res.is_awake = True
                res.wake_reason = "Supportive (Buniyad)"
                return res

        # 4. Standard Activation Rules
        is_dormant, woken_by_fwd, woken_by_aspect = self.check_dormancy_state(planet, house, ppos)
        
        if not is_dormant:
            res.is_awake = True
            res.wake_reason = "Standard (Fwd)" if woken_by_fwd else "Standard (Aspect)"
            return res
            
        return res

    def get_sustenance_factor(self, planet: str, house: int, ppos: Dict[str, int]) -> float:
        """
        The Leakage Principle: House 2 acts as the 'Roof' (Chhat).
        Returns:
            1.2 if H2 is occupied by a Friend or is the planet's Pakka Ghar.
            0.6 if H2 is blank.
            0.4 if H2 is occupied by an Enemy.
        """
        h2_occupants = [p for p, h in ppos.items() if h == 2]
        
        if not h2_occupants:
            return 0.6 # Blank Roof = Leakage
            
        planet_enemies = ENEMIES.get(planet, [])
        is_afflicted = any(occ in planet_enemies for occ in h2_occupants)
        
        if is_afflicted:
            return 0.4 # Afflicted Roof = Malefic Interference
            
        return 1.2 # Occupied by Friend/Neutral = Sustained

    def check_dormancy_state(self, planet: str, house: int, ppos: Dict[str, int]) -> Tuple[bool, bool, bool]:
        """
        Standard dormancy calculation.
        Returns: (is_dormant, woken_by_fwd, woken_by_aspect)
        """
        # Rule 1: Houses 1 to 6 from the planet's house must be empty
        woken_by_fwd = False
        for offset in range(1, 7):
            target_house = ((house - 1 + offset) % 12) + 1
            if any(h == target_house for p, h in ppos.items() if p != planet):
                woken_by_fwd = True
                break

        # Rule 2: Planet must not be aspected by any other planet
        woken_by_aspect = False
        aspecting_houses = []
        for h1, targets in HOUSE_ASPECT_TARGETS.items():
            if house in targets:
                aspecting_houses.append(h1)

        for p, h in ppos.items():
            if p != planet and h in aspecting_houses:
                woken_by_aspect = True
                break

        is_dormant = not woken_by_fwd and not woken_by_aspect
        return is_dormant, woken_by_fwd, woken_by_aspect
