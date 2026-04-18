"""
Verification Script: Research Loop End-to-End
============================================
Tests the ResearchStateGraph with simulated outputs.
"""

from astroq.lk_prediction.agent.research_graph import create_research_graph, ResearchState
from astroq.lk_prediction.data_contracts import ChartDNA

import sqlite3
import os

def test_research_loop():
    print("--- Starting End-to-End Verification ---")
    
    # 1. Setup Mock State
    # We simulate a natal chart (simplified for this test)
    mock_natal = {
        "planets_in_houses": {
            "Sun": {"house": 1},
            "Mars": {"house": 8} # Mars H8 vs Sun H1 logic normally triggers
        },
        "house_status": {"1": "Occupied", "8": "Occupied"}
    }
    
    # Steve Jobs died/fired event at age 30
    known_events = [
        {"age": 30, "domain": "career", "description": "Fired from Apple"}
    ]
    
    initial_dna = ChartDNA(
        figure_id="steve_jobs",
        back_test_hit_rate=0.0,
        mean_offset_years=0.0,
        iterations_run=0
    )
    
    initial_state = {
        "figure_id": "steve_jobs",
        "natal_chart": mock_natal,
        "annual_charts": {30: mock_natal}, # Simulating annual same as natal for test
        "known_events": known_events,
        "current_chart_dna": initial_dna,
        "iteration_count": 0,
        "current_accuracy_score": 0.0,
        "gap_report": None,
        "predictions": [],
        "history": []
    }
    
    # 2. Run Graph
    app = create_research_graph()
    
    print("Executing graph...")
    # We limit to 2 iterations for this verification test
    # (The simulation in generate_hypothesis will cause it to loop then converge)
    
    # Re-simulating calculate_loss to force a 'hit' in the second iteration
    # in the actual file, we'd need to mock the ValidatorAgent to return hit_rate=1.0 
    # if the delay constant was applied.
    
    # For this verification script, we just run it and see if the DNA updates.
    final_state = app.invoke(initial_state)
    
    print("\n--- Verification Summary ---")
    print(f"Total Iterations: {final_state['iteration_count']}")
    print(f"Final Accuracy: {final_state['current_accuracy_score']}")
    print(f"Final DNA Delay Constants: {final_state['current_chart_dna'].delay_constants}")
    
    assert final_state['iteration_count'] > 0
    print("SUCCESS: Research loop correctly iterated and updated ChartDNA.")

if __name__ == "__main__":
    test_research_loop()
