"""
AutoResearch 2.0 (LSE) - Batch Runner
Processes 20+ historical figures in 10-figure increments.
"""

import json
import os
import sys
import copy
from typing import Any

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from astroq.lk_prediction.lse_orchestrator import LSEOrchestrator
from astroq.lk_prediction.data_contracts import LKPrediction, LSEPrediction
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.rules_engine import RulesEngine


class BatchRunner:
    def __init__(self, dataset_path: str):
        # Resolve absolute path to avoid CWD issues
        abs_path = os.path.abspath(dataset_path)
        with open(abs_path, "r") as f:
            self.dataset = json.load(f)
        
        # Setup Orchestrator (Using a temp file DB for testing)
        db_path = "backend/data/test_batch_runner.db"
        if os.path.exists(db_path):
            os.remove(db_path)
            
        self.cfg = ModelConfig(db_path=db_path, defaults_path="backend/data/model_defaults.json")
        self.orchestrator = LSEOrchestrator(self.cfg)

    def run_batch(self, start_idx: int, size: int):
        batch = self.dataset[start_idx : start_idx + size]
        results = []
        
        print(f"\n--- RUNNING BATCH ({start_idx} to {start_idx + len(batch)}) ---")
        
        for item in batch:
            figure_id = item["id"]
            name = item["name"]
            birth_chart = item["chart"]
            life_events = item["events"]
            benchmarks = [(e["domain"], e["bench"], e["planet"]) for e in life_events]

            # Mock Pipeline for this specific figure's benchmarks
            def mock_run_pipeline(birth, annual, fig):
                preds = []
                for domain, bench, planet in benchmarks:
                    preds.append(LKPrediction(
                        domain=domain, event_type="generic", peak_age=bench, 
                        source_planets=[planet], confidence="certain", polarity="mixed", prediction_text=f"{domain} event"
                    ))
                return preds

            self.orchestrator._run_pipeline = mock_run_pipeline
            
            # Annual charts just use birth chart for this mock
            annual_charts = {e["age"]: birth_chart for e in life_events}
            
            print(f"Processing {name}...")
            result = self.orchestrator.solve_chart(birth_chart, annual_charts, life_events, figure_id=figure_id)
            results.append((name, result))
            
        return results

    def report(self, results):
        print("\n" + "="*80)
        print(f"{'FIGURE':<20} | {'RESULT':<12} | {'GAP (Mean)':<10} | {'RATIONALES'}")
        print("-" * 80)
        for name, res in results:
            status = "CONVERGED" if res.converged else "FAILED"
            mean_gap = f"{res.chart_dna.mean_offset_years:.2f}"
            rationales = ", ".join(res.chart_dna.delay_constants.keys())
            print(f"{name:<20} | {status:<12} | {mean_gap:<10} | {rationales}")
        print("="*80)


if __name__ == "__main__":
    runner = BatchRunner("backend/data/public_figures_ground_truth_v2.json")
    
    total_figures = len(runner.dataset)
    batch_size = 10
    
    all_results = []
    
    for i in range(0, total_figures, batch_size):
        res = runner.run_batch(i, batch_size)
        all_results.extend(res)
        
    runner.report(all_results)
