"""
Module 10: Config Tuner.

Automated grid search to find the optimal ModelConfig overrides
by maximizing the composite benchmark score.
"""
import os
import json
import itertools
from copy import deepcopy

from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.benchmark_runner import BenchmarkRunner, BenchmarkMetrics


class ConfigTuner:
    def __init__(self, db_path: str, defaults_path: str, data_dir: str):
        self.db_path = db_path
        self.defaults_path = defaults_path
        self.data_dir = data_dir
        self.config = ModelConfig(db_path, defaults_path)
        self.runner = BenchmarkRunner(self.config, data_dir)

    def evaluate_config(self, overrides: dict, figures_data: list) -> dict:
        """Apply overrides, run benchmark, return metrics."""
        self.config.reset_overrides()
        for k, v in overrides.items():
            self.config.set_override(k, v)

        # Run benchmark
        metrics = self.runner.run_all(figures_data)
        
        # Calculate composite
        hr = metrics.get_hit_rate()
        off = metrics.get_avg_offset()
        nat = metrics.get_natal_accuracy()
        fpr = metrics.get_fpr()

        # Target: HR > 0.80, Off < 2.0, Nat > 0.85, FPR < 0.15
        hr_score = hr / 0.80
        off_score = 1.0 - (off / 2.0)
        # Handle division by zero or edge cases if needed
        # We cap off_score at max 1.5 if it's 0 offset, min 0 if > 2
        off_score = max(0.0, min(1.5, off_score))
        nat_score = nat / 0.85
        fpr_score = 1.0 - (fpr / 0.15) if fpr > 0 else 1.0

        composite = (hr_score + off_score + nat_score + fpr_score) / 4.0

        return {
            "overrides": overrides,
            "hit_rate": hr,
            "offset": off,
            "natal_accuracy": nat,
            "fpr": fpr,
            "composite": composite,
            "hits": metrics.hits,
            "total_events": metrics.total_events
        }

    def grid_search(self, param_grid: dict, figures_data: list):
        """Perform full grid search over param_grid."""
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        
        best_score = -1000.0
        best_result = None
        results = []

        total_iterations = 1
        for v in values:
            total_iterations *= len(v)

        print(f"Starting grid search: {total_iterations} combinations.")
        count = 0
        for combination in itertools.product(*values):
            overrides = dict(zip(keys, combination))
            print(f"[{count+1}/{total_iterations}] Testing: {overrides}")
            res = self.evaluate_config(overrides, figures_data)
            print(f"  -> HR: {res['hit_rate']:.2%}, Off: {res['offset']:.2f}, Composite: {res['composite']:.3f} (Hits: {res['hits']}/{res['total_events']})")
            
            results.append(res)
            if res["composite"] > best_score:
                best_score = res["composite"]
                best_result = res
                print(f"  🌟 NEW BEST!")
                
            count += 1

        print("\n=== Grid Search Complete ===")
        print(f"Best Composite Score: {best_score:.3f}")
        print(f"Best Overrides: {json.dumps(best_result['overrides'], indent=2)}")
        print(f"Metrics: HR: {best_result['hit_rate']:.2%}, Offset: {best_result['offset']:.2f}")

        return best_result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=1)
    args = parser.parse_args()

    # Base paths
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # Use a temp db file for testing instead of memory, because ModelConfig opens new connections for each operation
    db_path = os.path.join(base_dir, "data", "temp_tuner.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    defaults_path = os.path.join(base_dir, "data", "model_defaults.json")
    
    gt_path = os.path.join(base_dir, "data", "public_figures_ground_truth.json")
    with open(gt_path, "r") as f:
        ground_truth = json.load(f)

    tuner = ConfigTuner(db_path, defaults_path, base_dir)
    
    # 1. First run with default config to get a baseline
    print("Running baseline...")
    baseline = tuner.evaluate_config({}, ground_truth)
    print(f"Baseline -> HR: {baseline['hit_rate']:.2%}, Offset: {baseline['offset']:.2f}, Composite: {baseline['composite']:.3f}")

    # 2. Setup grid
    # Experiment 7: expedited 9-combo Classifier & Scaling Synergy
    param_grid = {
        "event_classifier.threshold_absolute": [0.65, 0.70, 0.75],
        "rules.boost_scaling": [0.03, 0.04, 0.05]
    }
    
    if args.iterations > 1:
        # Run actual grid search
        best = tuner.grid_search(param_grid, ground_truth)
        
        # Save best overrides to tuned json
        tuned_path = os.path.join(base_dir, "data", "model_defaults_tuned.json")
        with open(tuned_path, "w") as f:
            json.dump(best["overrides"], f, indent=2)
        print(f"Saved tuned overrides to {tuned_path}")
