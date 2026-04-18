import numpy as np
from typing import List, Dict, Any


class DempsterShaferAggregator:
    """
    Implements Dempster-Shafer Theory (DST) for combining conflicting evidence.
    Refines scores from 'Simple Addition' to 'Weight of Evidence'.
    Moved here from pipeline.py — this is a standalone statistical component.
    """

    def __init__(self, uncertainty_base: float = 0.5):
        self.m_pos = 0.0
        self.m_neg = 0.0
        self.m_unc = 1.0  # Initial state is total uncertainty

    def add_evidence(self, magnitude: float, scoring_type: str) -> None:
        """
        magnitude (0 to 1): The strength of the rule hit.
        scoring_type: 'boost' (positive) or 'penalty' (negative).
        """
        mag = min(0.9, magnitude)  # Cap to avoid total certainty from a single rule
        if scoring_type == "boost":
            m_p, m_n, m_u = mag, 0.0, 1.0 - mag
        else:
            m_p, m_n, m_u = 0.0, mag, 1.0 - mag

        k = self.m_pos * m_n + self.m_neg * m_p
        if k >= 1.0:  # Total conflict — abort combination
            return

        denom = 1.0 - k
        self.m_pos = min(0.99, (self.m_pos * m_p + self.m_pos * m_u + self.m_unc * m_p) / denom)
        self.m_neg = min(0.99, (self.m_neg * m_n + self.m_neg * m_u + self.m_unc * m_n) / denom)
        self.m_unc = 1.0 - (self.m_pos + self.m_neg)

    def get_metrics(self) -> dict:
        """Returns Belief, Plausibility and Uncertainty."""
        belief = self.m_pos
        plausibility = 1.0 - self.m_neg
        return {
            "belief": round(belief, 3),
            "plausibility": round(plausibility, 3),
            "uncertainty": round(plausibility - belief, 3),
        }

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
