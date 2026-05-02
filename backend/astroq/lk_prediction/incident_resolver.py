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
        incidents = []
        
        # Reverse lookup house to planets
        house_to_planets = {}
        for p, h in positions.items():
            if h not in house_to_planets:
                house_to_planets[h] = []
            house_to_planets[h].append(p)
            
        for p_name, p_house in positions.items():
            aspect_data = HOUSE_ASPECT_DATA.get(p_house, {})
            
            # 1. Takkar (Confrontation)
            targets = []
            
            # Canonical confrontation
            confrontation_h = aspect_data.get("Confrontation")
            if confrontation_h:
                targets.append((confrontation_h, 1.0 if (p_house, confrontation_h) in self.PRIMARY_STRIKES else 0.5))
            
            # Explicit Primary/Secondary Strikes
            for h_target in range(1, 13):
                if (p_house, h_target) in self.SECONDARY_STRIKES:
                    targets.append((h_target, 0.5))
                elif (p_house, h_target) in self.PRIMARY_STRIKES and h_target != confrontation_h:
                    targets.append((h_target, 1.0))

            # Deduplicate targets by house, keeping max weight
            final_targets = {}
            for h, w in targets:
                final_targets[h] = max(final_targets.get(h, 0.0), w)

            for target_house, weight in final_targets.items():
                if target_house in house_to_planets:
                    for target_p in house_to_planets[target_house]:
                        incidents.append(Incident(
                            type="Takkar",
                            source=p_name,
                            target=target_p,
                            trauma_weight=weight
                        ))
            
            # 2. Sanctuary (Foundation/Buniyad)
            sanctuary_target_house = aspect_data.get("Foundation")
            if sanctuary_target_house and sanctuary_target_house in house_to_planets:
                for target_p in house_to_planets[sanctuary_target_house]:
                    incidents.append(Incident(
                        type="Sanctuary",
                        source=p_name,
                        target=target_p,
                        trauma_weight=0.0
                    ))
                        
        return incidents
