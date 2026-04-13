import pytest
import numpy as np
from typing import List, Dict

def test_dst_fusion_resolves_conflict():
    from astroq.lk_prediction.statistical_core import fuse_beliefs
    
    # Simulate two conflicting rules for the same domain
    # Rule 1: High belief in positive (marriage)
    # Rule 2: Low belief in negative (divorce)
    beliefs = [
        {"pro": 0.8, "con": 0.1, "uncertain": 0.1},
        {"pro": 0.2, "con": 0.7, "uncertain": 0.1}
    ]
    
    result = fuse_beliefs(beliefs)
    
    # Combined belief should be narrowed
    assert result["pro"] > 0
    assert result["con"] > 0
    assert result["uncertain"] < 0.1

def test_fuzzy_aggregation():
    from astroq.lk_prediction.statistical_core import aggregate_fuzzy_scores
    
    # Simulate multiple aspect strengths contributing to a domain score
    aspect_strengths = [80.0, 40.0, 10.0]
    
    final_score = aggregate_fuzzy_scores(aspect_strengths)
    
    # Should be a normalized 0.0-1.0 score
    assert 0.0 <= final_score <= 1.0
    assert final_score > 0.4 # Significant strength present
