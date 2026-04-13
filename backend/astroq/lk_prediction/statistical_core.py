import numpy as np
from typing import List, Dict, Any

def fuse_beliefs(beliefs: List[Dict[str, float]]) -> Dict[str, float]:
    """
    Dempster-Shafer Combination Rule to fuse multiple belief states.
    Each belief dict should have 'pro', 'con', and 'uncertain'.
    """
    if not beliefs:
        return {"pro": 0.0, "con": 0.0, "uncertain": 1.0}
    
    # Start with the first belief
    m1 = beliefs[0]
    
    for i in range(1, len(beliefs)):
        m2 = beliefs[i]
        
        # Calculate conflict K
        # Conflict exists between (pro1, con2) and (con1, pro2)
        k = m1["pro"] * m2["con"] + m1["con"] * m2["pro"]
        
        if k >= 1:
            # Absolute conflict, return maximum uncertainty or handle error
            return {"pro": 0.0, "con": 0.0, "uncertain": 1.0}
        
        normalization = 1 - k
        
        # Calculate new mass
        pro = (m1["pro"] * m2["pro"] + m1["pro"] * m2["uncertain"] + m1["uncertain"] * m2["pro"]) / normalization
        con = (m1["con"] * m2["con"] + m1["con"] * m2["uncertain"] + m1["uncertain"] * m2["con"]) / normalization
        uncertain = (m1["uncertain"] * m2["uncertain"]) / normalization
        
        m1 = {"pro": min(1.0, pro), "con": min(1.0, con), "uncertain": max(0.0, uncertain)}
        
    return m1

def aggregate_fuzzy_scores(scores: List[float]) -> float:
    """
    Fuzzy Aggregation using a weighted Power Mean.
    Bias towards higher scores to capture 'peak' activation.
    """
    if not scores:
        return 0.0
    
    # Convert to numpy array
    arr = np.array(scores)
    
    # Use Generalized Mean (p=2 for Quadratic Mean, which favors higher values)
    # This acts as a fuzzy 'OR-like' aggregation
    agg_score = np.sqrt(np.mean(np.square(arr)))
    
    # Normalize to 0-1 range (assuming input was 0-100 or 0-1)
    if np.max(arr) > 1.0:
        agg_score /= 100.0
        
    return float(np.clip(agg_score, 0.0, 1.0))

def apply_bayesian_prior(probability: float, prior_weight: float) -> float:
    """
    Simple Bayesian update to adjust a baseline probability using Chart DNA weight.
    """
    # Posterior = (Prior * Likelihood) / Evidence
    # Simplified version for single-pass agent logic:
    return float(np.clip(probability * prior_weight, 0.0, 1.0))
