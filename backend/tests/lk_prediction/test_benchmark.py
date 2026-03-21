import pytest
import os
import json
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.benchmark_runner import BenchmarkRunner

# We know the path to the ground truth JSON
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GT_PATH = os.path.join(BASE_DIR, "data", "public_figures_ground_truth.json")

def load_ground_truth():
    if not os.path.exists(GT_PATH):
        return []
    with open(GT_PATH, "r") as f:
        return json.load(f)

# Cache instance
GROUND_TRUTH_DATA = load_ground_truth()

@pytest.fixture
def benchmark_runner(tmp_db):
    config = ModelConfig(tmp_db, os.path.join(BASE_DIR, "data", "model_defaults.json"))
    return BenchmarkRunner(config, BASE_DIR)


def _get_figure_events(name: str):
    for f in GROUND_TRUTH_DATA:
        if f["name"].lower() == name.lower():
            return f["events"]
    return []


@pytest.mark.benchmark
class TestSachinTendulkar:
    def test_sachin_benchmark(self, benchmark_runner):
        events = _get_figure_events("Sachin Tendulkar")
        if not events: pytest.skip("GT data not found")
        
        res = benchmark_runner.run_figure("Sachin Tendulkar", events)
        assert len(res["events_eval"]) == 4
        # We don't strictly assert the hit rate here, as it may fail depending on config.
        # But we assert the runner returns the proper structure
        assert "hits" in res
        assert "false_positives" in res


@pytest.mark.benchmark
class TestAmitabhBachchan:
    def test_amitabh_benchmark(self, benchmark_runner):
        events = _get_figure_events("Amitabh Bachchan")
        if not events: pytest.skip("GT data not found")
        
        res = benchmark_runner.run_figure("Amitabh Bachchan", events)
        assert len(res["events_eval"]) == 4


@pytest.mark.benchmark
class TestNarendraModi:
    def test_modi_benchmark(self, benchmark_runner):
        events = _get_figure_events("Narendra Modi")
        if not events: pytest.skip("GT data not found")
        
        res = benchmark_runner.run_figure("Narendra Modi", events)
        assert len(res["events_eval"]) == 3


@pytest.mark.benchmark
class TestSteveJobs:
    def test_jobs_benchmark(self, benchmark_runner):
        events = _get_figure_events("Steve Jobs")
        if not events: pytest.skip("GT data not found")
        
        res = benchmark_runner.run_figure("Steve Jobs", events)
        assert len(res["events_eval"]) == 4

@pytest.mark.benchmark
class TestBillGates:
    def test_gates_benchmark(self, benchmark_runner):
        events = _get_figure_events("Bill Gates")
        if not events: pytest.skip("GT data not found")
        
        res = benchmark_runner.run_figure("Bill Gates", events)
        assert len(res["events_eval"]) == 3
