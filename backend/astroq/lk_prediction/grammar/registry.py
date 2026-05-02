import logging
from typing import List, Dict, Any
from .base import GrammarModule, GrammarHit

logger = logging.getLogger(__name__)

class GrammarRegistry:
    """
    The central orchestrator for the modular Grammar Audit Engine.
    Executes modules in order of their 'phase' attribute.
    """

    def __init__(self):
        self._modules: List[GrammarModule] = []

    def register(self, module: GrammarModule):
        """Registers a new grammar module and sorts by phase."""
        self._modules.append(module)
        self._modules.sort(key=lambda x: x.phase)
        logger.info(f"Registered Grammar Module: {module.name} (Phase {module.phase})")

    def get_module(self, module_class: Any) -> Any:
        """Returns a registered module by its class type."""
        for mod in self._modules:
            if isinstance(mod, module_class):
                return mod
        return None

    def apply_all(self, chart: Dict[str, Any], enriched: Dict[str, Any]) -> Dict[str, List[GrammarHit]]:
        """
        Runs the full grammar audit pipeline across all registered modules.
        Returns a map of module names to their detected hits.
        """
        all_hits: Dict[str, List[GrammarHit]] = {}

        # Initialize grammar fields in enriched data if not present
        self._init_enriched_fields(enriched)

        for module in self._modules:
            try:
                # 1. Forensic Detection
                hits = module.detect(chart)
                all_hits[module.name] = hits
                
                # 2. Audit Adjustment
                module.audit(chart, enriched, hits)
                
            except Exception as e:
                logger.error(f"Error in Grammar Module {module.name}: {e}", exc_info=True)

        return all_hits

    def _init_enriched_fields(self, enriched: Dict[str, Any]):
        """Ensures all enriched planet dicts have required grammar fields."""
        for ep in enriched.values():
            ep.setdefault("strength_total", 0.0)
            ep.setdefault("raw_aspect_strength", 0.0)
            ep.setdefault("house", 0)
            ep.setdefault("sleeping_status", "")
            ep.setdefault("kaayam_status", "")
            ep.setdefault("dharmi_status", "")
            ep.setdefault("is_nikami", False)
            ep.setdefault("sathi_companions", [])
            ep.setdefault("bilmukabil_hostile_to", [])
            ep.setdefault("is_masnui", False)
            ep.setdefault("is_masnui_parent", False)
            ep.setdefault("dhoka_graha", False)
            ep.setdefault("achanak_chot_active", False)
            ep.setdefault("rin_debts", [])
            ep.setdefault("dispositions_active", [])

            bd = ep.setdefault("strength_breakdown", {})
            # Ensure all standard keys exist to avoid KeyErrors downstream
            for key in [
                "sleeping", "kaayam", "disposition", "dharmi", "sathi", "bilmukabil",
                "mangal_badh", "masnui_feedback", "dhoka", "achanak_chot", "rin", "cycle_35yr",
                "spoiler"
            ]:
                bd.setdefault(key, 0.0)
