from typing import Dict, List, Any
import copy
from .lk_constants import VARSHPHAL_YEAR_MATRIX
from .state_ledger import StateLedger
from .incident_resolver import IncidentResolver

class LifecycleEngine:
    """
    Stateful 75-year prediction engine that tracks cumulative planetary trauma.
    Sequentially processes annual charts and updates a persistent StateLedger.
    """
    def __init__(self):
        self.ledger = StateLedger()
        self.resolver = IncidentResolver()

    def run_75yr_analysis(self, natal_positions: Dict[str, int]) -> Dict[int, Dict[str, Any]]:
        report = {}
        
        for age in range(1, 76):
            # 1. Project annual positions for this age
            annual_positions = self._get_annual_positions(natal_positions, age)
            
            # 2. Detect geometric incidents
            incidents = self.resolver.detect_incidents(annual_positions)
            
            # 3. Apply incidents to persistent ledger (Memory)
            for incident in incidents:
                state = self.ledger.get_planet_state(incident.target)
                if incident.type == "Takkar":
                    state.trauma_points += 1
                    state.modifier = "Startled"
                elif incident.type == "Sanctuary":
                    state.modifier = "Supported"
            
            # 4. Capture current year snapshot (including multipliers)
            year_snapshot = {
                "age": age,
                "positions": annual_positions,
                "incidents": incidents,
                "planetary_states": copy.deepcopy(self.ledger.planets),
                "multipliers": {
                    p: self.ledger.get_leakage_multiplier(p) 
                    for p in self.ledger.planets
                }
            }
            report[age] = year_snapshot
            
            # 5. Reset volatile modifiers for the next year cycle
            for p_state in self.ledger.planets.values():
                p_state.modifier = "None"
                
        return report

    def generate_75yr_report(self, natal_positions: Dict[str, int]) -> Dict[str, Any]:
        """
        Runs the 75-year analysis and formats the output for the Sachin Graph.
        Returns friction/momentum series and cumulative trauma hotspots.
        """
        raw_report = self.run_75yr_analysis(natal_positions)
        
        series = []
        for age, data in raw_report.items():
            friction = sum(data["multipliers"].values())
            momentum = sum(1 for i in data["incidents"] if i.type == "Sanctuary")
            
            series.append({
                "age": age,
                "friction": round(friction, 2),
                "momentum": momentum,
                "trauma_delta": sum(1 for i in data["incidents"] if i.type == "Takkar")
            })
            
        return {
            "summary": {
                "total_trauma": sum(p.trauma_points for p in self.ledger.planets.values()),
                "scarred_planets": [p for p, s in self.ledger.planets.items() if s.trauma_points > 0]
            },
            "timeline": series
        }

    def _get_annual_positions(self, natal_positions: Dict[str, int], age: int) -> Dict[str, int]:
        """Project natal houses to annual houses using the 120-year matrix."""
        year_map = VARSHPHAL_YEAR_MATRIX.get(age, {})
        annual = {}
        for p, natal_h in natal_positions.items():
            # Fallback to natal house if age not in matrix (though range is 1-120)
            annual[p] = year_map.get(natal_h, natal_h)
        return annual
