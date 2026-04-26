"""
Analyze Missed Events
=====================
This script analyzes events that were NOT predicted as a Top-3 hit by the Baseline (Fixed Fate) engine,
and checks if those specific events correspond to people who have a "Doubtful Promise" in their natal chart.
"""

import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.normpath(os.path.join(_HERE, ".."))
REPORT_PATH = os.path.join(_BACKEND, "..", "artifacts", "reports", "doubtful_timing_benchmark_report.json")

def main():
    if not os.path.exists(REPORT_PATH):
        print(f"Report not found at {REPORT_PATH}")
        return

    with open(REPORT_PATH, "r") as f:
        report = json.load(f)

    total_events = report.get("aggregate", {}).get("total_events", 0)
    baseline_hits = 0
    missed_events = []

    for figure in report.get("figures", []):
        for event in figure.get("events", []):
            if event.get("baseline_hit", False):
                baseline_hits += 1
            else:
                missed_events.append({
                    "figure": figure["name"],
                    "age": event["age"],
                    "description": event.get("description", ""),
                    "domain": event.get("domain", ""),
                    "active_doubtful_promises": event.get("active_promises", [])
                })

    missed_count = len(missed_events)
    missed_with_doubtful = sum(1 for e in missed_events if len(e["active_doubtful_promises"]) > 0)
    missed_without_doubtful = missed_count - missed_with_doubtful

    print(f"===========================================")
    print(f"Fixed Fate vs. Doubtful Promise Analysis")
    print(f"===========================================")
    print(f"Total Events Evaluated: {total_events}")
    print(f"Events predicted by Fixed Fate (Baseline Hit): {baseline_hits} ({(baseline_hits/total_events)*100:.1f}%)")
    print(f"Events missed by Fixed Fate: {missed_count} ({(missed_count/total_events)*100:.1f}%)")
    print(f"-------------------------------------------")
    print(f"Of the {missed_count} missed events:")
    print(f"  - Had a Doubtful Natal Promise: {missed_with_doubtful} ({(missed_with_doubtful/missed_count)*100:.1f}%)")
    print(f"  - Did NOT have a Doubtful Promise: {missed_without_doubtful} ({(missed_without_doubtful/missed_count)*100:.1f}%)")
    print(f"\nConclusion:")
    if missed_with_doubtful == missed_count:
        print("  YES, all remaining (missed) events are tied to doubtful natal promises.")
    else:
        print("  NO, the remaining events are NOT always doubtful in natal.")
        print("  Other factors (missing rules, inaccurate birth times, or different meta-patterns) are causing these misses.")

if __name__ == "__main__":
    main()
