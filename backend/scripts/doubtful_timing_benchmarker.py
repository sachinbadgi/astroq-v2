"""
Doubtful Timing Benchmarker
============================

Comparative benchmarker: Baseline VarshphalTimingEngine vs. DoubtfulTimingEngine.

For each public figure:
    1. Generates natal + annual charts using the ChartGenerator.
    2. Runs BOTH engines on each event year.
    3. Compares Top-3 Hit Rate for the actual event year vs. noise years.
    4. Reports the "Improvement Delta" — how much the doubtful layer helps.

Usage:
    cd backend
    python -m scripts.doubtful_timing_benchmarker

Output:
    - Per-figure summary table.
    - Aggregate stats: hit rate, FPR, improvement delta.
    - Saved to: artifacts/reports/doubtful_timing_benchmark_report.json
"""

import json
import os
import sys
import traceback
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

# Ensure the backend package is importable from this script location
_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.normpath(os.path.join(_HERE, ".."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.varshphal_timing_engine import VarshphalTimingEngine
from astroq.lk_prediction.doubtful_timing_engine import DoubtfulTimingEngine


# ── CONFIG ────────────────────────────────────────────────────────────────
GROUND_TRUTH_PATH = os.path.join(_BACKEND, "data", "public_figures_ground_truth.json")
REPORT_PATH = os.path.normpath(
    os.path.join(_BACKEND, "..", "artifacts", "reports", "doubtful_timing_benchmark_report.json")
)
# Domains we will test timing confidence on
DOMAINS_TO_TEST = ["marriage", "finance", "health", "career_travel", "progeny"]
# How many non-event years to sample as "noise" years around each event
NOISE_WINDOW = 5


def load_ground_truth() -> List[Dict[str, Any]]:
    with open(GROUND_TRUTH_PATH, "r") as f:
        return json.load(f)


def generate_charts(figure: Dict[str, Any]) -> Tuple[Optional[Dict], Optional[Dict[int, Dict]]]:
    """Generate natal + per-age annual charts for a figure."""
    try:
        gen = ChartGenerator()
        dob   = figure["dob"]
        tob   = figure.get("tob", "12:00")
        place = figure.get("birth_place", "India")

        # Geocode the birthplace to get lat/lon/utc
        locations = gen.geocode_place(place)
        if not locations:
            print(f"  [GEOCODE FAIL] {figure['name']}: {place} — using defaults")
            lat, lon, utc = 20.0, 77.0, "+05:30"
        else:
            loc = locations[0]
            lat  = loc["latitude"]
            lon  = loc["longitude"]
            utc  = loc["utc_offset"]

        natal = gen.generate_chart(dob, tob, place, lat, lon, utc, chart_system="vedic")

        all_annual = gen.generate_annual_charts(natal, max_years=100)

        # Build age → chart dict
        annuals: Dict[int, Dict] = {}
        for key, chart in all_annual.items():
            age = chart.get("chart_period")
            if age is not None:
                annuals[age] = chart

        return natal, annuals
    except Exception as e:
        print(f"  [CHART ERROR] {figure['name']}: {e}")
        return None, None



def _confidence_score(confidence: str) -> int:
    """Convert confidence label to numeric score for comparison."""
    return {"None": 0, "Low": 1, "Medium": 2, "High": 3}.get(confidence, 0)


def evaluate_figure(
    figure: Dict[str, Any],
    baseline_engine: VarshphalTimingEngine,
    doubtful_engine: DoubtfulTimingEngine,
) -> Dict[str, Any]:
    """Run both engines on a single figure and compare results."""
    name = figure["name"]
    print(f"\n{'─'*60}")
    print(f"  Figure: {name}  ({figure.get('dob')})")

    natal, annuals = generate_charts(figure)
    if natal is None or not annuals:
        return {"name": name, "error": "chart_generation_failed"}

    events   = figure.get("events", [])
    results  = []

    for event in events:
        age    = event["age"]
        domain = event.get("domain", "career_travel")
        # Map ground truth domains to engine domains
        domain_map = {
            "career":   "career_travel",
            "legal":    "career_travel",
            "other":    "career_travel",
            "finance":  "finance",
            "health":   "health",
            "marriage": "marriage",
            "progeny":  "progeny",
        }
        engine_domain = domain_map.get(domain, "career_travel")

        event_annual = annuals.get(age)
        if event_annual is None:
            continue

        # Noise years: ages around the event that are NOT the event year
        noise_ages = [
            a for a in range(max(1, age - NOISE_WINDOW), age + NOISE_WINDOW + 1)
            if a != age and a in annuals
        ]

        try:
            # ── Baseline ──────────────────────────────────────────────────
            base_event   = baseline_engine.get_timing_confidence(natal, event_annual, age, engine_domain)
            base_noise   = [
                baseline_engine.get_timing_confidence(natal, annuals[a], a, engine_domain)
                for a in noise_ages
            ]

            # ── Doubtful Engine ───────────────────────────────────────────
            dbt_event   = doubtful_engine.get_timing_confidence(natal, event_annual, age, engine_domain)
            dbt_noise   = [
                doubtful_engine.get_timing_confidence(natal, annuals[a], a, engine_domain)
                for a in noise_ages
            ]
        except Exception as e:
            print(f"    [ENGINE ERROR] {name} age {age}: {e}")
            traceback.print_exc()
            continue

        base_event_score = _confidence_score(base_event["confidence"])
        dbt_event_score  = _confidence_score(dbt_event["confidence"])

        # Boolean hit: event year generates an absolute signal (confidence > Low)
        base_noise_scores = [_confidence_score(n["confidence"]) for n in base_noise]
        dbt_noise_scores  = [_confidence_score(n["confidence"]) for n in dbt_noise]

        base_hit = base_event_score > 1
        dbt_hit  = dbt_event_score > 1

        # FPR contribution: noise years that have an absolute signal (confidence > Low)
        base_fpr = sum(1 for s in base_noise_scores if s > 1) / max(len(noise_ages), 1)
        dbt_fpr  = sum(1 for s in dbt_noise_scores  if s > 1) / max(len(noise_ages), 1)

        improvement = dbt_hit and not base_hit
        regression  = base_hit and not dbt_hit

        print(f"    Event age={age} domain={engine_domain}: "
              f"Base={base_event['confidence']}(hit={base_hit}) "
              f"Dbt={dbt_event['confidence']}(hit={dbt_hit}) "
              f"Modifier={dbt_event.get('doubtful_confidence_modifier', 'N/A')} "
              f"{'✅ IMPROVE' if improvement else '⚠️ REGRESS' if regression else '─'}")

        results.append({
            "age":           age,
            "description":   event.get("description", ""),
            "domain":        engine_domain,

            "baseline_confidence": base_event["confidence"],
            "baseline_hit":        base_hit,
            "baseline_fpr":        round(base_fpr, 3),

            "doubtful_confidence": dbt_event["confidence"],
            "doubtful_hit":        dbt_hit,
            "doubtful_fpr":        round(dbt_fpr, 3),
            "doubtful_modifier":   dbt_event.get("doubtful_confidence_modifier", "Neutral"),
            "active_promises":     dbt_event.get("doubtful_promises", []),

            "improved":  improvement,
            "regressed": regression,
        })

    return {"name": name, "events": results}


def compute_aggregate_stats(all_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute aggregate metrics across all figures."""
    base_hits = base_total = 0
    dbt_hits  = dbt_total  = 0
    base_fpr_sum = dbt_fpr_sum = 0.0
    improvements = regressions = 0

    for figure_result in all_results:
        for evt in figure_result.get("events", []):
            base_total += 1
            dbt_total  += 1
            if evt["baseline_hit"]:
                base_hits += 1
            if evt["doubtful_hit"]:
                dbt_hits += 1
            base_fpr_sum += evt["baseline_fpr"]
            dbt_fpr_sum  += evt["doubtful_fpr"]
            if evt["improved"]:
                improvements += 1
            if evt["regressed"]:
                regressions += 1

    n = max(base_total, 1)
    return {
        "total_events":        base_total,
        "baseline_hit_rate":   round(base_hits / n, 3),
        "doubtful_hit_rate":   round(dbt_hits  / n, 3),
        "improvement_delta":   round((dbt_hits - base_hits) / n, 3),
        "baseline_avg_fpr":    round(base_fpr_sum / n, 3),
        "doubtful_avg_fpr":    round(dbt_fpr_sum  / n, 3),
        "fpr_reduction":       round((base_fpr_sum - dbt_fpr_sum) / n, 3),
        "improvements":        improvements,
        "regressions":         regressions,
    }


def print_summary(stats: Dict[str, Any]) -> None:
    print(f"\n{'='*60}")
    print("  DOUBTFUL TIMING BENCHMARK SUMMARY")
    print(f"{'='*60}")
    print(f"  Total events tested:     {stats['total_events']}")
    print(f"  Baseline Hit Rate:       {stats['baseline_hit_rate']*100:.1f}%")
    print(f"  Doubtful Hit Rate:       {stats['doubtful_hit_rate']*100:.1f}%")
    print(f"  Improvement Delta:       {stats['improvement_delta']*100:+.1f}%")
    print(f"  Baseline Avg FPR:        {stats['baseline_avg_fpr']*100:.1f}%")
    print(f"  Doubtful Avg FPR:        {stats['doubtful_avg_fpr']*100:.1f}%")
    print(f"  FPR Reduction:           {stats['fpr_reduction']*100:+.1f}%")
    print(f"  Cases Improved:          {stats['improvements']}")
    print(f"  Cases Regressed:         {stats['regressions']}")
    print(f"{'='*60}\n")


def main():
    print(f"\n{'='*60}")
    print("  Doubtful Timing Engine Benchmarker")
    print(f"  Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    figures = load_ground_truth()
    print(f"  Loaded {len(figures)} public figures from ground truth.")

    baseline_engine = VarshphalTimingEngine()
    doubtful_engine = DoubtfulTimingEngine()

    all_results = []
    for figure in figures:
        result = evaluate_figure(figure, baseline_engine, doubtful_engine)
        all_results.append(result)

    stats = compute_aggregate_stats(all_results)
    print_summary(stats)

    # Save JSON report
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    report = {
        "generated_at": datetime.now().isoformat(),
        "aggregate":    stats,
        "figures":      all_results,
    }
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)
    print(f"  Report saved to: {REPORT_PATH}\n")


if __name__ == "__main__":
    main()
