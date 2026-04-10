"""
AutoResearch 2.0 — Full Benchmark: Domain-Based Hit Rate Report

Runs LSEOrchestrator.solve_chart() over ALL public figures in astroq_gt.db,
collects GapReports, and writes a domain-breakdown Markdown report to:

    artifacts/reports/domain_hit_rate_report.md

Usage:
    python backend/scripts/run_all_figures_domain_report.py
    python backend/scripts/run_all_figures_domain_report.py --batch-size 10 --limit 20
"""

import argparse
import logging
import os
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
from typing import Any

sys.path.append(os.path.join(os.getcwd(), "backend"))

from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.data_contracts import ChartData, LifeEventLog
from astroq.lk_prediction.lse_chart_dna import ChartDNARepository
from astroq.lk_prediction.lse_orchestrator import LSEOrchestrator
from astroq.lk_prediction.lse_researcher import normalize_domain

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DB_PATH       = "backend/data/astroq_gt.db"
DEFAULTS_PATH = "backend/data/model_defaults.json"
REPORT_DIR    = "artifacts/reports"
REPORT_PATH   = os.path.join(REPORT_DIR, "domain_hit_rate_report.md")

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("domain_report")


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _norm_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def fetch_all_figures(db_path: str) -> list[dict[str, Any]]:
    """Return every birth-chart row that has at least one benchmark event."""
    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()

    cur.execute(
        "SELECT id, client_name, birth_date, birth_time, birth_place, "
        "latitude, longitude, timezone_name FROM lk_birth_charts"
    )
    charts = cur.fetchall()

    cur.execute(
        "SELECT figure_name, event_name, age, domain FROM benchmark_ground_truth"
    )
    events_raw = cur.fetchall()
    conn.close()

    # Group events by normalised figure name
    events_by_norm: dict[str, list[dict]] = defaultdict(list)
    for fig_name, event_name, age, domain in events_raw:
        norm = _norm_name(fig_name)
        events_by_norm[norm].append({
            "age":         int(age) if age is not None else 0,
            "domain":      (domain or "career").lower(),
            "description": event_name,
            "is_verified": True,
        })

    figures = []
    for bc_id, name, dob, tob, place, lat, lon, tz in charts:
        norm = _norm_name(name)
        if norm in events_by_norm:
            figures.append({
                "id":    bc_id,
                "name":  name,
                "dob":   dob,
                "tob":   tob,
                "place": place,
                "lat":   lat,
                "lon":   lon,
                "tz":    tz,
                "events": events_by_norm[norm],
            })
        else:
            logger.debug("No events for %s", name)

    logger.info("Loaded %d figures with events (out of %d charts).", len(figures), len(charts))
    return figures


# ---------------------------------------------------------------------------
# Per-figure run
# ---------------------------------------------------------------------------

