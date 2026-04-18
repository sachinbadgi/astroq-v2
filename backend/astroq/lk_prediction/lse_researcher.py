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
    type: str           # "Delay", "Grammar", "Boost", "Alignment"
    key: str            # Config key to override
    value: Any          # Override value (offset or target_age)
    rationale: str      # Why this hypothesis was generated
    target_age: Optional[int] # NEW: For alignment milestones


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

# ---------------------------------------------------------------------------
# Domain → Lal Kitab House Mapping
# Used to route contradiction hypotheses through canonical house placements.
# ---------------------------------------------------------------------------

DOMAIN_HOUSE_MAP: dict[str, dict[str, list[int]]] = {
    "career":       {"primary": [10], "secondary": [6, 2]},
    "profession":   {"primary": [10], "secondary": [6, 2]},
    "health":       {"primary": [1],  "secondary": [6, 8]},
    "marriage":     {"primary": [7],  "secondary": [2]},
    "wealth":       {"primary": [2],  "secondary": [11, 9]},
    "progeny":      {"primary": [5],  "secondary": []},
    "foreign":      {"primary": [12], "secondary": [9]},
    "spirituality": {"primary": [12], "secondary": [9]},
    "family":       {"primary": [4],  "secondary": [2]},
    "education":    {"primary": [5],  "secondary": [9]},
    "property":     {"primary": [4],  "secondary": [8]},
    "courage":      {"primary": [3],  "secondary": [1]},
    "litigation":   {"primary": [6],  "secondary": [12]},
}

# Vocabulary normalisation: maps alternate domain labels to canonical key above.
DOMAIN_ALIASES: dict[str, str] = {
    "profession":   "career",
    "vocation":     "career",
    "matrimony":    "marriage",
    "spouse":       "marriage",
    "ill-health":   "health",
    "disease":      "health",
    "children":     "progeny",
    "offspring":    "progeny",
    "abroad":       "foreign",
    "foreign_travel": "foreign",
    "gains":        "wealth",
    "income":       "wealth",
    "money":        "wealth",
}


def normalize_domain(domain: str) -> str:
    """Return canonical domain string, lower-cased and alias-resolved."""
    d = domain.strip().lower()
    return DOMAIN_ALIASES.get(d, d)


