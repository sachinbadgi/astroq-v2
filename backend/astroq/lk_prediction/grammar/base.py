from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, List, Protocol, Dict, Optional

@dataclass
class GrammarHit:
    """
    Represents a specific grammar condition detected in the chart.
    Provides forensic grounding for strength adjustments.
    """
    rule_id: str
    description: str
    affected_planets: List[str] = field(default_factory=list)
    magnitude: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class GrammarModule(Protocol):
    """
    Protocol for a Deep Grammar Module.
    """
    name: str
    phase: int  # Controls execution order (1-5)

    def detect(self, chart: Dict[str, Any]) -> List[GrammarHit]:
        """Analyzes the chart and returns a list of detected hits."""
        ...

    def audit(self, chart: Dict[str, Any], enriched: Dict[str, Any], hits: List[GrammarHit]) -> None:
        """Applies strength adjustments to enriched planets based on hits."""
        ...
