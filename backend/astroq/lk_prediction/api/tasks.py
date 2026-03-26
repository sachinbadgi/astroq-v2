"""
TaskIQ configuration for AstroQ background tasks.
Uses InMemoryBroker by default for local development.
"""

from taskiq import InMemoryBroker
from astroq.lk_prediction.benchmark_runner import BenchmarkRunner
from astroq.lk_prediction.config import ModelConfig
import json

# Initialize the broker
broker = InMemoryBroker()

@broker.task
async def cleanup_expired_charts(db_path: str) -> int:
    """Purge expired charts from the database."""
    from astroq.lk_prediction.api.chart_store import ChartStore
    store = ChartStore(db_path)
    return store.cleanup_expired()

@broker.task
async def run_benchmark_task(config_params: dict, bench_dir: str, figures: list) -> dict:
    """
    Execute benchmark runner as a background task.
    """
    cfg = ModelConfig(
        db_path=config_params["db_path"], 
        defaults_path=config_params["defaults_path"]
    )
    runner = BenchmarkRunner(cfg, bench_dir)
    
    metrics = runner.run_all(figures)
    
    runs = []
    for name, res in metrics.results_by_figure.items():
        for ev in res["events_eval"]:
            runs.append({
                "id": f"{name}_{ev['actual_age']}",
                "public_figure": name,
                "event": ev["event"],
                "actual_age": ev["actual_age"],
                "predicted_age": ev["predicted_age"],
                "status": "HIT" if ev["hit"] else "MISS" if ev["offset"] > 5 else "PARTIAL"
            })
            
    return {
        "runs": runs,
        "metrics": {
            "hit_rate": f"{round(metrics.get_hit_rate() * 100, 1)}%",
            "avg_offset": f"+{round(metrics.get_avg_offset(), 1)} yrs",
            "total_tested": metrics.total_events
        }
    }
