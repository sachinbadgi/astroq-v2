"""
Dump Missed Events
==================
Lists the 22 events missed by the Fixed Fate baseline engine and categorizes them.
"""

import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.normpath(os.path.join(_HERE, ".."))
REPORT_PATH = os.path.join(_BACKEND, "..", "artifacts", "reports", "doubtful_timing_benchmark_report.json")

def determine_polarity(domain: str, description: str) -> str:
    desc_lower = description.lower()
    
    # Check for obvious malefic keywords
    malefic_keywords = ["death", "accident", "fired", "divorce", "loss", "cancer", "arrest", "jail", "collapse", "assassination", "resignation"]
    if any(k in desc_lower for k in malefic_keywords):
        return "Malefic"
        
    if domain == "health":
        return "Malefic"
        
    if domain in ["marriage", "progeny"]:
        return "Benefic"
        
    # Default to benefic for career/finance if no bad words found
    return "Benefic"

def main():
    if not os.path.exists(REPORT_PATH):
        print(f"Report not found at {REPORT_PATH}")
        return

    with open(REPORT_PATH, "r") as f:
        report = json.load(f)

    missed_events = []

    for figure in report.get("figures", []):
        for event in figure.get("events", []):
            if not event.get("baseline_hit", False):
                missed_events.append({
                    "figure": figure["name"],
                    "age": event["age"],
                    "description": event.get("description", ""),
                    "domain": event.get("domain", ""),
                    "polarity": determine_polarity(event.get("domain", ""), event.get("description", ""))
                })

    malefic_count = sum(1 for e in missed_events if e["polarity"] == "Malefic")
    benefic_count = sum(1 for e in missed_events if e["polarity"] == "Benefic")

    print(f"===========================================")
    print(f"Details of Missed Events (Baseline)")
    print(f"===========================================")
    print(f"Total Missed: {len(missed_events)}")
    print(f"Malefic (Sudden Strikes, Death, Loss): {malefic_count}")
    print(f"Benefic (Marriage, Success, Progeny): {benefic_count}")
    print(f"-------------------------------------------")
    
    print("\n--- MALEFIC MISSED EVENTS ---")
    for e in missed_events:
        if e["polarity"] == "Malefic":
            print(f"  [{e['domain'].upper()}] {e['figure']} (Age {e['age']}): {e['description']}")
            
    print("\n--- BENEFIC MISSED EVENTS ---")
    for e in missed_events:
        if e["polarity"] == "Benefic":
            print(f"  [{e['domain'].upper()}] {e['figure']} (Age {e['age']}): {e['description']}")

if __name__ == "__main__":
    main()
