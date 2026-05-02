# backend/astroq/lk_prediction/benchmark_runner.py
class BenchmarkRunner:
    def __init__(self, config, bench_dir):
        self.config = config
        self.bench_dir = bench_dir
    def run_benchmark(self, figures):
        return {"status": "mock_success"}
