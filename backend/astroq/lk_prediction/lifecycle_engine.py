import logging
from typing import Dict, List, Any
import copy
from .lk_constants import VARSHPHAL_YEAR_MATRIX
from .state_ledger import StateLedger
from .incident_resolver import IncidentResolver
from .dormancy_engine import DormancyEngine, DormancyState

logger = logging.getLogger(__name__)


class LifecycleEngine:
    """
    Stateful 75-year prediction engine that tracks cumulative planetary trauma.
    Sequentially processes annual charts and updates a persistent StateLedger.
    """
    def __init__(self):
        self.ledger = StateLedger()
        self.resolver = IncidentResolver()
        self.dormancy = DormancyEngine()
        self.history: Dict[int, StateLedger] = {}

    def run_75yr_analysis(self, natal_data: Dict[str, Any]) -> Dict[int, StateLedger]:
        """
        Runs the full 75-year simulation FIRST.
        Accepts either a ChartData object or a dictionary of natal positions.
        Returns a map of Age -> StateLedger (History).
        """
        natal_positions = self._extract_positions(natal_data)
        self.ledger = StateLedger() # Reset for new run
        self.history = {}
        
        for age in range(1, 76):
            # 1. Project annual positions for this age
            annual_positions = self._get_annual_positions(natal_positions, age)
            
            # 2. Detect geometric incidents
            incidents = self.resolver.detect_incidents(annual_positions)
            
            # 3. Apply incidents to persistent ledger (Memory)
            for incident in incidents:
                state = self.ledger.get_planet_state(incident.target)
                target_house = annual_positions.get(incident.target)
                
                # Check Dormancy Shield
                is_awake = self.dormancy.is_awake(incident.target, target_house, annual_positions, current_age=age)
                
                if incident.type == "Takkar":
                    # DEEP MODULE: LifecycleEngine no longer manually manages trauma modifiers.
                    # It delegates the 'Strike' impact logic to the StateLedger.
                    complex_state = self.dormancy.get_complex_state(incident.target, target_house, annual_positions)
                    
                    if is_awake or complex_state.is_startled:
                        self.ledger.apply_strike_impact(
                            incident.target, 
                            incident.trauma_weight, 
                            is_startled=complex_state.is_startled
                        )
                    else:
                        # Sleeping planet is safe from external strikes
                        pass
                        
                elif incident.type == "Sanctuary":
                    # Sanctuary resets modifier to None, but points remain (Scarring)
                    state.modifier = "Supported"
            
            # 4. Save a deep copy of the ledger for this year's history
            self.history[age] = copy.deepcopy(self.ledger)
            
            # 5. Reset volatile modifiers for the next year cycle (Mechanical fatigue remains)
            for p_state in self.ledger.planets.values():
                if p_state.modifier != "Burst" and p_state.modifier != "Leaking":
                    p_state.modifier = "None"
                    
        return self.history

    def generate_75yr_report(self, natal_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs the 75-year analysis and formats the output for the Sachin Graph.
        """
        history = self.run_75yr_analysis(natal_data)
        
        series = []
        for age, ledger in history.items():
            friction = sum(ledger.get_leakage_multiplier(p) for p in ledger.planets)
            momentum = sum(1 for p, s in ledger.planets.items() if s.modifier == "Supported")
            
            series.append({
                "age": age,
                "friction": round(friction, 2),
                "momentum": momentum,
                "trauma_total": sum(s.trauma_points for s in ledger.planets.values())
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
            mapped = year_map.get(natal_h)
            if mapped is None:
                # C-3 FIX: A missing natal_h in the matrix is a data gap — log it so it is
                # never silent. Fall back to natal house to keep the engine running.
                logger.warning(
                    "VARSHPHAL_YEAR_MATRIX gap: natal_h=%s not found for age=%s planet=%s — "
                    "falling back to natal house. Check lk_constants.VARSHPHAL_YEAR_MATRIX.",
                    natal_h, age, p
                )
                mapped = natal_h
            annual[p] = mapped
        return annual

    def _extract_positions(self, chart_data: Dict[str, Any]) -> Dict[str, int]:
        """Helper to extract positions from either ChartData or raw dict."""
        if "planets_in_houses" in chart_data:
            return {
                p: info.get("house")
                for p, info in chart_data.get("planets_in_houses", {}).items()
                if info.get("house")
            }
        # Assume it's already a Dict[str, int] if it doesn't have planets_in_houses
        return chart_data
