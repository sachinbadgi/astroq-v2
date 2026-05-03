import json
import os
import sqlite3
import sys
from typing import Any, Dict, List, Tuple, Optional

from .chart_generator import ChartGenerator
from .natal_fate_view import NatalFateView
from .config import ModelConfig
from .pipeline import LKPredictionPipeline
from .calibration_module import CalibrationModule, CalibrationResult
from .tracer import trace_hit

class LKEngineRunner:
    """
    Deep module that orchestrates the entire Lal Kitab prediction lifecycle.
    Hides the complexity of building charts, initializing the pipeline,
    and classifying the fate domains.
    """

    # ── Geo map ───────────────────────────────────────────────────────────────────
    GEO_MAP = {
        "Allahabad, India":                        (25.4358,  81.8463,  "+05:30"),
        "Mumbai, India":                           (19.0760,  72.8777,  "+05:30"),
        "Vadnagar, India":                         (23.7801,  72.6373,  "+05:30"),
        "San Francisco, California, US":           (37.7749,-122.4194,  "-08:00"),
        "Seattle, Washington, US":                 (47.6062,-122.3321,  "-08:00"),
        "Sandringham, Norfolk, UK":                (52.8311,   0.5054,  "+00:00"),
        "New Delhi, India":                        (28.6139,  77.2090,  "+05:30"),
        "Gary, Indiana, US":                       (41.5934, -87.3464,  "-06:00"),
        "Pretoria, South Africa":                  (-25.7479, 28.2293,  "+02:00"),
        "Porbandar, India":                        (21.6417,  69.6293,  "+05:30"),
        "Jamaica Hospital, Queens, New York, US":  (40.7028, -73.8152,  "-05:00"),
        "Honolulu, Hawaii, US":                    (21.3069,-157.8583,  "-10:00"),
        "Mayfair, London, UK":                     (51.5100,  -0.1458,  "+00:00"),
        "Skopje, North Macedonia":                 (42.0003,  21.4280,  "+01:00"),
        "Scranton, Pennsylvania, US":              (41.4090, -75.6624,  "-05:00"),
        "Buckingham Palace, London, UK":           (51.5014,  -0.1419,  "+00:00"),
        "St. Petersburg, Russia":                  (59.9311,  30.3609,  "+03:00"),
        "Hodgenville, KY, USA":                    (37.5737, -85.7411,  "-06:00"),
        "Mvezo, South Africa":                     (-31.9329, 28.9988,  "+02:00"),
        "Aden, Yemen":                             (12.7855,  45.0187,  "+03:00"),
        "Indore, India":                           (22.7196,  75.8577,  "+05:30"),
        "Jamshedpur, India":                       (22.8046,  86.2029,  "+05:30"),
        "Raisen, India":                           (23.3314,  77.7886,  "+05:30"),
        "Madanapalle, India":                      (13.5510,  78.5051,  "+05:30"),
    }
    DEFAULT_GEO = (28.6139, 77.2090, "+05:30")

    def __init__(self, db_path: str, config_path: str):
        self.db_path = db_path
        self.config_path = config_path
        self.gen = ChartGenerator()
        self.view = NatalFateView()
        
    def _get_geo(self, place: str) -> Tuple[float, float, str]:
        pl = place.lower()
        for key, val in self.GEO_MAP.items():
            if key.lower() in pl or pl in key.lower():
                return val
        return self.DEFAULT_GEO

    def build_chart(self, dob: str, tob: str, place: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        trace_hit("lk_prediction_engine_runner_lkenginerunner_build_chart")
        tob_full = tob + ":00" if len(tob) == 5 else tob
        lat, lon, tz = self._get_geo(place)
        payload = self.gen.build_full_chart_payload(
            dob_str=dob, tob_str=tob_full, place_name=place,
            latitude=lat, longitude=lon, utc_string=tz, chart_system="vedic",
        )
        natal = payload.get("chart_0")
        if not natal:
            raise RuntimeError("ChartGenerator returned no chart_0")
        return natal, payload

    def build_pipeline(self) -> Optional[LKPredictionPipeline]:
        trace_hit("lk_prediction_engine_runner_lkenginerunner_build_pipeline")
        if not os.path.exists(self.db_path):
            return None
        cfg = ModelConfig(self.db_path, self.config_path)
        return LKPredictionPipeline(cfg)

    def run(
        self,
        dob: str,
        tob: str,
        place: str,
        age: Optional[int] = None,
        domain_only: bool = False,
        include_neither: bool = True
    ) -> Dict[str, Any]:
        trace_hit("lk_prediction_engine_runner_lkenginerunner_run")
        """
        Executes the engine lifecycle.
        Returns a dictionary containing all computed predictions and charts.
        """
        natal, full_payload = self.build_chart(dob, tob, place)

        rule_preds = None
        annual_preds = None
        pipe_error = None

        if not domain_only:
            pipe = self.build_pipeline()
            if pipe:
                try:
                    pipe.load_natal_baseline(natal)
                    rule_preds, _ = pipe.generate_predictions(natal)

                    if age is not None:
                        annual_chart = full_payload.get(f"chart_{age}")
                        if annual_chart:
                            annual_preds, _ = pipe.generate_predictions(annual_chart)
                    
                    # ENRICHMENT: Replace raw full_payload with forensic timeline
                    # (This hydrates logic and forensic_machine_ledger for every year)
                    charts_list = [full_payload[k] for k in sorted(full_payload.keys()) if k.startswith("chart_")]
                    full_payload = pipe.generate_full_payload(dob, dob, charts_list)
                    
                except Exception as e:
                    pipe_error = str(e)

        fate_entries = self.view.evaluate(natal, include_neither=include_neither)

        return {
            "natal_chart": natal,
            "full_payload": full_payload,
            "rule_predictions": rule_preds,
            "annual_predictions": annual_preds,
            "fate_entries": fate_entries,
            "pipeline_error": pipe_error
        }


# ------------------------------------------------------------------
# Validation / Regression Testing
# ------------------------------------------------------------------

BASELINE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "metrics_baseline.json")
REGRESSION_THRESHOLD = 0.05  # 5% F1 drop triggers failure


