# backend/astroq/lk_prediction/scapegoat_router.py
"""
ScapegoatRouter — 1952 Gosvami Sacrificial Agent rerouting.
Canonical table: Gosvami 1952, pp. 171-200.
"""
from typing import List, Optional

SCAPEGOAT_TABLE = {
    "Saturn":  ["Venus", "Rahu"],  # Wife / In-laws (cite: p.197)
    "Jupiter": ["Ketu"],           # Son / Maternal Uncle (cite: p.199)
    "Sun":     ["Ketu"],           # Son / Grandfather (cite: p.199)
    "Mars":    ["Ketu"],           # Nephew / Son (cite: p.198)
    "Venus":   ["Moon"],           # Mother (cite: p.198)
    "Mercury": ["Venus"],          # Wife (cite: p.198)
}
MASTERS_OF_JUSTICE = {"Sun", "Mars", "Jupiter"}

class ScapegoatRouter:
    def get_scapegoats(self, planet: str, attacker: Optional[str] = None) -> List[str]:
        base = planet.replace("Masnui ", "") if planet.startswith("Masnui ") else planet
        if base in MASTERS_OF_JUSTICE:
            return ["Ketu"]  # Masters always sacrifice Ketu first (cite: p.174)
        return SCAPEGOAT_TABLE.get(base, [])

    def is_master_of_justice(self, planet: str) -> bool:
        base = planet.replace("Masnui ", "") if planet.startswith("Masnui ") else planet
        return base in MASTERS_OF_JUSTICE
