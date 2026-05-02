from typing import Any, Dict, List
from .grammar.registry import GrammarRegistry
from .grammar.modules.structural_module import StructuralModule
from .grammar.modules.state_module import StateModule
from .grammar.modules.mangal_badh_module import MangalBadhModule
from .grammar.modules.debt_module import DebtModule
from .grammar.modules.entanglement_module import EntanglementModule
from .grammar.modules.interaction_module import InteractionModule

class GrammarAnalyser:
    """
    Registry-backed grammar facade.

    Provides two access patterns:
      - apply_grammar_rules() — batch audit of all 6 modules
      - Point-query methods (detect_sleeping, detect_kaayam, etc.) —
        delegate to individual module logic for per-planet/per-pair queries.
    """

    def __init__(self, config: Any) -> None:
        self._cfg = config
        self.registry = GrammarRegistry()

        self.registry.register(StructuralModule())
        self.registry.register(StateModule(config))
        self.registry.register(DebtModule(config))
        self.registry.register(MangalBadhModule(config))
        self.registry.register(InteractionModule(config))
        self.registry.register(EntanglementModule(config))

    # -- batch entry point --------------------------------------------------

    def apply_grammar_rules(self, chart: Dict[str, Any], enriched: Dict[str, Any]) -> None:
        """Run all 6 grammar modules. Writes hits to chart['grammar_audit_hits']."""
        all_hits = self.registry.apply_all(chart, enriched)
        chart["grammar_audit_hits"] = {
            mod_name: [
                {"rule_id": h.rule_id, "description": h.description, "planets": h.affected_planets}
                for h in hits
            ]
            for mod_name, hits in all_hits.items()
        }

    # -- point-query methods (delegate to module logic) ---------------------

    def detect_sleeping(self, planet: str, planets: Dict[str, Any]) -> bool:
        mod = self.registry.get_module(StateModule)
        if not mod: return False
        house = planets.get(planet, {}).get("house")
        if not house: return False
        return mod._is_sleeping(planet, house, planets)

    def detect_kaayam(self, planet: str, planets: Dict[str, Any]) -> bool:
        mod = self.registry.get_module(StateModule)
        if not mod: return False
        house = planets.get(planet, {}).get("house")
        if not house: return False
        return mod._is_kaayam(planet, house, planets)

    def detect_nikami(self, planet: str, planets: Dict[str, Any]) -> bool:
        mod = self.registry.get_module(StateModule)
        if not mod: return False
        house = planets.get(planet, {}).get("house")
        if not house: return False
        return mod._is_nikami(planet, house, planets)

    def detect_dharmi(self, planet: str, planets: Dict[str, Any], chart: Dict[str, Any]) -> bool:
        mod = self.registry.get_module(StateModule)
        if not mod: return False
        house = planets.get(planet, {}).get("house")
        if not house: return False
        teva = chart.get("dharmi_kundli_status") == "Dharmi Teva"
        return bool(mod._get_dharmi_type(planet, house, planets, teva))

    def detect_sathi(self, p1: str, p2: str, planets: Dict[str, Any]) -> bool:
        mod = self.registry.get_module(InteractionModule)
        if not mod: return False
        return mod._detect_exchange(p1, p2, planets)

    def detect_bilmukabil(self, p1: str, p2: str, planets: Dict[str, Any]) -> bool:
        mod = self.registry.get_module(InteractionModule)
        if not mod: return False
        return mod._detect_bilmukabil(p1, p2, planets)