class Rationale(TypedDict):
    """Astrological justification for a gap."""
    condition_name: str
    logic: str
    suggested_offset: float
    suggested_alignment: Optional[int]  # NEW: Target canonical age
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
        domain = normalize_domain(gap["life_event"].get("domain", ""))
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
                    "logic": "1st house (Sun) confronts 8th house (Mars) ruthlessly. Results manifest specifically around Mars maturity (28).",
                    "suggested_offset": 0.0,
                    "suggested_alignment": 28,
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
                        "logic": "H10 is dormant. Lord Saturn in 8/12 delays the 'awakening' until Saturn's maturity age (36).",
                        "suggested_offset": 0.0,
                        "suggested_alignment": 36,
                        "target_planet": "Saturn",
                        "target_house": 10
                    }

        # 4. Venus in H10 (Imaginary Saturn)
        # Rule: native is amative/greedy; results delayed or damaged.
        if ven.get("house") == 10:
            if domain == "marriage" and ("Venus" in source_planets or not source_planets):
                return {
                    "condition_name": "Venus in H10 (Imaginary Saturn)",
                    "logic": "Venus acts as an 'Imaginary Saturn', delaying domestic stability until Saturn's cycle milestone (36).",
                    "suggested_offset": 0.0,
                    "suggested_alignment": 36,
                    "target_planet": "Venus",
                    "target_house": 10
                }

        # 5. Mercury in H9 (Highly Malefic till 34)
        if mer.get("house") == 9:
            if domain in ["marriage", "family"] and ("Mercury" in source_planets or not source_planets):
                # Rule: Malefic specifically until age 34.
                return {
                    "condition_name": "Mercury in H9 (Malefic till 34)",
                    "logic": "Mercury in H9 is highly malefic specifically until its maturity age of 34.",
                    "suggested_offset": 0.0,
                    "suggested_alignment": 34,
                    "target_planet": "Mercury",
                    "target_house": 9
                }

        # 8. Mercury in H8 (Disease/Debt)
        if mer.get("house") == 8:
            if domain in ["health", "career"] and ("Mercury" in source_planets or not source_planets):
                return {
                    "condition_name": "Mercury in H8 (Disease)",
                    "logic": "Mercury in 8th acts maliciously, bringing sudden long-term diseases or debts around its maturity age (34).",
                    "suggested_offset": 0.0,
                    "suggested_alignment": 34,
                    "target_planet": "Mercury",
                    "target_house": 8
                }

        # 8b. Saturn in H8 (Longevity/Injury)
        if sat.get("house") == 8:
            if domain in ["health", "death", "longevity"] and ("Saturn" in source_planets or not source_planets):
                return {
                    "condition_name": "Saturn in H8 (Longevity/Injury)",
                    "logic": "Saturn in H8 governs the span of life and physical crises, maturing at age 36.",
                    "suggested_offset": 0.0,
                    "suggested_alignment": 36,
                    "target_planet": "Saturn",
                    "target_house": 8
                }

        # 6. Saturn in H4 (Snake in Water)
        # Rule: Property at age 36. Impact on family sickness.
        if sat.get("house") == 4:
            if domain in ["health", "property"] and ("Saturn" in source_planets or not source_planets):
                return {
                    "condition_name": "Saturn in H4 (Snake in Water)",
                    "logic": "Property manifests specifically around Saturn's maturity age (36).",
                    "suggested_offset": 0.0,
                    "suggested_alignment": 36,
                    "target_planet": "Saturn",
                    "target_house": 4
                }

        # 7. Mercury in H12 (Speech/Isolation)
        if mer.get("house") == 12:
            if domain in ["health", "career"] and ("Mercury" in source_planets or not source_planets):
                # Rule: "Poisonous speech" or stammering; isolation.
                return {
                    "condition_name": "Mercury in H12 (Speech/Isolation)",
                    "logic": "Mercury in H12 causes hurdles until its maturation at age 34.",
                    "suggested_offset": 0.0,
                    "suggested_alignment": 34,
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
                    "logic": "Sun in H8 (Sun of cemetery) brings results specifically after Saturn's maturity (36) or Rahu's (42). Aligning to 36.",
                    "suggested_offset": 0.0,
                    "suggested_alignment": 36,
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
                return {
                    "condition_name": "Takrav (Sun H1 vs Saturn H7)",
                    "logic": "Sun in H1 is confronted by Saturn in H7, delaying stability until Saturn's maturity (36).",
                    "suggested_offset": 0.0,
                    "suggested_alignment": 36,
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
        jup_house = jup.get("house")
        nodes_houses = [rah.get("house"), planets.get("Ketu", {}).get("house")]
        if jup_house and jup_house in nodes_houses:
            if domain in ["wealth", "fortune", "career", "profession"] and ("Jupiter" in source_planets or not source_planets):
                # Rule: Destiny becomes dual/smoke. 
                # Use "Guru-Chandal" name consistently for tests. 
                return {
                    "condition_name": "Guru-Chandal",
                    "logic": "Jupiter is eclipsed by a Node. Fortune typically manifests after Rahu's maturity (42) or Ketu's (48).",
                    "suggested_offset": 0.0,
                    "suggested_alignment": 42, # Rahu maturity as initial milestone
                    "target_planet": "Jupiter",
                    "target_house": jup.get("house")
                }

        # 18. Saturn Lord of 10 in 8 or 12
        if sat.get("house") in [8, 12] and birth_chart.get("house_status", {}).get("10") == "Occupied":
            if domain in ["career", "profession"] and ("Saturn" in source_planets or not source_planets):
                # Rule: Lord of Karma in the house of death/loss.
                return {
                    "condition_name": "Malefic Saturn (Lord 10 in 8/12)",
                    "logic": "Karma Lord is in 8 or 12, causing career results to manifest specifically after Saturn's maturity (36).",
                    "suggested_offset": 0.0,
                    "suggested_alignment": 36,
                    "target_planet": "Saturn",
                    "target_house": 10
                }

        # 19. Progeny: Saturn in H5 (Blind Snake/Delay)
        if sat.get("house") == 5:
            if domain == "progeny" and ("Saturn" in source_planets or not source_planets):
                # Lal Kitab: Native reaches the age of 48; blind snake strikes before that.
                # alignment logic: if event is near 48, snap to 48.
                return {
                    "condition_name": "Saturn in H5 (Blind Snake)",
                    "logic": "Saturn in H5 acts as a blind snake devouring children until the native reaches age 48.",
                    "suggested_offset": 0.0, 
                    "suggested_alignment": 48,
                    "target_planet": "Saturn",
                    "target_house": 5
                }

        # 20. Progeny: Ketu H11 + Jup/Sat/Moon H5 (Delay)
        ket = planets.get("Ketu", {})
        if ket.get("house") == 11 and jup.get("house") == 5: # Simplified match for Jup H5
            if domain == "progeny":
                return {
                    "condition_name": "Ketu H11 vs Jup H5 (Progeny Delay)",
                    "logic": "Ketu in 11 and Jupiter in 5 creates a block for progeny results (P.307).",
                    "suggested_offset": offset,
                    "target_planet": "Jupiter",
                    "target_house": 5
                }

        # 21. Litigation: Moon H12 + Ketu H1 (Court Cases)
        if moon := planets.get("Moon", {}):
            if moon.get("house") == 12 and ket.get("house") == 1:
                if domain == "litigation":
                    return {
                        "condition_name": "Moon H12 + Ketu H1 (Litigation)",
                        "logic": "Unlucky configuration leading to litigations and prosecutions (P.450).",
                        "suggested_offset": offset,
                        "suggested_alignment": None,
                        "target_planet": "Moon",
                        "target_house": 12
                    }

        # Rahu in H6 removed as per feedback (benefic/exalted placement).

        # 22. Wealth: Rahu in H9 (Destiny after 42)
        if rah.get("house") == 9:
            if domain == "wealth":
                return {
                    "condition_name": "Rahu in H9 (Maturity Age 42)",
                    "logic": "Rahu in 9 makes destiny shine specifically after the age of 42 (P.104).",
                    "suggested_offset": 0.0,
                    "target_house": 9
                }

        # 23. 35-Year Cycle Reset (End of 1st Cycle / Start of 2nd)
        # Lal Kitab: Life events often repeat or manifest at completion of 35-year cycle (Age 36).
        if actual_age in [36, 71] and abs(gap["predicted_peak_age"] - 0.0) < 1.0:
            # If there's a strong natal promise (predicted at age 0) but no timing, align to cycle.
            return {
                "condition_name": "35-Year Cycle Reset (Age 36/71)",
                "logic": "The completion of the 35-year cycle (Age 35) triggers manifestation of dormant natal promises in the following year (36).",
                "suggested_offset": 0.0,
                "suggested_alignment": actual_age,
                "target_planet": "Generic",
                "target_house": 0
            }

        return None

    def generate_hypotheses(
        self, gap_report: GapReport, birth_chart: ChartData,
        life_event_log=None  # Optional[LifeEventLog] — avoids circular import
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
                    planet = rationale.get("target_planet") or "Generic"
                    house = rationale.get("target_house") or 0
                    
                    target_alignment = rationale.get("suggested_alignment")
                    actual_event_age = entry["life_event"]["age"]
                    
                    if target_alignment is not None and abs(actual_event_age - target_alignment) <= 2.0:
                        key = f"align.{planet.lower()}_h{house}"
                        hypotheses.append({
                            "type": "Alignment",
                            "key": key,
                            "value": int(target_alignment),
                            "rationale": f"{rationale['condition_name']}: {rationale['logic']}",
                            "target_age": int(target_alignment)
                        })
                    else:
                        key = f"delay.{planet.lower()}_h{house}"
                        hypotheses.append({
                            "type": "Delay",
                            "key": key,
                            "value": float(actual_event_age - entry["predicted_peak_age"]),
                            "rationale": f"{rationale['condition_name']}: {rationale['logic']}",
                            "target_age": None
                        })

        # 2. Address Contradictions (Events with no matching domain prediction)
        #    Route through DOMAIN_HOUSE_MAP to find which planets sit in the
        #    canonical houses for that life domain, then propose Delay hypotheses.
        #    Use life_event_log to compute the actual required offset (actual_age - bench).
        planets_data = birth_chart.get("planets_in_houses", {})

        # Build a domain -> [actual_ages] lookup from the event log
        domain_actual_ages: dict[str, list[float]] = {}
        for ev in (life_event_log or []):
            canon = normalize_domain(ev.get("domain", ""))
            domain_actual_ages.setdefault(canon, []).append(float(ev.get("age", 0)))

        for domain in gap_report.get("contradictions", []):
            canonical = normalize_domain(domain)
            house_spec = DOMAIN_HOUSE_MAP.get(canonical)
            actual_ages = domain_actual_ages.get(canonical, [])

            generated_for_domain = False
            if house_spec:
                # Check primary houses first, then secondary
                for house_num in house_spec["primary"] + house_spec["secondary"]:
                    for planet, pdata in planets_data.items():
                        if pdata.get("house") == house_num:
                            bench = PLANET_EFFECTIVE_AGES.get(planet, 0)
                            key = f"delay.{planet.lower()}_h{house_num}"
                            # Compute offset: use the closest actual event age to bench
                            if actual_ages and bench:
                                closest_age = min(actual_ages, key=lambda a: abs(a - bench))
                                computed_offset = float(closest_age - bench)
                            else:
                                computed_offset = 0.0
                            # Avoid duplicate keys
                            if not any(h["key"] == key for h in hypotheses):
                                hypotheses.append({
                                    "type": "Delay",
                                    "key": key,
                                    "value": computed_offset,
                                    "rationale": (
                                        f"Domain '{canonical}' contradiction: {planet} sits in "
                                        f"H{house_num} (primary house for {canonical}). "
                                        f"Bench={bench}, actual={closest_age if actual_ages else '?'}, "
                                        f"offset={computed_offset:+.1f}."
                                    ),
                                    "target_age": bench
                                })
                                generated_for_domain = True

            # Fallback grammar hypothesis for career/profession sleeping house
            if not generated_for_domain and canonical in ("career", "profession"):
                house_status = birth_chart.get("house_status", {})
                if house_status.get("10") == "Sleeping House":
                    hypotheses.append({
                        "type": "Grammar",
                        "key": "grammar.h10_sleep_cancelled",
                        "value": True,
                        "rationale": "Soya Ghar logic: H10 career rules are blocked; hypothesizing cancellation due to unrecorded travel/H12.",
                        "target_age": None
                    })

        return hypotheses

    def rank_hypotheses(self, hypotheses: list[Hypothesis]) -> list[Hypothesis]:
        """
        Simple ranking: Delay constants first, then Grammar.
        """
        return sorted(hypotheses, key=lambda h: (h["type"] != "Delay", h["type"] != "Grammar"))
