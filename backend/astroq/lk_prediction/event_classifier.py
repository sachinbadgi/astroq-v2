"""
Module 6: Event Classifier.

Filters raw probabilistic events into the final ClassifiedEvent representations.
Applies sentiment analysis (BENEFIC/MALEFIC/MIXED/VOLATILE), absolute and
momentum peak detection, and domains mapping via astrological house rules.
"""

from __future__ import annotations

import copy
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

    def classify_events(self, raw_events: list[dict[str, Any]], age: int = 0) -> list[ClassifiedEvent]:
        """
        Process a list of enriched events and return ClassifiedEvent instances.
        
        raw_events normally includes:
        - planet, house, annual_magnitude, final_probability
        - prob_t_minus_1 (optional)
        - rule_hits (optional)
        """
        raw_classified: list[ClassifiedEvent] = []
        
        for ev in raw_events:
            prob = ev.get("final_probability", 0.0)
            
            # Extract inputs
            planet = ev.get("planet", "")
            house = ev.get("house", 0)
            mag = ev.get("annual_magnitude", 0.0)
            prob_t_minus_1 = ev.get("prob_t_minus_1")
            
            # 1. Peak Detection
            peak = self._is_peak(prob, prob_t_minus_1)
            
            # 2. Sentiment Classification
            sentiment = self._classify_sentiment(mag, planet)
            
            # 3. Domain Mapping
            rule_hits = ev.get("rule_hits", [])
            rule_domains = set()
            for h in rule_hits:
                rd = getattr(h, "domain", "")
                if rd:
                    parts = [p.strip().lower() for p in rd.split(",") if p.strip()]
                    rule_domains.update(parts)
            
            domains = self._map_domains(planet, house, list(rule_domains))
            
            prediction_text = ev.get("prediction_text", f"Lal Kitab prediction for {planet} in House {house}")
            if not ev.get("prediction_text") and rule_hits:
                prediction_text = getattr(rule_hits[0], "description", prediction_text)

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
                contributing_rules=[getattr(h, "description", h.rule_id) for h in rule_hits],
                peak_age=age,
                source_planets=[planet],
                source_houses=[house]
            )
            raw_classified.append(ce)
            
        # 4. Domain Collapsing (Reduction of False Positives)
        # Groups all events for a domain in this year and picks the strongest signal.
        domain_peaks: dict[str, ClassifiedEvent] = {}
        
        for ce in raw_classified:
            for d in ce.domains:
                if d not in domain_peaks:
                    # Deep copy of the CE for this domain bucket
                    peak_ce = copy.copy(ce)
                    peak_ce.domains = [d] # Single domain for this bucket
                    domain_peaks[d] = peak_ce
                else:
                    existing = domain_peaks[d]
                    # Update peak if this signal is stronger
                    if abs(ce.magnitude) > abs(existing.magnitude):
                        existing.magnitude = ce.magnitude
                        existing.probability = ce.probability
                        existing.is_peak = existing.is_peak or ce.is_peak
                        existing.peak_type = ce.peak_type if ce.is_peak else existing.peak_type
                        existing.planet = ce.planet
                        existing.house = ce.house
                        existing.prediction_text = ce.prediction_text
                    
                    # Merge traceability info
                    for r in ce.contributing_rules:
                        if r not in existing.contributing_rules:
                            existing.contributing_rules.append(r)
                    for p in ce.source_planets:
                        if p not in existing.source_planets:
                            existing.source_planets.append(p)
                    for h in ce.source_houses:
                        if h not in existing.source_houses:
                            existing.source_houses.append(h)

        return list(domain_peaks.values())

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

    def _map_domains(self, planet: str, house: int, rule_domains: list[str] | None = None) -> list[str]:
        """Combine domain tags based on planet and house placements, prioritizing rule domains.
        """
        # 1. If explicit rule domains exist, use them exclusively to reduce noise
        if rule_domains:
            mapped = set()
            for rd in rule_domains:
                # Standardize common labels to the audit map
                rd_l = rd.lower()
                if rd_l == "profession":
                    mapped.update(["Career", "Profession", "Status"])
                elif rd_l == "health":
                    mapped.add("Health")
                elif rd_l == "marriage":
                    mapped.update(["Marriage", "Partnerships"])
                elif rd_l == "progeny":
                    mapped.update(["Children", "Progeny"])
                elif rd_l == "wealth":
                    mapped.update(["Wealth", "Gains", "Income"])
                elif rd_l == "foreign_travel":
                    mapped.update(["Foreign Travel", "Expenses", "Losses"])
                elif rd_l in ["general", "none", ""]:
                    mapped.add("General")
                else:
                    mapped.add(rd.title())
            return sorted(list(mapped))

        # 2. No explicit rule domains – fall back to planet/house mapping using DOMAIN_MAP
        domains = set()
        # Planet based mapping
        planet_key = planet
        if planet_key in DOMAIN_MAP:
            domains.update(DOMAIN_MAP[planet_key])
        # House based mapping (e.g., "h10")
        house_key = f"h{house}"
        if house_key in DOMAIN_MAP:
            domains.update(DOMAIN_MAP[house_key])
        # If still empty, default to General
        if not domains:
            domains.add("General")
        return sorted(list(domains))
