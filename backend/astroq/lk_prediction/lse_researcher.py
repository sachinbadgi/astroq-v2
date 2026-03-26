"""
Phase 3 (Enhanced): Researcher Agent (AutoResearch 2.0)

Generates hypotheses based on gaps between predictions and life events,
validated by specific Lal Kitab astrological rationale rules.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Any, TypedDict, Optional, List

from astroq.lk_prediction.rules_engine import RulesEngine
from astroq.lk_prediction.config import ModelConfig

if TYPE_CHECKING:
    from astroq.lk_prediction.data_contracts import ChartData, GapReport, RuleHit, GapEntry


class Hypothesis(TypedDict):
    """A proposed change to the chart DNA."""
    type: str           # "Delay", "Grammar", "Boost"
    key: str            # Config key to override
    value: Any          # Override value
    rationale: str      # Why this hypothesis was generated


# ---------------------------------------------------------------------------
# Lal Kitab Canonical Constants
# ---------------------------------------------------------------------------

PLANET_EFFECTIVE_AGES = {
    "Jupiter": 16,
    "Sun": 22,
    "Moon": 24,
    "Venus": 25,
    "Mars": 28,
    "Mercury": 34,
    "Saturn": 36,
    "Rahu": 42,
    "Ketu": 48
}


class Rationale(TypedDict):
    """Astrological justification for a gap."""
    condition_name: str
    logic: str
    suggested_offset: float
    target_planet: Optional[str]
    target_house: Optional[int]


class ResearcherAgent:
    """
    Hypothesis generation engine.
    Analyses GapReport and ChartData to propose model corrections.
    """

    def __init__(self, config: Optional[ModelConfig] = None):
        if config:
            self.rules_engine = RulesEngine(config)
        else:
            self.rules_engine = None

    def extract_applicable_rules(self, birth_chart: ChartData) -> list[RuleHit]:
        """Runs RulesEngine on natal chart to see what potential rules exist."""
        if not self.rules_engine: return []
        return self.rules_engine.evaluate_chart(birth_chart)

    def find_astrological_rationale(self, gap: GapEntry, birth_chart: ChartData) -> Optional[Rationale]:
        """
        Check for specific Lal Kitab conditions that explain the gap.
        Calculates suggested_offset based on Effective Ages vs Actual Life Events.
        """
        actual_age = gap["life_event"]["age"]
        pred_age = gap["predicted_peak_age"]
        if pred_age is None: return None
        
        offset = actual_age - pred_age
        domain = gap["life_event"]["domain"].lower()
        planets = birth_chart.get("planets_in_houses", {})
        source_planets = gap.get("source_planets", [])
        
        # Initialize planet lookups
        sun = planets.get("Sun", {})
        mars = planets.get("Mars", {})
        sat = planets.get("Saturn", {})
        jup = planets.get("Jupiter", {})
        rah = planets.get("Rahu", {})
        ven = planets.get("Venus", {})
        mer = planets.get("Mercury", {})
        
        # 1. Mars H8 vs Sun H1 (Ruthless Clash)
        if sun.get("house") == 1 and mars.get("house") == 8:
            if domain in ["profession", "career", "health"] and ("Sun" in source_planets or not source_planets):
                # Logic: Destiny is challenged by the 8th house clash.
                return {
                    "condition_name": "Mars H8 vs Sun H1 (Ruthless Clash)",
                    "logic": "1st house (Sun) confronts 8th house (Mars) ruthlessly. Results may be delayed or destroyed until the clash resolves.",
                    "suggested_offset": offset, # Discover the actual gap relative to effective age
                    "target_planet": "Sun",
                    "target_house": 1
                }

        # 2. Soya Ghar (Sleeping House) - H10 sleep
        # Rule: A house without planet/aspect is dormant. Saturn awakens H10.
        if domain in ["profession", "career"]:
            house_status = birth_chart.get("house_status", {})
            if house_status.get("10") == "Sleeping House":
                if sat.get("house") in [8, 12] and ("Saturn" in source_planets or not source_planets):
                    # Lord Saturn is malefic/weak, delaying H10 awakening.
                    # Canonical benchmark: Saturn effective age 36.
                    return {
                        "condition_name": "Dormant H10 (Soya Ghar)",
                        "logic": "H10 is dormant. Lord Saturn in 8/12 delays the 'awakening' of career results.",
                        "suggested_offset": offset,
                        "target_planet": "Saturn",
                        "target_house": 10
                    }

        # 4. Venus in H10 (Imaginary Saturn)
        # Rule: native is amative/greedy; results delayed or damaged.
        if ven.get("house") == 10:
            if domain == "marriage" and ("Venus" in source_planets or not source_planets):
                return {
                    "condition_name": "Venus in H10 (Imaginary Saturn)",
                    "logic": "Venus acts as an 'Imaginary Saturn', making the native prone to suspicion and hankering, delaying domestic stability.",
                    "suggested_offset": offset,
                    "target_planet": "Venus",
                    "target_house": 10
                }

        # 5. Mercury in H9 (Highly Malefic till 34)
        if mer.get("house") == 9:
            if domain in ["marriage", "family"] and ("Mercury" in source_planets or not source_planets):
                # Rule: Malefic specifically until age 34.
                return {
                    "condition_name": "Mercury in H9 (Malefic till 34)",
                    "logic": "Mercury in H9 is highly malefic, destroying comforts and luck until the age of 34.",
                    "suggested_offset": offset,
                    "target_planet": "Mercury",
                    "target_house": 9
                }

        # 6. Saturn in H4 (Snake in Water)
        # Rule: Property at age 36. Impact on family sickness.
        if sat.get("house") == 4:
            if domain in ["health", "property"] and ("Saturn" in source_planets or not source_planets):
                return {
                    "condition_name": "Saturn in H4 (Snake in Water)",
                    "logic": "Acts like a 'snake in water' devouring family comforts; property manifests specifically around age 36.",
                    "suggested_offset": offset,
                    "target_planet": "Saturn",
                    "target_house": 4
                }

        # 7. Mercury in H12 (Speech/Isolation)
        if mer.get("house") == 12:
            if domain in ["health", "career"] and ("Mercury" in source_planets or not source_planets):
                # Rule: "Poisonous speech" or stammering; isolation.
                return {
                    "condition_name": "Mercury in H12 (Speech/Isolation)",
                    "logic": "Mercury in H12 can cause speech hurdles, nervous issues, or isolation until its maturation at 34.",
                    "suggested_offset": offset,
                    "target_planet": "Mercury",
                    "target_house": 12
                }

        # 8. Saturn in H10 (Up/Down Volatility)
        if sat.get("house") == 10:
            if domain in ["career", "profession"] and ("Saturn" in source_planets or not source_planets):
                # Rule: native is a "King-maker", but can fall suddenly if they deceive.
                return {
                    "condition_name": "Saturn in H10 (Up/Down Volatility)",
                    "logic": "Saturn in H10 gives high peaks but also sudden drops or ousting from power.",
                    "suggested_offset": offset,
                    "target_planet": "Saturn",
                    "target_house": 10
                }

        # 9. Sun in H8 (Hidden Glory/Danger)
        if sun.get("house") == 8:
            if domain in ["health", "career"] and ("Sun" in source_planets or not source_planets):
                # Rule: "Sun of the cemetery"; danger to life or hidden peak.
                return {
                    "condition_name": "Sun in H8 (Hidden Glory/Danger)",
                    "logic": "Sun in H8 brings results through struggles or near-death experiences, often quite late.",
                    "suggested_offset": offset,
                    "target_planet": "Sun",
                    "target_house": 8
                }

        # 10. Sun in H2 (Kingdom/Wealth)
        if sun.get("house") == 2:
            if domain in ["career", "profession"] and ("Sun" in source_planets or not source_planets):
                # Rule: "King of the house"; brings status and wealth.
                return {
                    "condition_name": "Sun in H2 (Kingdom/Wealth)",
                    "logic": "Sun in H2 bestows status and a 'kingdom' like authority, typically maturing at age 22.",
                    "suggested_offset": offset,
                    "target_planet": "Sun",
                    "target_house": 2
                }

        # 11. Mercury in H1 (Royal/Kingship)
        if mer.get("house") == 1:
            if domain in ["career", "profession"] and ("Mercury" in source_planets or not source_planets):
                # Rule: native is intelligent like a king.
                return {
                    "condition_name": "Mercury in H1 (Royal/Kingship)",
                    "logic": "Mercury in H1 brings status and royal-like intelligence, maturing at age 34.",
                    "suggested_offset": offset,
                    "target_planet": "Mercury",
                    "target_house": 1
                }

        # 12. Takrav (Confrontation) - Sun H1 vs Saturn H7
        if sun.get("house") == 1 and sat.get("house") == 7:
            if domain in ["career", "profession", "health"] and ("Sun" in source_planets or not source_planets):
                # Rule: Mutual aspect between Sun/Saturn delays Sun's peak.
                # Canonical Takrav offset is 4.5 if not specifically calculated.
                suggested = 4.5 if abs(offset - 4.5) < 0.6 else offset
                return {
                    "condition_name": "Takrav (Sun H1 vs Saturn H7)",
                    "logic": "Sun in H1 is confronted by Saturn in H7, causing constant struggle and delaying the 'throne' results by approx 4.5 years.",
                    "suggested_offset": suggested,
                    "target_planet": "Sun",
                    "target_house": 1
                }

        # 13. Sun in H1 (Throne/Presidency)
        if sun.get("house") == 1:
            if domain in ["career", "profession", "health"] and ("Sun" in source_planets or not source_planets):
                # Rule: "King on the throne"; highest status, but also self-physical vitality.
                return {
                    "condition_name": "Sun in H1 (Throne/Presidency)",
                    "logic": "Sun in H1 gives peak career status and authority, and governs physical health, maturing at age 22.",
                    "suggested_offset": offset,
                    "target_planet": "Sun",
                    "target_house": 1
                }

        # 17. Guru-Chandal (Jupiter + Rahu/Ketu)
        nodes_houses = [rah.get("house"), planets.get("Ketu", {}).get("house")]
        if jup.get("house") in nodes_houses and jup.get("house") != 0:
            if domain in ["wealth", "fortune", "career", "profession"] and ("Jupiter" in source_planets or not source_planets):
                # Rule: Destiny becomes dual/smoke. 
                # Use "Guru-Chandal" name consistently for tests. 
                return {
                    "condition_name": "Guru-Chandal",
                    "logic": "Jupiter is eclipsed by Rahu or Ketu, making fortune dual and results delayed by a full planetary cycle (avg 5-6 years).",
                    "suggested_offset": offset,
                    "target_planet": "Jupiter",
                    "target_house": jup.get("house")
                }

        # 18. Saturn Lord of 10 in 8 or 12
        if sat.get("house") in [8, 12] and birth_chart.get("house_status", {}).get("10") == "Occupied":
            if domain in ["career", "profession"] and ("Saturn" in source_planets or not source_planets):
                # Rule: Lord of Karma in the house of death/loss.
                return {
                    "condition_name": "Malefic Saturn (Lord 10 in 8/12)",
                    "logic": "Karma Lord is in 8 or 12, causing professional results to manifest only after intense labor or significant delay (avg 6 years).",
                    "suggested_offset": offset,
                    "target_planet": "Saturn",
                    "target_house": 10
                }

        return None

    def generate_hypotheses(
        self, gap_report: GapReport, birth_chart: ChartData
    ) -> list[Hypothesis]:
        """
        Produce a list of hypotheses to close the gaps in the report,
        only if an astrological rationale is found.
        """
        hypotheses: list[Hypothesis] = []
        
        # 1. Address Misses (Timing offsets) with Rationale
        for entry in gap_report.get("entries", []):
            if not entry["is_hit"]:
                rationale = self.find_astrological_rationale(entry, birth_chart)
                if rationale:
                    planet = rationale["target_planet"]
                    house = rationale["target_house"]
                    key = f"delay.{planet.lower()}_h{house}"
                    
                    hypotheses.append({
                        "type": "Delay",
                        "key": key,
                        "value": float(rationale["suggested_offset"]),
                        "rationale": f"{rationale['condition_name']}: {rationale['logic']}"
                    })

        # 2. Address Contradictions (Events with no predictions) -> Use Grammar rationale
        for domain in gap_report.get("contradictions", []):
            if domain == "profession":
                house_status = birth_chart.get("house_status", {})
                if house_status.get("10") == "Sleeping House":
                    hypotheses.append({
                        "type": "Grammar",
                        "key": "grammar.h10_sleep_cancelled",
                        "value": True,
                        "rationale": "Soya Ghar logic: H10 career rules are blocked; hypothesizing cancellation due to unrecorded travel/H12."
                    })

        return hypotheses

    def rank_hypotheses(self, hypotheses: list[Hypothesis]) -> list[Hypothesis]:
        """
        Simple ranking: Delay constants first, then Grammar.
        """
        return sorted(hypotheses, key=lambda h: (h["type"] != "Delay", h["type"] != "Grammar"))
