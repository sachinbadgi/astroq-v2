"""
Module 9/10: Benchmark Runner & Config Tuner.

Runs the prediction engine against public figure charts to measure metrics.
"""
import json
import os
from typing import Dict, List, Any

from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.pipeline import LKPredictionPipeline

class BenchmarkMetrics:
    def __init__(self):
        self.hits = 0
        self.total_events = 0
        self.total_offset = 0
        self.natal_matches = 0
        self.false_positives = 0
        self.total_predictions = 0
        self.results_by_figure = {}

    def get_hit_rate(self) -> float:
        return self.hits / max(1, self.total_events)

    def get_avg_offset(self) -> float:
        return self.total_offset / max(1, self.total_events)

    def get_natal_accuracy(self) -> float:
        return self.natal_matches / max(1, self.total_events)

    def get_fpr(self) -> float:
        return self.false_positives / max(1, self.total_predictions)


class BenchmarkRunner:
    def __init__(self, config: ModelConfig, data_dir: str):
        self.config = config
        self.data_dir = data_dir
        self.pipeline = LKPredictionPipeline(config)

    def run_figure(self, figure_name: str, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run benchmark for a single figure."""
        # Load chart file
        filename = figure_name.lower().replace(" ", "_").replace(".", "") + "_enriched_chart.json"
        
        # Special case mappings (from old codebase)
        if "abdul_kalam" in filename: filename = "a_p_j_abdul_kalam_enriched_chart.json"
        elif "ambedkar" in filename: filename = "b_r_ambedkar_enriched_chart.json"

        chart_path = os.path.join(self.data_dir, "tests", "data", "public_figures", filename)
        if not os.path.exists(chart_path):
            raise FileNotFoundError(f"Chart JSON not found for {figure_name}: {chart_path}")

        with open(chart_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        # The raw_data has chart_0, chart_1, ..., chart_75
        birth_chart = raw_data.get("chart_0")
        if not birth_chart:
            raise ValueError(f"No chart_0 found in {filename}")

        # Ensure type is Birth
        birth_chart["chart_type"] = "Birth"
        birth_chart["chart_period"] = 0
        self.pipeline.load_natal_baseline(birth_chart)

        # We will collect all predictions from age 1 to 75
        # Actually, pipeline.generate_predictions works on ONE chart at a time, but maintains state!
        # State depends on chronological execution.
        all_predictions = []
        max_age_to_run = min(75, max([e["age"] for e in events]) + 5)
        
        for age in range(1, max_age_to_run + 1):
            key = f"chart_{age}"
            if key in raw_data:
                annual_chart = raw_data[key]
                annual_chart["chart_type"] = "Yearly"
                annual_chart["chart_period"] = age
                preds = self.pipeline.generate_predictions(annual_chart)
                for p in preds:
                    p.peak_age = age # ensure peak age is set to current year
                all_predictions.extend(preds)

        results = {
            "name": figure_name,
            "events_eval": [],
            "hits": 0,
            "offset_sum": 0,
            "false_positives": 0,
            "total_predictions": len(all_predictions)
        }

        # Evaluate Ground Truth Events
        for event in events:
            domain = event["domain"].lower()
            actual_age = event["age"]
            
            # Filter predictions for this domain
            domain_preds = [p for p in all_predictions if domain in p.domain.lower()]
            
            if not domain_preds:
                results["events_eval"].append({
                    "event": event["description"], "actual_age": actual_age,
                    "hit": False, "offset": 10.0, "predicted_age": 0
                })
                results["offset_sum"] += 10.0 # max penalty
                continue

            # Find closest
            closest = min(domain_preds, key=lambda p: abs(p.peak_age - actual_age))
            offset = abs(closest.peak_age - actual_age)
            is_hit = offset <= 2

            results["events_eval"].append({
                "event": event["description"],
                "actual_age": actual_age,
                "predicted_age": closest.peak_age,
                "offset": offset,
                "hit": is_hit
            })
            
            if is_hit:
                results["hits"] += 1
            results["offset_sum"] += min(offset, 10.0) # cap offset penalty

        # Evaluate False Positives
        # A FP is a prediction that doesn't match any GT event within ±3 years
        fp_count = 0
        for p in all_predictions:
            domain = p.domain.lower()
            # GT events for this domain
            gt_events = [e for e in events if e["domain"].lower() == domain]
            
            if not gt_events:
                fp_count += 1
                continue
                
            closest_gt_offset = min(abs(p.peak_age - e["age"]) for e in gt_events)
            if closest_gt_offset > 3:
                fp_count += 1
                
        results["false_positives"] = fp_count

        return results

    def run_all(self, figures: List[Dict[str, Any]]) -> BenchmarkMetrics:
        metrics = BenchmarkMetrics()
        for f in figures:
            name = f["name"]
            events = f["events"]
            try:
                res = self.run_figure(name, events)
                metrics.total_events += len(events)
                metrics.hits += res["hits"]
                metrics.total_offset += res["offset_sum"]
                metrics.false_positives += res["false_positives"]
                metrics.total_predictions += res["total_predictions"]
                metrics.results_by_figure[name] = res
            except Exception as e:
                print(f"Failed to run figure {name}: {e}")
                
        return metrics
