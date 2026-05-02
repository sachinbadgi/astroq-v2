from typing import Dict, List, Any, Optional, Set
from .data_contracts import ChartData, PlanetInHouse

class AstroChart:
    """
    DEEP MODULE: A smart wrapper around ChartData.
    Provides a consistent interface for planetary positions and house status,
    hiding the complexity of Masnui (artificial) vs standard planets.
    """

    def __init__(self, data: ChartData):
        self.data = data
        self.planets = data.get("planets_in_houses", {})
        self.masnuis = data.get("masnui_grahas_formed", [])
        self._house_occupants: Dict[int, List[str]] = self._index_houses()

    def _index_houses(self) -> Dict[int, List[str]]:
        """Pre-indexes which planets are in which houses."""
        index: Dict[int, List[str]] = {i: [] for i in range(1, 13)}
        
        # Standard planets
        for p, info in self.planets.items():
            h = info.get("house")
            if h and 1 <= h <= 12:
                index[h].append(p)
                
        # Masnui planets
        for m in self.masnuis:
            h = m.get("formed_in_house")
            name = m.get("name")
            if h and 1 <= h <= 12 and name:
                index[h].append(name)
        
        return index

    def get_house(self, planet_name: str) -> Optional[int]:
        """
        Returns the house of a planet. 
        Automatically falls back to Masnui if standard planet not found.
        """
        # Try standard
        if planet_name in self.planets:
            return self.planets[planet_name].get("house")
        
        # Try Masnui
        masnui_name = f"Masnui {planet_name}" if not planet_name.startswith("Masnui ") else planet_name
        for m in self.masnuis:
            if m.get("name") == masnui_name:
                return m.get("formed_in_house")
        
        return None

    def get_occupants(self, house: int) -> List[str]:
        """Returns all planets (standard + Masnui) in a house."""
        return self._house_occupants.get(house, [])

    def is_empty(self, house: int) -> bool:
        """Checks if a house has no planets."""
        return len(self.get_occupants(house)) == 0

    @property
    def house_status(self) -> Dict[str, str]:
        """Returns the house status map (Occupied/Empty House)."""
        return {
            str(h): "Occupied" if occupants else "Empty House" 
            for h, occupants in self._house_occupants.items()
        }

    def get_planet_data(self, planet_name: str) -> Optional[PlanetInHouse]:
        """Returns the raw data for a planet."""
        return self.planets.get(planet_name)

    @property
    def type(self) -> str:
        return self.data.get("chart_type", "Birth")

    @property
    def period(self) -> int:
        return self.data.get("chart_period", 0)
