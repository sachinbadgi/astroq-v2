"""
pipeline.py — Backward-compatibility shim.

LKPredictionPipeline has been merged into PredictionRunner.
This module re-exports PredictionRunner as LKPredictionPipeline so that
all existing callers (scripts, tests, API server) continue to work without
modification.

New code should import PredictionRunner directly:
    from astroq.lk_prediction.prediction_runner import PredictionRunner
"""
from .prediction_runner import PredictionRunner as LKPredictionPipeline

__all__ = ["LKPredictionPipeline"]
