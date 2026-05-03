import os
import sys
import json
from dataclasses import dataclass

sys.path.append(os.path.join(os.getcwd(), "backend"))

from astroq.lk_prediction.state_ledger import StateLedger
from astroq.lk_prediction.astrological_context import UnifiedAstrologicalContext
from astroq.lk_prediction.data_contracts import EnrichedChart, ChartData

def verify_stateful_logic():
    print("--- VERIFYING STATEFUL ENGINE LOGIC ---")
    
    # 1. Test Lamp House Awakening & H2 Leakage
    print("\nTest 1: Lamp House (H1) Awakening & H2 Leakage")
    ledger = StateLedger()
    
    # Mock context where Sun is in H1, H2 is blank
    class MockChart:
        def __init__(self, ppos, age=20):
            self.ppos = ppos
            self.period = age
            self.type = "Yearly"
        def get_house(self, p): return self.ppos.get(p)
        def get_occupants(self, h): return [p for p, house in self.ppos.items() if house == h]

    # Sun in H1, H2 empty
    ppos = {"Sun": 1, "Moon": 4}
    chart = MockChart(ppos)
    enriched = EnrichedChart(source={"chart_period": 20}, planet_strengths={})
    
    ctx = UnifiedAstrologicalContext(enriched=enriched)
    ctx.chart = chart
    ctx.age = 20
    
    ledger.evolve_state(ctx)
    sun_state = ledger.get_planet_state("Sun")
    print(f"Sun in H1: is_awake={sun_state.is_awake}, sustenance_factor={sun_state.sustenance_factor}")
    assert sun_state.is_awake == True
    assert sun_state.sustenance_factor == 0.6 # Leakage due to H2 blank
    
    # Add planet to H2
    ppos["Mercury"] = 2
    ledger.evolve_state(ctx)
    sun_state = ledger.get_planet_state("Sun")
    print(f"Sun in H1 (H2 occupied): sustenance_factor={sun_state.sustenance_factor}")
    assert sun_state.sustenance_factor == 1.0

    # 2. Test Trauma Carry-over & Age 36 Boundary
    print("\nTest 2: Trauma Carry-over & Age 36 Boundary")
    ledger = StateLedger()
    
    class GrahaContext:
        def __init__(self): self.age = 30
        def get_fate_type_for_domain(self, d): return "GRAHA_PHAL"

    ledger.apply_trauma("Saturn", 3.0, context=GrahaContext()) # High trauma
    sat_state = ledger.get_planet_state("Saturn")
    old_threshold = sat_state.burst_threshold
    print(f"Saturn Trauma: {sat_state.trauma_points}, Old Burst Threshold: {old_threshold}")
    
    # Simulate Age 36 boundary
    class Age36Context:
        def __init__(self, age=36):
            self.age = age
            from astroq.lk_prediction.astro_chart import AstroChart
            self.chart = AstroChart({"planets_in_houses": {}})
        def get_house(self, p): return None
    
    ledger.evolve_state(Age36Context())
    sat_state = ledger.get_planet_state("Saturn")
    print(f"Saturn Age 36 Burst Threshold: {sat_state.burst_threshold}")
    assert sat_state.burst_threshold < old_threshold
    
    # 3. Test Scapegoat Rerouting
    print("\nTest 3: Scapegoat Rerouting (Saturn -> Rahu)")
    ledger = StateLedger()
    # Mock context to return RASHI_PHAL
    class MockContext:
        def __init__(self): self.age = 30
        def get_fate_type_for_domain(self, d): return "RASHI_PHAL"
    
    ledger.apply_trauma("Saturn", 1.0, context=MockContext())
    sat_state = ledger.get_planet_state("Saturn")
    rahu_state = ledger.get_planet_state("Rahu")
    print(f"Saturn Hit (Rashi Phal): Saturn Trauma={sat_state.trauma_points}, Rahu Trauma={rahu_state.trauma_points}")
    # Rahu should take 0.5 of Saturn's hit per SCAPEGOATS const
    assert rahu_state.trauma_points > 0
    assert sat_state.trauma_points == 0 # Fully rerouted since Saturn is healthy

    # 4. Test Fatigue (Double Hit)
    print("\nTest 4: Fatigue (Double Hit)")
    ledger.apply_trauma("Saturn", 2.0, context=GrahaContext()) # Make Saturn fatigued (> 1.5)
    ledger.apply_trauma("Saturn", 1.0, context=MockContext())
    sat_state = ledger.get_planet_state("Saturn")
    print(f"Saturn Hit (Fatigued): Saturn Trauma={sat_state.trauma_points}")
    # Should be > 2.0 now because it didn't fully reroute
    assert sat_state.trauma_points > 2.0

    print("\n--- ALL TESTS PASSED ---")

if __name__ == "__main__":
    verify_stateful_logic()
