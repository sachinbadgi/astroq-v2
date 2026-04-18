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

# Re-export the shared normalizer so callers can import from here
from astroq.lk_prediction.lse_researcher import normalize_domain


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

        # Group predictions by NORMALISED domain for faster lookup
        preds_by_domain: dict[str, list[LKPrediction]] = {}
        unused_preds: list[LKPrediction] = []
        for p in predictions:
            d = normalize_domain(p.domain)
            if d not in preds_by_domain:
                preds_by_domain[d] = []
            preds_by_domain[d].append(p)
            unused_preds.append(p)

        for event in life_event_log:
            domain = normalize_domain(event.get("domain", ""))
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
                # Mark as used for FP tracking
                if best_match in unused_preds:
                    unused_preds.remove(best_match)
                    
                raw_offset = float(best_match.peak_age - actual_age)
                entry["predicted_peak_age"] = best_match.peak_age
                entry["offset"] = raw_offset
                entry["is_hit"] = abs(raw_offset) <= 2.0  # ≤2 year window

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

        # Domain level scores
        domain_stats: dict[str, dict[str, int]] = {}
        for entry in entries:
            d = normalize_domain(entry["life_event"].get("domain", "General"))
            if d not in domain_stats:
                domain_stats[d] = {"hits": 0, "total": 0}
            domain_stats[d]["total"] += 1
            if entry["is_hit"]:
                domain_stats[d]["hits"] += 1
        
        # Domain level scores
        domain_scores = {
            d: round(s["hits"] / s["total"], 4) if s["total"] > 0 else 0.0
            for d, s in domain_stats.items()
        }

        # Domain FP counts
        domain_fp_counts: dict[str, int] = {}
        for p in unused_preds:
            # Handle multi-domain predictions (separated by '/')
            sub_domains = [sd.strip() for sd in p.domain.split("/") if sd.strip()]
            for sd in sub_domains:
                d = normalize_domain(sd)
                domain_fp_counts[d] = domain_fp_counts.get(d, 0) + 1


        # Compute Top-3 Competitive Hit Rate
        top3_hits = 0
        domain_top3_stats: dict[str, dict[str, int]] = {}
        
        for event in life_event_log:
            d = normalize_domain(event.get("domain", ""))
            actual_age = event.get("age", 0)
            
            p_list = preds_by_domain.get(d, [])
            if not p_list:
                # Check for messy containment
                for dn, pl in preds_by_domain.items():
                    if d in dn or dn in d:
                        p_list = pl
                        break
            
            # NEW: Domain Karaka & Purity Logic
            DOMAIN_KARAKAS = {
                "marriage": ["Venus", "Jupiter", "Moon"],
                "career": ["Sun", "Saturn", "Mars", "Mercury"],
                "profession": ["Sun", "Saturn", "Mars", "Mercury"],
                "wealth": ["Jupiter", "Venus", "Moon"],
                "health": ["Sun", "Mars", "Saturn"]
            }

            def get_rank_tuple(p):
                purity_bonus = 1.0
                domain_lower = d.lower()
                
                # 1. Primary Domain check
                p_domain_lower = p.domain.lower()
                target_domain_lower = d.lower()
                if target_domain_lower in p_domain_lower:
                    if p_domain_lower.startswith(target_domain_lower):
                        purity_bonus *= 1.0 # Primary hit
                    else:
                        purity_bonus *= 0.5 # Secondary hit (50% penalty)
                else:
                    purity_bonus *= 0.1 # Not in domain at all
                
                # 2. Karaka Synergy check
                karakas = DOMAIN_KARAKAS.get(domain_lower, [])
                planet_name = p.source_planets[0] if p.source_planets else ""
                if karakas and planet_name.capitalize() in karakas:
                    purity_bonus *= 1.2 # 20% boost for domain-appropriate planets
                
                # We sort by (Weighted Probability, Weighted Magnitude)
                # To ensure Rank 1 is truly distinct
                return (round(p.probability * purity_bonus, 4), round(p.magnitude * purity_bonus, 4))

            ranked = sorted(p_list, key=get_rank_tuple, reverse=True)
            
            # Select Top 3 UNIQUE ages
            top_ages = []
            for r in ranked:
                if r.peak_age not in top_ages:
                    top_ages.append(r.peak_age)
                if len(top_ages) >= 3:
                    break
            
            # Hit if actual age matches any top age within +/- 1 (stricter window)
            is_top3_hit = False
            for tage in top_ages:
                if abs(tage - actual_age) <= 1:
                    is_top3_hit = True
                    break
            
            if is_top3_hit:
                top3_hits += 1
                
            if d not in domain_top3_stats:
                domain_top3_stats[d] = {"hits": 0, "total": 0}
            domain_top3_stats[d]["total"] += 1
            if is_top3_hit:
                domain_top3_stats[d]["hits"] += 1

        top3_hit_rate = (top3_hits / count) if count > 0 else 0.0
        domain_top_3_scores = {
            d: round(s["hits"] / s["total"], 4) if s["total"] > 0 else 0.0
            for d, s in domain_top3_stats.items()
        }

        return {
            "entries": entries,
            "hit_rate": round(hit_rate, 4),
            "top_3_hit_rate": round(top3_hit_rate, 4),
            "mean_offset": round(mean_offset, 4),
            "total": count,
            "hits": hits,
            "domain_scores": domain_scores,
            "domain_top_3_scores": domain_top_3_scores,
            "domain_fp_counts": domain_fp_counts,
            "contradictions": sorted(list(contradictions)),
            "false_positives": [f"{p.prediction_text} [{' '.join(p.source_rules) if p.source_rules else 'NO_ID'}]" for p in unused_preds]
        }




    def compute_hit_rate(self, gap_report: GapReport) -> float:
        """Helper to get hit rate from report."""
        return gap_report["hit_rate"]

    def compute_mean_offset(self, gap_report: GapReport) -> float:
        """Helper to get mean offset from report."""
        return gap_report["mean_offset"]
