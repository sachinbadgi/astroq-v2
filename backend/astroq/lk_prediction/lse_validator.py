"""
Phase 2: Validator Agent (AutoResearch 2.0)

Compares engine predictions against supplied life events to produce a GapReport.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from astroq.lk_prediction.data_contracts import (
        LKPrediction,
        LifeEventLog,
        GapReport,
        GapEntry,
        LifeEvent,
    )


class ValidatorAgent:
    """
    Back-tests engine predictions against a LifeEventLog.
    """

    def compare_to_events(
        self, predictions: list[LKPrediction], life_event_log: LifeEventLog
    ) -> GapReport:
        """
        Match each LifeEvent to the nearest LKPrediction by domain.
        Computes offset, hit status, and reports contradictions.
        """
        entries: list[GapEntry] = []
        hits = 0
        total_offset = 0.0
        contradictions = set()

        # Group predictions by domain for faster lookup
        preds_by_domain: dict[str, list[LKPrediction]] = {}
        for p in predictions:
            d = p.domain.lower()
            if d not in preds_by_domain:
                preds_by_domain[d] = []
            preds_by_domain[d].append(p)

        for event in life_event_log:
            domain = event.get("domain", "").lower()
            actual_age = event.get("age", 0)
            
            # Find matching predictions for this domain
            best_match: Optional[LKPrediction] = None
            min_offset = float("inf")

            for d_name, preds in preds_by_domain.items():
                if domain in d_name or d_name in domain:
                    for m in preds:
                        offset = abs(m.peak_age - actual_age)
                        if offset < min_offset:
                            min_offset = offset
                            best_match = m

            entry: GapEntry = {
                "life_event": event,
                "predicted_peak_age": None,
                "offset": None,
                "is_hit": False,
                "matched_prediction_text": "",
                "source_planets": [],
                "source_houses": []
            }

            if best_match:
                raw_offset = float(best_match.peak_age - actual_age)
                entry["predicted_peak_age"] = best_match.peak_age
                entry["offset"] = raw_offset
                entry["is_hit"] = abs(raw_offset) <= 1.0  # DEC-004

                entry["matched_prediction_text"] = best_match.prediction_text
                entry["source_planets"] = best_match.source_planets
                entry["source_houses"] = best_match.source_houses
                
                if entry["is_hit"]:
                    hits += 1
                total_offset += abs(raw_offset)
            else:
                contradictions.add(domain)

            entries.append(entry)

        count = len(life_event_log)
        hit_rate = (hits / count) if count > 0 else 0.0
        mean_offset = (total_offset / count) if count > 0 else 0.0

        return {
            "entries": entries,
            "hit_rate": round(hit_rate, 4),
            "mean_offset": round(mean_offset, 4),
            "total": count,
            "hits": hits,
            "contradictions": sorted(list(contradictions))
        }

    def compute_hit_rate(self, gap_report: GapReport) -> float:
        """Helper to get hit rate from report."""
        return gap_report["hit_rate"]

    def compute_mean_offset(self, gap_report: GapReport) -> float:
        """Helper to get mean offset from report."""
        return gap_report["mean_offset"]