def run_validation(db_path: str, config_path: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Run all public figures through the engine and compare metrics against
    stored baselines. Exits with non-zero if any domain regresses >5%.

    Returns (passed, report_dict).
    """
    # 1. Run calibration to get current metrics
    calibrator = CalibrationModule(db_path)
    result = calibrator.calibrate()

    # 2. Build current metrics summary
    current_metrics: Dict[str, float] = {}
    for domain, fate_metrics in result.domain_metrics.items():
        for fate_type, m in fate_metrics.items():
            key = f"{domain}__{fate_type}"
            current_metrics[key] = m["f1"]

    # 3. Load baseline (if it exists)
    baseline: Dict[str, float] = {}
    if os.path.exists(BASELINE_PATH):
        with open(BASELINE_PATH, "r") as f:
            baseline = json.load(f)

    # 4. Compare
    regressions: List[Dict[str, Any]] = []
    improvements: List[Dict[str, Any]] = []
    new_domains: List[str] = []

    for key, current_f1 in current_metrics.items():
        if key in baseline:
            delta = current_f1 - baseline[key]
            if delta < -REGRESSION_THRESHOLD:
                regressions.append({
                    "domain": key,
                    "baseline_f1": round(baseline[key], 4),
                    "current_f1": round(current_f1, 4),
                    "delta": round(delta, 4),
                })
            elif delta > REGRESSION_THRESHOLD:
                improvements.append({
                    "domain": key,
                    "baseline_f1": round(baseline[key], 4),
                    "current_f1": round(current_f1, 4),
                    "delta": round(delta, 4),
                })
        else:
            new_domains.append(key)

    # 5. Build report
    passed = len(regressions) == 0
    report = {
        "passed": passed,
        "baseline_f1": result.baseline_f1,
        "regressions": regressions,
        "improvements": improvements,
        "new_domains": new_domains,
        "total_domains": len(current_metrics),
    }

    # 6. Print report
    _print_validation_report(report)

    # 7. Update baseline (always update after validation)
    with open(BASELINE_PATH, "w") as f:
        json.dump(current_metrics, f, indent=2)

    return passed, report


def _print_validation_report(report: Dict[str, Any]) -> None:
    """Print a human-readable validation report."""
    print("\n" + "=" * 70)
    print("ENGINE VALIDATION REPORT")
    print(f"Baseline F1: {report['baseline_f1']:.4f}")
    print(f"Domains evaluated: {report['total_domains']}")
    print(f"Status: {'PASSED' if report['passed'] else 'FAILED - REGRESSIONS DETECTED'}")
    print("=" * 70)

    if report["regressions"]:
        print("\n--- REGRESSIONS (>5% F1 drop) ---")
        for r in report["regressions"]:
            print(
                f"  {r['domain']}: {r['baseline_f1']:.4f} -> {r['current_f1']:.4f} "
                f"({r['delta']:+.4f})"
            )

    if report["improvements"]:
        print("\n--- IMPROVEMENTS (>5% F1 gain) ---")
        for imp in report["improvements"]:
            print(
                f"  {imp['domain']}: {imp['baseline_f1']:.4f} -> {imp['current_f1']:.4f} "
                f"({imp['delta']:+.4f})"
            )

    if report["new_domains"]:
        print(f"\n--- NEW DOMAINS ({len(report['new_domains'])}) ---")
        for d in report["new_domains"]:
            print(f"  {d}")

    print("=" * 70 + "\n")


# ------------------------------------------------------------------
# CLI Entry Point
# ------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Lal Kitab Engine Runner")
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run validation: compare current metrics against stored baselines",
    )
    parser.add_argument(
        "--db-path",
        default=os.path.join(os.path.dirname(__file__), "..", "..", "data", "public_figures.db"),
        help="Path to public_figures.db",
    )
    parser.add_argument(
        "--config-path",
        default=os.path.join(os.path.dirname(__file__), "..", "..", "data", "model_defaults.json"),
        help="Path to model_defaults.json",
    )
    args = parser.parse_args()

    if args.validate:
        passed, _ = run_validation(args.db_path, args.config_path)
        sys.exit(0 if passed else 1)
    else:
        print("Usage: python -m astroq.lk_prediction.engine_runner --validate")
        sys.exit(0)