def run_figure(
    fig: dict[str, Any],
    generator: ChartGenerator,
    orchestrator: LSEOrchestrator,
) -> dict[str, Any]:
    """Generate charts and run LSE; return a result dict."""
    name = fig["name"]
    try:
        payload = generator.build_full_chart_payload(
            dob_str=fig["dob"],
            tob_str=fig["tob"],
            place_name=fig["place"],
            latitude=fig["lat"],
            longitude=fig["lon"],
            utc_string=fig["tz"],
        )
        natal_chart: ChartData = payload["chart_0"]
        annual_charts: dict[int, ChartData] = {
            int(k.split("_")[1]): v
            for k, v in payload.items()
            if k.startswith("chart_") and k != "chart_0"
        }

        result = orchestrator.solve_chart(
            birth_chart=natal_chart,
            annual_charts=annual_charts,
            life_event_log=fig["events"],
            figure_id=name,
        )

        gap = result.gap_report
        hit_details = {}
        false_positives = []
        domain_fp_counts = {}
        if gap:
            hit_details = gap.get("domain_scores", {})
            false_positives = gap.get("false_positives", [])
            domain_fp_counts = gap.get("domain_fp_counts", {})

        # Pull stats from result
        hit_rate   = result.chart_dna.back_test_hit_rate if result.chart_dna else 0.0
        converged  = result.converged
        iterations = result.iterations_run

        return {
            "name":        name,
            "hit_rate":    hit_rate,
            "converged":   converged,
            "iterations":  iterations,
            "total_events": len(fig["events"]),
            "events":      fig["events"],  # RESTORED: needed for domain aggregation
            "domain_scores": hit_details,
            "domain_fp_counts": domain_fp_counts,
            "false_positives": false_positives,
            "error":       None,
        }


    except Exception as exc:
        logger.error("Error processing %s: %s", name, exc)
        return {
            "name":        name,
            "hit_rate":    0.0,
            "converged":   False,
            "iterations":  0,
            "total_events": len(fig["events"]),
            "events":      fig["events"],
            "error":       str(exc),
        }


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def build_report(
    results: list[dict[str, Any]],
    elapsed_seconds: float,
) -> str:
    """Produce a Markdown report from collected results."""

    ok      = [r for r in results if not r["error"]]
    errors  = [r for r in results if r["error"]]
    total   = len(results)

    # Overall hit rate (weighted by event count)
    total_events  = sum(r["total_events"] for r in ok)
    weighted_hits = sum(r["hit_rate"] * r["total_events"] for r in ok)
    overall_hr    = (weighted_hits / total_events) if total_events else 0.0

    converged_count = sum(1 for r in ok if r["converged"])

    # Per-domain metrics
    domain_events: dict[str, int]   = defaultdict(int)
    domain_hits: dict[str, int]     = defaultdict(int)
    domain_fps: dict[str, int]      = defaultdict(int) 
    total_fps = 0

    for r in ok:
        total_fps += len(r["false_positives"])
        # Domain hits
        for d, rate in r["domain_scores"].items():
            count = sum(1 for ev in r.get("events", []) if normalize_domain(ev.get("domain", "")) == d)
            if count == 0: count = 1 # Fallback
            domain_events[d] += count
            domain_hits[d] += int(rate * count)
        
        # Domain FPs
        for d, fp_count in r["domain_fp_counts"].items():
            domain_fps[d] += fp_count

    domain_rows = []
    all_domains = sorted(set(domain_events.keys()) | set(domain_fps.keys()))
    for d in all_domains:
        n     = domain_events[d]
        hr    = (domain_hits[d] / n) if n else 0.0
        fps   = domain_fps[d]
        domain_rows.append((d, n, hr, fps))
    domain_rows.sort(key=lambda x: x[2])  # worst HR first

    # Per-figure table sorted by hit rate ascending
    sorted_results = sorted(ok, key=lambda r: r["hit_rate"])

    lines = [
        "# Domain-Based Hit Rate Report",
        f"\n_Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}_",
        f"_Engine: LSEOrchestrator · Hit window: ≤ 2 years · Run time: {elapsed_seconds:.0f}s_\n",

        "## Summary",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Figures processed | {total} |",
        f"| Figures with errors | {len(errors)} |",
        f"| Figures converged | {converged_count} / {len(ok)} |",
        f"| Total life events | {total_events} |",
        f"| Total False Positives | {total_fps} |",
        f"| **Overall hit rate** | **{overall_hr:.1%}** |",
        "",

        "## Per-Domain Noise & Hit Rate",
        "_(Sorted worst → best Hit Rate. FP = False Positives.)_\n",
        "| Domain | Events | Hit Rate | False Positives |",
        "|--------|--------|----------|-----------------|",
    ]
    for d, n, hr, fps in domain_rows:
        lines.append(f"| {d} | {n} | {hr:.1%} | {fps} |")

    lines += [
        "",
        "## Per-Figure Audit",
        "_(Sorted worst → best hit rate. FP = False Positives/Redundant Predictions.)_\n",
        "| # | Figure | Events | Hit Rate | FP | Converged | Iterations |",
        "|---|--------|--------|----------|----|-----------|------------|",
    ]
    for i, r in enumerate(sorted_results, 1):
        conv = "✓" if r["converged"] else "✗"
        fp_count = len(r["false_positives"])
        lines.append(
            f"| {i} | {r['name']} | {r['total_events']} "
            f"| {r['hit_rate']:.1%} | {fp_count} | {conv} | {r['iterations']} |"
        )

    if errors:
        lines += [
            "",
            "## Errors",
            "| Figure | Error |",
            "|--------|-------|",
        ]
        for e in errors:
            msg = e["error"].replace("|", "\\|")[:120]
            lines.append(f"| {e['name']} | {msg} |")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(batch_size: int = 20, limit: int | None = None, start_index: int = 0) -> None:
    import time

    logger.info("=== Domain-Based Hit Rate Benchmark ===")
    figures = fetch_all_figures(DB_PATH)
    figures = figures[start_index:]
    if limit:
        figures = figures[:limit]

    logger.info("Processing %d figures in batches of %d.", len(figures), batch_size)

    config      = ModelConfig(db_path=DB_PATH, defaults_path=DEFAULTS_PATH)
    generator   = ChartGenerator()
    orchestrator = LSEOrchestrator(config)
    repo        = ChartDNARepository(DB_PATH)

    results: list[dict[str, Any]] = []
    t0 = time.monotonic()

    for batch_start in range(0, len(figures), batch_size):
        batch = figures[batch_start: batch_start + batch_size]
        batch_num = batch_start // batch_size + 1
        logger.info("--- Batch %d (%d figures) ---", batch_num, len(batch))

        for fig in batch:
            logger.info("  Processing: %s", fig["name"])
            res = run_figure(fig, generator, orchestrator)
            results.append(res)

            # Persist ChartDNA for converged figures
            if not res["error"]:
                pass  # DNA already saved inside solve_chart via repo if wired

    elapsed = time.monotonic() - t0
    logger.info("All done in %.0fs. Building report...", elapsed)

    report_md = build_report(results, elapsed)

    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report_md)

    logger.info("Report written to: %s", REPORT_PATH)

    # Quick console summary
    ok = [r for r in results if not r["error"]]
    total_events = sum(r["total_events"] for r in ok)
    weighted_hits = sum(r["hit_rate"] * r["total_events"] for r in ok)
    overall_hr = (weighted_hits / total_events) if total_events else 0.0
    print(f"\n{'='*60}")
    print(f"OVERALL HIT RATE: {overall_hr:.1%}  (across {len(ok)} figures, {total_events} events)")
    print(f"ERRORS: {len(results) - len(ok)}")
    print(f"Report: {REPORT_PATH}")
    print(f"{'='*60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Domain-based hit rate benchmark")
    parser.add_argument("--batch-size",  type=int, default=20)
    parser.add_argument("--limit",       type=int, default=None)
    parser.add_argument("--start-index", type=int, default=0)
    args = parser.parse_args()
    run(batch_size=args.batch_size, limit=args.limit, start_index=args.start_index)
