from dataclasses import dataclass
from typing import Dict, List, Any
from .lk_constants import HOUSE_ASPECT_DATA

@dataclass
class Incident:
    type: str # Takkar, Sanctuary
    source: str
    target: str
    strength: float = 1.0

class IncidentResolver:
    """
    Scans annual chart geometric pairs to detect 'Ghatna' (Incidents).
    Uses canonical House Aspect definitions for Confrontation and Foundation.
    """

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
            takkar_target_house = aspect_data.get("Confrontation")
            if takkar_target_house and takkar_target_house in house_to_planets:
                for target_p in house_to_planets[takkar_target_house]:
                    incidents.append(Incident(
                        type="Takkar",
                        source=p_name,
                        target=target_p
                    ))
            
            # 2. Sanctuary (Foundation/Buniyad)
            sanctuary_target_house = aspect_data.get("Foundation")
            if sanctuary_target_house and sanctuary_target_house in house_to_planets:
                for target_p in house_to_planets[sanctuary_target_house]:
                    incidents.append(Incident(
                        type="Sanctuary",
                        source=p_name,
                        target=target_p
                    ))
                        
        return incidents
