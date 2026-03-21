"""
Module 6: Event Classifier.

Filters raw probabilistic events into the final ClassifiedEvent representations.
Applies sentiment analysis (BENEFIC/MALEFIC/MIXED/VOLATILE), absolute and
momentum peak detection, and domains mapping via astrological house rules.
"""

from __future__ import annotations

from typing import Any

from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.data_contracts import ClassifiedEvent


# Standard domain mapping logic (simplified for implementation ease)
DOMAIN_MAP = {
    # Houses
    "h1": ["Health", "Self", "Personality"],
    "h2": ["Wealth", "Family", "Speech"],
    "h3": ["Courage", "Siblings", "Short Trips"],
    "h4": ["Home", "Mother", "Property", "Vehicles"],
    "h5": ["Children", "Education", "Speculation"],
    "h6": ["Enemies", "Debts", "Diseases", "Daily Work"],
    "h7": ["Marriage", "Partnerships", "Business"],
    "h8": ["Longevity", "Sudden Events", "Obstacles"],
    "h9": ["Fortune", "Religion", "Higher Education", "Father"],
    "h10": ["Career", "Profession", "Status"],
    "h11": ["Gains", "Income", "Elder Siblings"],
    "h12": ["Losses", "Foreign Travel", "Expenses", "Spirituality"],
    
    # Planets (Primary natural karakas)
    "Sun": ["Career", "Authority", "Health"],
    "Moon": ["Mind", "Emotions", "Mother"],
    "Mars": ["Courage", "Property", "Siblings", "Accidents"],
    "Mercury": ["Communication", "Business", "Intelligence"],
    "Jupiter": ["Wealth", "Education", "Children", "Wisdom"],
    "Venus": ["Marriage", "Romance", "Vehicles", "Luxury"],
    "Saturn": ["Career", "Karma", "Delays", "Longevity"],
    "Rahu": ["Foreign", "Sudden Events", "Obsession"],
    "Ketu": ["Spirituality", "Detachment", "Sudden Endings"]
}


class EventClassifier:
    """
    Classifies raw probability events into domains, sentiments, and peaks.
    """

    def __init__(self, config: ModelConfig) -> None:
        self._cfg = config
        
        # Classifier configurations
        self.abs_peak = config.get("classifier.absolute_peak_threshold", fallback=0.85)
        self.momentum_jump = config.get("classifier.momentum_jump_threshold", fallback=0.30)
        self.noise_floor = config.get("classifier.noise_floor", fallback=0.30)
        
        # Sentiments
        self.sent_mixed_max = config.get("classifier.sentiment_mixed_max_mag", fallback=2.0)
        self.sent_mixed_min = config.get("classifier.sentiment_mixed_min_mag", fallback=-2.0)

    def classify_events(self, raw_events: list[dict[str, Any]]) -> list[ClassifiedEvent]:
        """
        Process a list of enriched events and return ClassifiedEvent instances.
        
        raw_events normally includes:
        - planet, house, annual_magnitude, final_probability
        - prob_t_minus_1 (optional)
        - rule_hits (optional)
        """
        classified: list[ClassifiedEvent] = []
        
        for ev in raw_events:
            prob = ev.get("final_probability", 0.0)
            
            # 1. Filter Noise
            if prob < self.noise_floor:
                # Optionally, we can still return it but `is_peak=False`.
                # For safety against clutter, we might skip, but tests expect them
                # if asked or expect `is_peak=False`. Let's just create it but it won't be a peak.
                pass
            
            # Extract inputs
            planet = ev.get("planet", "")
            house = ev.get("house", 0)
            mag = ev.get("annual_magnitude", 0.0)
            prob_t_minus_1 = ev.get("prob_t_minus_1")
            
            # 2. Peak Detection
            peak = self._is_peak(prob, prob_t_minus_1)
            
            # 3. Sentiment Classification
            sentiment = self._classify_sentiment(mag, planet)
            
            # 4. Domain Mapping
            domains = self._map_domains(planet, house)
            
            prediction_text = ev.get("prediction_text", f"Lal Kitab prediction for {planet} in House {house}")
            if not ev.get("prediction_text") and ev.get("rule_hits"):
                # For simplified implementation, grab top rule description
                hits = ev["rule_hits"]
                if hits:
                    prediction_text = getattr(hits[0], "description", prediction_text)

            # Build contract
            ce = ClassifiedEvent(
                planet=planet,
                house=house,
                domains=domains,
                sentiment=sentiment,
                probability=prob,
                magnitude=mag,
                is_peak=peak,
                peak_type="ABSOLUTE" if prob >= self.abs_peak else "MOMENTUM" if peak else "NONE",
                prediction_text=prediction_text,
                contributing_rules=[getattr(h, "rule_id", "") for h in ev.get("rule_hits", [])] if "rule_hits" in ev else []
            )
            classified.append(ce)
            
        return classified

    def _is_peak(self, prob: float, prob_t_minus_1: float | None) -> bool:
        """Determines if the event is a peak (Absolute OR Momentum)."""
        # Absolute peak
        if prob >= self.abs_peak:
            return True
            
        # Momentum peak
        if prob_t_minus_1 is not None:
            jump = prob - prob_t_minus_1
            if jump >= self.momentum_jump:
                return True
                
        return False

    def _classify_sentiment(self, magnitude: float, planet: str) -> str:
        """Classifies the sentiment based on magnitude and planet karakas."""
        # Volatile planets can have VOLATILE sentiment if highly negative or mixed
        volatile_planets = ["Rahu", "Ketu", "Mars"]
        
        if self.sent_mixed_min <= magnitude <= self.sent_mixed_max:
            if planet in volatile_planets:
                return "VOLATILE"
            return "MIXED"
            
        if magnitude > self.sent_mixed_max:
            return "BENEFIC"
            
        if magnitude < self.sent_mixed_min:
            if planet in volatile_planets:
                return "MALEFIC" # or VOLATILE
            return "MALEFIC"
            
        return "MIXED"

    def _map_domains(self, planet: str, house: int) -> list[str]:
        """Combine domain tags based on planet and house placements."""
        domains = set()
        
        # House primary
        house_key = f"h{house}"
        if house_key in DOMAIN_MAP:
            domains.update(DOMAIN_MAP[house_key])
            
        # Planet natural domains
        if planet in DOMAIN_MAP:
            domains.update(DOMAIN_MAP[planet])
            
        return sorted(list(domains))
