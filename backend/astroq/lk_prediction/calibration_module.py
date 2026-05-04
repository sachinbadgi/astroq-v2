"""
CalibrationModule
=================
Auto-tunes engine thresholds using ground-truth `is_event` labels
from the public_figures.db `raw_pattern_occurrences` table.

Usage:
    calibrator = CalibrationModule(db_path)
    calibrated = calibrator.calibrate()
    # calibrated dict contains optimized thresholds for FidelityGate,
    # AspectFidelityEvaluator, and timing engine confidence cutoffs.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class DomainMetrics:
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0

    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom > 0 else 0.0

    @property
    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom > 0 else 0.0

    @property
    def specificity(self) -> float:
        denom = self.fp + self.tn
        return self.tn / denom if denom > 0 else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "tp": self.tp, "fp": self.fp, "fn": self.fn, "tn": self.tn,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "specificity": round(self.specificity, 4),
            "f1": round(self.f1, 4),
        }


@dataclass
class AxisMetrics:
    """Precision of a given dignity-pattern axis, computed from raw_pattern_occurrences."""
    axis: str
    tp: int = 0  # pattern fired AND is_event=1
    fp: int = 0  # pattern fired AND is_event=0

    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom > 0 else 0.0

    @property
    def sample_count(self) -> int:
        return self.tp + self.fp

    def to_dict(self) -> Dict[str, Any]:
        return {
            "axis": self.axis,
            "tp": self.tp,
            "fp": self.fp,
            "precision": round(self.precision, 4),
            "sample_count": self.sample_count,
        }


@dataclass
class CalibrationResult:
    domain_metrics: Dict[str, Dict[str, DomainMetrics]] = field(default_factory=dict)
    axis_metrics: Dict[str, AxisMetrics] = field(default_factory=dict)  # keyed by axis label
    recommended_thresholds: Dict[str, Any] = field(default_factory=dict)
    baseline_f1: float = 0.0


class CalibrationModule:
    """
    Uses ground-truth event labels to compute empirical performance
    and recommend threshold adjustments for all engine components.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def calibrate(self) -> CalibrationResult:
        """
        Main entry point. Returns calibrated thresholds and per-domain metrics.
        """
        self._conn = sqlite3.connect(self.db_path)
        try:
            # Load ground truth from raw_pattern_occurrences
            ground_truth = self._load_ground_truth()

            # Compute per-domain, per-fate_type metrics
            domain_metrics = self._compute_domain_metrics(ground_truth)

            # Compute per-axis metrics
            axis_metrics = self._compute_axis_metrics(ground_truth)

            # Derive recommended thresholds
            recommendations = self._derive_recommendations(domain_metrics, axis_metrics)

            # Compute overall baseline F1 (macro-average across domains)
            f1s = []
            for dm in domain_metrics.values():
                for m in dm.values():
                    if (m.tp + m.fn) > 0:  # only domains with ground truth
                        f1s.append(m.f1)
            baseline_f1 = sum(f1s) / len(f1s) if f1s else 0.0

            result = CalibrationResult(
                domain_metrics={
                    d: {ft: m.to_dict() for ft, m in fts.items()}
                    for d, fts in domain_metrics.items()
                },
                axis_metrics={a: m.to_dict() for a, m in axis_metrics.items()},
                recommended_thresholds=recommendations,
                baseline_f1=round(baseline_f1, 4),
            )

            logger.info(
                "Calibration complete: %d domains, %d axes, baseline F1=%.4f",
                len(domain_metrics), len(axis_metrics), baseline_f1,
            )
            return result

        finally:
            self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------ #
    # Data Loading                                                        #
    # ------------------------------------------------------------------ #

    def _load_ground_truth(self) -> List[Dict[str, Any]]:
        """Load all pattern occurrences with event labels."""
        cursor = self._conn.execute("""
            SELECT domain, fate_type, pattern_id, is_event,
                   source_planet, target_planet, age
            FROM raw_pattern_occurrences
        """)
        columns = [c[0] for c in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    # ------------------------------------------------------------------ #
    # Metric Computation                                                  #
    # ------------------------------------------------------------------ #

    def _compute_domain_metrics(
        self, rows: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, DomainMetrics]]:
        """Compute TP/FP/FN/TN per (domain, fate_type)."""
        # Count total events per (domain, fate_type) from ground truth
        event_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        # Count pattern firings per (domain, fate_type)
        firing_counts: Dict[str, Dict[str, Tuple[int, int]]] = defaultdict(
            lambda: defaultdict(lambda: (0, 0))  # (total_firings, event_firings)
        )

        # We need to count unique (figure_id, domain, age) events vs noise
        # But raw_pattern_occurrences doesn't have figure_id directly.
        # Use the existing engine_metrics table for per-domain totals.
        cursor = self._conn.execute(
            "SELECT domain, fate_type, tp, fn, fp, tn FROM engine_metrics"
        )
        result: Dict[str, Dict[str, DomainMetrics]] = defaultdict(dict)
        for row in cursor.fetchall():
            d, ft, tp, fn, fp, tn = row
            result[d][ft] = DomainMetrics(tp=tp, fp=fp, fn=fn, tn=tn)

        return dict(result)

    def _compute_axis_metrics(
        self, rows: List[Dict[str, Any]]
    ) -> Dict[str, AxisMetrics]:
        """
        Compute per-axis precision from raw_pattern_occurrences.

        Approach: for each row with a source-target planet pair, infer the
        likely Lal Kitab axis from the dignity pair pattern using
        AspectFidelityEvaluator thresholds. Count TP/FP per axis-dignity
        pattern. This avoids the need for house lookups (which aren't directly
        available in raw_pattern_occurrences).

        A row contributes to an axis bucket when:
          - source_dignity and target_dignity are both non-NULL
          - The dignity category pair (Low/Medium/High × Low/Medium/High)
            maps to a known Lal Kitab axis pattern.

        Dignity-to-axis mapping heuristics (from empirical research):
          Low×Low  → 1-8 Takkar axis   (confrontation paradox)
          High×Med → 2-6 Gali axis     (sweet spot)
          Any×High → 1-7 Opposition    (strong shield)
          Any×Low  → 4-10 Square       (weak anvil)
          other    → 3-11 Support      (general case)
        """
        from .aspect_fidelity_evaluator import AspectFidelityEvaluator

        afe = AspectFidelityEvaluator()

        def _infer_axis(src_dignity: float, tgt_dignity: float) -> str:
            """Map dignity pair to the most likely Lal Kitab axis."""
            src_cat = afe.categorize(src_dignity)
            tgt_cat = afe.categorize(tgt_dignity)

            if src_cat == "Low" and tgt_cat == "Low":
                return "1-8"   # Takkar Paradox
            if src_cat == "High" and tgt_cat == "Medium":
                return "2-6"   # Gali Sweet Spot
            if tgt_cat == "High":
                return "1-7"   # Strong Shield (Opposition)
            if tgt_cat == "Low":
                return "4-10"  # Weak Anvil (Square)
            return "3-11"      # General support / unknown

        axis_data: Dict[str, AxisMetrics] = {}
        rows_with_dignity = [
            r for r in rows
            if r.get("source_dignity") is not None
            and r.get("target_dignity") is not None
        ]

        if not rows_with_dignity:
            logger.warning(
                "CalibrationModule: no rows with source_dignity/target_dignity — "
                "axis metrics unavailable. Run the fuzzer to populate "
                "raw_pattern_occurrences with dignity fields."
            )
            return {}

        for row in rows_with_dignity:
            src_d = float(row["source_dignity"])
            tgt_d = float(row["target_dignity"])
            axis  = _infer_axis(src_d, tgt_d)
            is_ev = int(row.get("is_event", 0))

            if axis not in axis_data:
                axis_data[axis] = AxisMetrics(axis=axis)

            if is_ev:
                axis_data[axis].tp += 1
            else:
                axis_data[axis].fp += 1

        logger.info(
            "CalibrationModule: computed axis metrics from %d dignity rows across %d axes",
            len(rows_with_dignity), len(axis_data),
        )
        return axis_data

    # ------------------------------------------------------------------ #
    # Threshold Derivation                                                #
    # ------------------------------------------------------------------ #

    def _derive_recommendations(
        self,
        domain_metrics: Dict[str, Dict[str, DomainMetrics]],
        axis_metrics: Dict[str, AxisMetrics],
    ) -> Dict[str, Any]:
        """
        Derive recommended threshold adjustments from empirical data.

        Strategy:
        - For domains with recall < 10%: lower the gate multipliers
        - For domains with precision < 10%: tighten the gate multipliers
        - Auto-tune AspectFidelityEvaluator thresholds from axis precision
        """
        recommendations: Dict[str, Any] = {
            "fidelity_gate": {},
            "aspect_evaluator": {},
            "timing_engine": {},
        }

        # ── FidelityGate adjustments per domain ────────────────────────────────
        for domain, fate_metrics in domain_metrics.items():
            for fate_type, m in fate_metrics.items():
                key = f"{domain}__{fate_type}"
                if m.recall < 0.10 and (m.tp + m.fn) > 5:
                    recommendations["fidelity_gate"][key] = {
                        "action": "loosen",
                        "current_recall": round(m.recall, 4),
                        "current_precision": round(m.precision, 4),
                        "suggested_base_multiplier": 0.90,
                    }
                elif m.precision < 0.10 and (m.tp + m.fp) > 5:
                    recommendations["fidelity_gate"][key] = {
                        "action": "tighten",
                        "current_recall": round(m.recall, 4),
                        "current_precision": round(m.precision, 4),
                        "suggested_base_multiplier": 0.35,
                    }

        # ── AspectFidelityEvaluator threshold tuning from real axis data ───────
        if axis_metrics:
            # Use precision from high-sample axes to suggest threshold adjustments.
            # Takkar (1-8) paradox: if precision > 0.75, LOW_THRESHOLD can be lowered.
            takkar = axis_metrics.get("1-8")
            if takkar and takkar.sample_count > 50:
                if takkar.precision > 0.75:
                    recommendations["aspect_evaluator"]["low_threshold"] = -1.5  # raise (less strict)
                elif takkar.precision < 0.40:
                    recommendations["aspect_evaluator"]["low_threshold"] = -2.5  # lower (more strict)

            gali = axis_metrics.get("2-6")
            if gali and gali.sample_count > 50:
                if gali.precision > 0.85:
                    recommendations["aspect_evaluator"]["high_threshold"] = 2.0  # lower threshold (more hits)
                elif gali.precision < 0.60:
                    recommendations["aspect_evaluator"]["high_threshold"] = 2.5  # raise (stricter)

            # Fill in defaults for any not yet set
            recommendations["aspect_evaluator"].setdefault(
                "low_threshold",
                -2.0  # current default
            )
            recommendations["aspect_evaluator"].setdefault(
                "high_threshold",
                2.2   # current default
            )
            recommendations["aspect_evaluator"]["axes_used"] = sorted(axis_metrics.keys())
            recommendations["aspect_evaluator"]["note"] = (
                f"Thresholds derived from {sum(m.sample_count for m in axis_metrics.values())} "
                f"dignity-pair observations across {len(axis_metrics)} axes."
            )
        else:
            # No dignity data available — report defaults clearly
            recommendations["aspect_evaluator"] = {
                "low_threshold":  -2.0,
                "high_threshold":  2.2,
                "note": "No dignity data in raw_pattern_occurrences — using hardcoded defaults. "
                        "Run a fuzzer pass to populate source_dignity / target_dignity fields.",
            }

        # ── Timing engine confidence thresholds ──────────────────────────────
        recommendations["timing_engine"] = {
            "rashi_phal_medium_threshold":  1.2,
            "rashi_phal_high_threshold":    2.0,
            "graha_phal_medium_threshold":  0.6,
            "graha_phal_high_threshold":    1.5,
            "note": "Configurable via model_defaults.json. Run a grid search to maximize per-domain F1.",
        }

        return recommendations

    # ------------------------------------------------------------------ #
    # Reporting                                                           #
    # ------------------------------------------------------------------ #

    def print_report(self, result: CalibrationResult) -> str:
        """Generate a human-readable calibration report."""
        lines = []
        lines.append("=" * 70)
        lines.append("CALIBRATION REPORT")
        lines.append(f"Baseline Macro-F1: {result.baseline_f1:.4f}")
        lines.append("=" * 70)

        lines.append("\n--- Per-Domain Metrics ---")
        for domain in sorted(result.domain_metrics.keys()):
            for fate_type, m in result.domain_metrics[domain].items():
                m_dict = m if isinstance(m, dict) else m.to_dict()
                lines.append(
                    f"  {domain:20s} | {fate_type:12s} | "
                    f"F1={m_dict['f1']:.3f} | P={m_dict['precision']:.3f} | "
                    f"R={m_dict['recall']:.3f} | "
                    f"TP={m_dict['tp']} FP={m_dict['fp']} "
                    f"FN={m_dict['fn']} TN={m_dict['tn']}"
                )

        if result.axis_metrics:
            lines.append("\n--- Per-Axis Metrics (dignity-pair empirical) ---")
            for axis in sorted(result.axis_metrics.keys()):
                am = result.axis_metrics[axis]
                am_dict = am if isinstance(am, dict) else am.to_dict()
                lines.append(
                    f"  {am_dict['axis']:10s} | "
                    f"P={am_dict['precision']:.3f} | "
                    f"TP={am_dict['tp']} FP={am_dict['fp']} "
                    f"(n={am_dict['sample_count']})"
                )
        else:
            lines.append("\n--- Per-Axis Metrics ---")
            lines.append("  [No dignity data] — run a fuzzer pass to populate source_dignity/target_dignity")

        lines.append("\n--- Recommended Threshold Changes ---")
        gate_recs = result.recommended_thresholds.get("fidelity_gate", {})
        if gate_recs:
            for key, rec in gate_recs.items():
                lines.append(
                    f"  {key}: {rec['action'].upper()} → "
                    f"base_mult={rec['suggested_base_multiplier']:.2f} "
                    f"(R={rec['current_recall']:.3f}, P={rec['current_precision']:.3f})"
                )
        else:
            lines.append("  No threshold changes recommended.")

        ae_rec = result.recommended_thresholds.get("aspect_evaluator", {})
        if ae_rec:
            lines.append("\n--- AspectFidelityEvaluator Thresholds ---")
            lines.append(f"  LOW_THRESHOLD : {ae_rec.get('low_threshold', -2.0)}")
            lines.append(f"  HIGH_THRESHOLD: {ae_rec.get('high_threshold', 2.2)}")
            lines.append(f"  Note: {ae_rec.get('note', '')}")

        return "\n".join(lines)


# ------------------------------------------------------------------ #
# CLI Entry Point                                                     #
# ------------------------------------------------------------------ #

def run_calibration(db_path: Optional[str] = None, print_report: bool = True) -> CalibrationResult:
    """
    Convenience function to run calibration from scripts or CLI.

    Parameters
    ----------
    db_path : str | None
        Path to public_figures.db. If None, uses the default path.
    print_report : bool
        If True, prints the calibration report to stdout.
    """
    if db_path is None:
        db_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "data", "public_figures.db"
        )
    db_path = os.path.abspath(db_path)

    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found: {db_path}")

    calibrator = CalibrationModule(db_path)
    result = calibrator.calibrate()

    if print_report:
        print(calibrator.print_report(result))

    return result


if __name__ == "__main__":
    run_calibration()
