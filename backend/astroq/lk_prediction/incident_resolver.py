from dataclasses import dataclass
from typing import Dict, List, Any
from .lk_constants import HOUSE_ASPECT_DATA

@dataclass
class Incident:
    type: str # Takkar, Sanctuary
    source: str
    target: str
    strength: float = 1.0
    trauma_weight: float = 0.0

class IncidentResolver:
    """
    Scans annual chart geometric pairs to detect 'Ghatna' (Incidents).
    Uses canonical House Aspect definitions for Confrontation and Foundation.
    """

    # Primary Strikes: Direct/Geometric Collisions (1/8, 12/2)
    PRIMARY_STRIKES = {
        (1, 8), (8, 1),
        (12, 2), (2, 12)
    }
    
    # Secondary Strikes: Opposition/BilMukabil (1/7)
    SECONDARY_STRIKES = {
        (1, 7), (7, 1)
    }

    def detect_incidents(self, positions: Dict[str, int]) -> List[Incident]:
        """
        Scans annual chart geometric pairs to detect 'Ghatna' (Incidents).
        Uses ASPECT_STRENGTH_DATA from lk_constants for canonical weighting.
        """
        from .lk_constants import ASPECT_STRENGTH_DATA
        incidents = []
        
        # Reverse lookup house to planets
        house_to_planets = {}
        for p, h in positions.items():
            if h not in house_to_planets:
                house_to_planets[h] = []
            house_to_planets[h].append(p)
            
        for p_source, p_house in positions.items():
            aspect_data = HOUSE_ASPECT_DATA.get(p_house, {})
            
            # 1. Takkar (Confrontation)
            targets = []
            
            # Canonical confrontation
            confrontation_h = aspect_data.get("Confrontation")
            if confrontation_h:
                targets.append(confrontation_h)
            
            # Explicit Primary/Secondary Strikes
            for h_target in range(1, 13):
                if (p_house, h_target) in self.SECONDARY_STRIKES or (p_house, h_target) in self.PRIMARY_STRIKES:
                    targets.append(h_target)

            # Deduplicate targets
            final_targets = sorted(set(targets))

            for target_house in final_targets:
                if target_house in house_to_planets:
                    for p_target in house_to_planets[target_house]:
                        # ── CANONICAL WEIGHTING ──────────────────────────────
                        # Use ASPECT_STRENGTH_DATA to determine impact.
                        # If the value is negative, it's a Malefic Strike (Trauma).
                        # If positive, it's a Benefic Impact (Lower Trauma or Sanctuary).
                        
                        aspect_strength = ASPECT_STRENGTH_DATA.get(p_source, {}).get(p_target, 0.0)
                        
                        trauma_weight = 0.0
                        if aspect_strength < 0:
                            # Malefic Strike: Magnitude of hostility is the trauma
                            trauma_weight = abs(aspect_strength)
                        elif aspect_strength > 0:
                            # Benefic Contact: Soft impact (0.1) or handled by Sanctuary
                            trauma_weight = 0.1
                        
                        incidents.append(Incident(
                            type="Takkar",
                            source=p_source,
                            target=p_target,
                            trauma_weight=trauma_weight
                        ))
            
            # 2. Sanctuary (Foundation/Buniyad)
            sanctuary_target_house = aspect_data.get("Foundation")
            if sanctuary_target_house and sanctuary_target_house in house_to_planets:
                for p_target in house_to_planets[sanctuary_target_house]:
                    incidents.append(Incident(
                        type="Sanctuary",
                        source=p_source,
                        target=p_target,
                        trauma_weight=0.0
                    ))
                        
        return incidents
