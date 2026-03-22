"""
Module 7: Prediction Translator.

Translates internal `ClassifiedEvent` objects into human-readable
`LKPrediction` records. Maps probabilities to confidence levels,
resolves affected people and items from astrological karakas, and
provides remedy hints for malefic events.
"""

from __future__ import annotations

from typing import Any
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.data_contracts import ClassifiedEvent, LKPrediction


# Simple Karaka Mappings for People and Items (abridged for translation)
PEOPLE_MAP = {
    "Sun": ["Self", "Father", "Authority Figures"],
    "Moon": ["Mother", "Women", "Public"],
    "Mars": ["Brothers", "Friends", "Enemies"],
    "Mercury": ["Sisters", "Daughters", "Business Partners"],
    "Jupiter": ["Father", "Guru", "Children", "Elders"],
    "Venus": ["Wife", "Spouse", "Women"],
    "Saturn": ["Uncles", "Subordinates", "Elderly"],
    "Rahu": ["In-laws", "Paternal Grandfather", "Strangers"],
    "Ketu": ["Sons", "Maternal Grandfather", "Dogs"],
    
    # Houses
    "h3": ["Younger Siblings"],
    "h4": ["Mother"],
    "h5": ["Children"],
    "h7": ["Spouse", "Partners"],
    "h9": ["Father", "Guru"],
    "h11": ["Elder Siblings"]
}

ITEMS_MAP = {
    "Sun": ["Government", "Gold", "Wheat"],
    "Moon": ["Water", "Silver", "Rice", "Milk"],
    "Mars": ["Property", "Weapons", "Blood", "Land"],
    "Mercury": ["Business", "Green items", "Books"],
    "Jupiter": ["Gold", "Yellow items", "Education", "Wealth"],
    "Venus": ["Luxury", "Vehicles", "Cosmetics", "Clothes"],
    "Saturn": ["Iron", "Machinery", "Oil", "Shoes"],
    "Rahu": ["Electronics", "Foreign goods", "Old currency"],
    "Ketu": ["Flags", "Dogs", "Black/White blankets"],
    
    # Houses
    "h2": ["Wealth", "Bank Balance"],
    "h4": ["Property", "Vehicles", "Home"],
    "h6": ["Debts", "Diseases"],
    "h8": ["Hidden Wealth", "Obstacles"],
    "h10": ["Career", "Status"],
    "h12": ["Expenses", "Hospitals", "Foreign Lands"]
}


class PredictionTranslator:
    """Translates classified events into final LKPrediction outputs."""

    def __init__(self, config: ModelConfig, remedy_engine: Any | None = None) -> None:
        self._cfg = config
        self.remedy_engine = remedy_engine
        self.cert_thresh = config.get("translation.certain_threshold", fallback=0.85)
        self.high_thresh = config.get("translation.highly_likely_threshold", fallback=0.65)
        self.poss_thresh = config.get("translation.possible_threshold", fallback=0.40)

    def translate(
        self,
        events: list[ClassifiedEvent],
        enriched_natal: dict | None = None,
        enriched_annual: dict | None = None,
    ) -> list[LKPrediction]:
        """Convert a list of ClassifiedEvents into LKPredictions."""
        predictions = []
        for ev in events:
            # Domain string
            domain = ev.domains[0] if ev.domains else "General"
            
            # Sub-type
            event_type = f"{ev.planet}_{ev.sentiment.lower()}"
            
            # Text
            text = self._generate_text(ev)
            
            # Details
            confidence = self._map_confidence(ev.probability)
            people = self._resolve_affected_people(ev)
            items = self._resolve_affected_items(ev)
            remedy_needed, hints = self._generate_remedies(ev, enriched_natal, enriched_annual)
            
            p = LKPrediction(
                domain=domain,
                event_type=event_type,
                prediction_text=text,
                confidence=confidence,
                polarity=ev.sentiment,
                peak_age=ev.peak_age,
                age_window=ev.age_window,
                probability=ev.probability,
                affected_people=people,
                affected_items=items,
                source_planets=[ev.planet] + ev.source_planets,
                source_houses=[ev.house] + ev.source_houses,
                source_rules=ev.contributing_rules,
                remedy_applicable=remedy_needed,
                remedy_hints=hints
            )
            predictions.append(p)
            
        return predictions

    def _map_confidence(self, prob: float) -> str:
        """Map raw probability to human-readable confidence."""
        if prob >= self.cert_thresh:
            return "CERTAIN"
        if prob >= self.high_thresh:
            return "HIGHLY_LIKELY"
        if prob >= self.poss_thresh:
            return "POSSIBLE"
        return "UNLIKELY"

    def _resolve_affected_people(self, ev: ClassifiedEvent) -> list[str]:
        """Determine affected people based on karakas."""
        people = set()
        if ev.planet in PEOPLE_MAP:
            people.update(PEOPLE_MAP[ev.planet])
        
        h_key = f"h{ev.house}"
        if h_key in PEOPLE_MAP:
            people.update(PEOPLE_MAP[h_key])
            
        return sorted(list(people))

    def _resolve_affected_items(self, ev: ClassifiedEvent) -> list[str]:
        """Determine affected items based on karakas."""
        items = set()
        if ev.planet in ITEMS_MAP:
            items.update(ITEMS_MAP[ev.planet])
            
        h_key = f"h{ev.house}"
        if h_key in ITEMS_MAP:
            items.update(ITEMS_MAP[h_key])
            
        return sorted(list(items))

    def _generate_remedies(
        self,
        ev: ClassifiedEvent,
        natal: dict | None,
        annual: dict | None,
    ) -> tuple[bool, list[str]]:
        """If malefic or volatile, generate remedy hints."""
        # Use RemedyEngine if provided
        if self.remedy_engine and natal and annual:
            year_options = self.remedy_engine.get_year_shifting_options(
                birth_chart=natal,
                annual_chart=annual,
                age=ev.peak_age,
            )
            p_result = year_options.get(ev.planet)
            if p_result and p_result.safe_matches:
                hints = self.remedy_engine.generate_remedy_hints({ev.planet: p_result})
                return True, hints
            return False, []

        # Fallback if no engine
        if ev.sentiment in ("MALEFIC", "VOLATILE"):
            hints = [
                f"Lal Kitab remedy required for {ev.planet}",
                f"Check condition of House {ev.house}",
                "Feed animals associated with planet"
            ]
            return True, hints
        return False, []

    def _generate_text(self, ev: ClassifiedEvent) -> str:
        """Construct the final prediction text."""
        if ev.prediction_text:
            return ev.prediction_text
            
        # Fallback generation
        pol = "positive" if ev.sentiment == "BENEFIC" else "challenging" if ev.sentiment == "MALEFIC" else "mixed"
        domain_str = ", ".join(ev.domains) if ev.domains else "General life"
        
        return f"The placement of {ev.planet} in House {ev.house} creates a {pol} effect concerning {domain_str}."
