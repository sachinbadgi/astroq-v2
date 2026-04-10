"""
Module: RemedyEngine
File:   backend/astroq/lk_prediction/remedy_engine.py

Implements Lal Kitab Planet Shifting (Graha Parivartan) logic:
  1. Identify safe target houses per planet (birth × annual intersection)
  2. Rank safe houses using Goswami priority rules
  3. Project lifetime strength with vs. without remedies
  4. Aggregate life-area improvement potential
  5. Surface top-3 remedy hints for LKPrediction output

All constants are config-driven via ModelConfig (remedy.* prefix).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from astroq.lk_prediction.config import ModelConfig


# ---------------------------------------------------------------------------
# Reference Constants
# ---------------------------------------------------------------------------

# Extended Pucca Ghars — safe target houses for remedy shifting.
# NOTE: These are broader than the single Pakka Ghar used in StrengthEngine.
PUCCA_GHARS: dict[str, list[int]] = {
    "Sun":     [1, 5],
    "Moon":    [2, 4],
    "Mars":    [3, 8, 10],
    "Mercury": [6, 7],
    "Jupiter": [2, 4, 5, 9, 11, 12],
    "Venus":   [2, 7, 12],
    "Saturn":  [7, 8, 10, 11],
    "Rahu":    [3, 6, 12],
    "Ketu":    [6, 9, 12],
}

EXALTATION_HOUSES: dict[str, list[int]] = {
    "Sun":     [1],
    "Moon":    [2],
    "Mars":    [10],
    "Mercury": [6],
    "Jupiter": [4],
    "Venus":   [12],
    "Saturn":  [7],
    "Rahu":    [3, 6],
    "Ketu":    [9, 12],
}

ENEMIES: dict[str, list[str]] = {
    "Sun":     ["Saturn", "Venus", "Rahu", "Ketu"],
    "Moon":    ["Rahu", "Ketu"],
    "Mars":    ["Mercury", "Ketu"],
    "Mercury": ["Moon"],
    "Jupiter": ["Mercury", "Venus"],
    "Venus":   ["Sun", "Moon", "Rahu"],
    "Saturn":  ["Sun", "Moon", "Mars"],
    "Rahu":    ["Sun", "Venus", "Mars", "Moon", "Ketu"],
    "Ketu":    ["Moon", "Mars", "Rahu"],
}

# Maps artificial planet names → base planet (for enemy checks)
MASNUI_TO_STANDARD: dict[str, str] = {
    "Artificial Jupiter": "Jupiter",
    "Artificial Sun": "Sun",
    "Artificial Moon": "Moon",
    "Artificial Venus": "Venus",
    "Artificial Mars (Auspicious)": "Mars",
    "Artificial Mars (Malefic)": "Mars",
    "Artificial Mercury": "Mercury",
    "Artificial Saturn (Like Ketu)": "Saturn",
    "Artificial Saturn (Like Rahu)": "Saturn",
    "Artificial Rahu (Debilitated Rahu)": "Rahu",
    "Artificial Rahu (Exalted Rahu)": "Rahu",
    "Artificial Ketu (Exalted Ketu)": "Ketu",
    "Artificial Ketu (Debilitated Ketu)": "Ketu",
}

# Goswami companion pairs: (planet_a, planet_b) → preferred target houses
GOSWAMI_PAIR_TARGETS: dict[tuple[str, str], list[int]] = {
    ("Moon", "Jupiter"): [2, 4, 10],
    ("Jupiter", "Moon"): [2, 4, 10],
    ("Sun", "Moon"):     [1, 2, 4],
    ("Moon", "Sun"):     [1, 2, 4],
    ("Mars", "Saturn"):  [8, 10],
    ("Saturn", "Mars"):  [8, 10],
}

LIFE_AREA_GROUPS: dict[str, list[str]] = {
    "Wealth & Prosperity": ["Jupiter", "Venus", "Mercury"],
    "Health & Vitality":   ["Sun", "Mars", "Saturn"],
    "Career & Status":     ["Sun", "Mars", "Jupiter"],
    "Relationships & Joy": ["Venus", "Moon", "Jupiter"],
}

STANDARD_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter",
                    "Venus", "Saturn", "Rahu", "Ketu"]


# ---------------------------------------------------------------------------
# Data Contracts
# ---------------------------------------------------------------------------

@dataclass
class ShiftingOption:
    """Represents a single ranked target house for a planet shift."""
    house: int
    score: int
    rank: str           # "CRITICAL" | "High" | "Medium" | "Low"
    rationale: str
    articles: list[str] = field(default_factory=list)


@dataclass
class PlanetShiftingResult:
    """All shifting options for one planet in one year."""
    planet: str
    birth_house: int
    annual_house: int
    safe_matches: list[ShiftingOption]   # sorted by score desc
    other_options: list[int]             # houses safe in birth only (info)
    conflicts: dict[int, str]
    llm_hint: str = ""


@dataclass
class LifetimeStrengthProjection:
    """Strength trajectories for all planets across 75 ages."""
    ages: list[int]
    planets: dict[str, dict]
    # planet → {baseline: list, remedy: list, cum_baseline: list, cum_remedy: list}


@dataclass
class LifeAreaSummary:
    """Aggregated lifetime improvement potential for one life area."""
    area: str
    fixed_fate: float
    current_remediation: float
    untapped_potential: float
    max_remediable: float
    remediation_efficiency: float   # 0-100%


# ---------------------------------------------------------------------------
# RemedyEngine
# ---------------------------------------------------------------------------

class RemedyEngine:
    """
    Lal Kitab Planet Shifting (Graha Parivartan) remedy engine.

    Identifies safe target houses, ranks them with Goswami rules, projects
    lifetime strength improvements, and generates remedy hints for LKPrediction.
    """

    def __init__(self, config: ModelConfig, items_resolver: Any) -> None:
        self._cfg = config
        self._resolver = items_resolver
        self._birth_safe_cache: dict[str, tuple[list[int], dict[int, str]]] = {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_pih(self, chart: dict) -> dict:
        """Return planets_in_houses dict, supporting both field names."""
        return (
            chart.get("planet_analysis")
            or chart.get("planets_in_houses")
            or {}
        )

    def _get_planet_house(self, pih: dict, planet: str) -> int:
        data = pih.get(planet, {})
        return data.get("house", 0)

    def _get_planet_states(self, pih: dict, planet: str) -> list[str]:
        data = pih.get(planet, {})
        return data.get("states", [])

    def _score_to_rank(self, score: int) -> str:
        critical = int(self._cfg.get("remedy.critical_score_threshold", fallback=60))
        high = int(self._cfg.get("remedy.high_score_threshold", fallback=40))
        medium = int(self._cfg.get("remedy.medium_score_threshold", fallback=20))
        if score >= critical:
            return "CRITICAL"
        if score >= high:
            return "High"
        if score >= medium:
            return "Medium"
        return "Low"

    def _build_rationale(self, house: int, reasons: list[str]) -> str:
        reasons_str = "; ".join(reasons) if reasons else "Standard safe house"
        return f"House {house} — {reasons_str}"

    # ------------------------------------------------------------------
    # Core: get_safe_houses
    # ------------------------------------------------------------------

    def get_safe_houses(
        self,
        planet: str,
        chart: dict,
    ) -> tuple[list[int], dict[int, str]]:
        """
        Returns (safe_house_list, conflict_map) for one planet in one chart.

        Base recs = PUCCA_GHARS[planet] ∪ EXALTATION_HOUSES[planet]
        A house is safe if no enemy of `planet` sits there (standard or masnui).
        """
        base_recs = sorted(
            set(PUCCA_GHARS.get(planet, []) + EXALTATION_HOUSES.get(planet, []))
        )
        pih = self._get_pih(chart)
        masnui_list = chart.get("masnui_grahas_formed", [])
        enemies = ENEMIES.get(planet, [])

        safe: list[int] = []
        conflicts: dict[int, str] = {}

        for h in base_recs:
            blockers: list[str] = []
            # Check standard planets
            for p, data in pih.items():
                if data.get("house") == h and p in enemies:
                    blockers.append(p)
            # Check masnui planets (resolve to standard)
            for m in masnui_list:
                m_name = m.get("name", "")
                m_house = m.get("house")
                if m_house == h and MASNUI_TO_STANDARD.get(m_name) in enemies:
                    blockers.append(m_name)

            if blockers:
                conflicts[h] = f"Blocked by {', '.join(str(b) for b in blockers)}"
            else:
                safe.append(h)

        return safe, conflicts

    # ------------------------------------------------------------------
    # Core: get_year_shifting_options
    # ------------------------------------------------------------------

    def get_year_shifting_options(
        self,
        birth_chart: dict,
        annual_chart: dict,
        age: int,
    ) -> dict[str, PlanetShiftingResult]:
        """
        Returns per-planet {planet: PlanetShiftingResult} for one age.

        safe_matches = birth_safe ∩ annual_safe (must be safe in BOTH charts).
        """
        results: dict[str, PlanetShiftingResult] = {}
        birth_pih = self._get_pih(birth_chart)
        annual_pih = self._get_pih(annual_chart)

        for planet in STANDARD_PLANETS:
            # Cache birth-safe houses as they never change for a given native
            if planet not in self._birth_safe_cache:
                self._birth_safe_cache[planet] = self.get_safe_houses(planet, birth_chart)
            
            birth_safe, b_conflicts = self._birth_safe_cache[planet]
            annual_safe, a_conflicts = self.get_safe_houses(planet, annual_chart)

            safe_matches_houses = [h for h in birth_safe if h in annual_safe]

            # Other options: in birth but not annual, or vice versa
            birth_set = set(birth_safe)
            annual_set = set(annual_safe)
            other_options = sorted(
                (birth_set | annual_set) - set(safe_matches_houses)
            )

            # Merge conflicts with source prefix
            conflict_map: dict[int, str] = {}
            for h, reason in b_conflicts.items():
                conflict_map[h] = f"Birth: {reason}"
            for h, reason in a_conflicts.items():
                if h in conflict_map:
                    conflict_map[h] += f" | Annual: {reason}"
                else:
                    conflict_map[h] = f"Annual: {reason}"

            # Rank the safe houses
            ranked = self.rank_safe_houses(planet, safe_matches_houses, annual_chart, annual_pih)

            birth_house = self._get_planet_house(birth_pih, planet)
            annual_house = self._get_planet_house(annual_pih, planet)

            # Build LLM one-liner
            if ranked:
                top = ranked[0]
                llm_hint = (
                    f"{planet}: shift to House {top.house} "
                    f"[{top.rank}, score={top.score}] — {top.rationale}"
                )
            else:
                llm_hint = f"{planet}: no safe shifting options this year"

            results[planet] = PlanetShiftingResult(
                planet=planet,
                birth_house=birth_house,
                annual_house=annual_house,
                safe_matches=ranked,
                other_options=other_options,
                conflicts=conflict_map,
                llm_hint=llm_hint,
            )

        return results

    # ------------------------------------------------------------------
    # Core: rank_safe_houses
    # ------------------------------------------------------------------

    def rank_safe_houses(
        self,
        planet: str,
        safe_houses: list[int],
        annual_chart: dict,
        annual_planets: dict,
    ) -> list[ShiftingOption]:
        """
        Score and rank each safe house using Goswami priority rules.

        Scoring is additive (base=10):
          +goswami_h9_weight (30)  if house == 9
          +goswami_h2_weight (20)  if house == 2
          +goswami_h4_weight (10)  if house == 4
          +goswami_unblock_weight (50)  if annual planet is in H8 AND target in [2,4]
          +goswami_pair_weight (40)  if planet in a pair AND companion at same annual house
                                     AND target in pair's preferred houses
          +goswami_doubtful_weight (20)  if "Doubtful" in planet's annual states
        """
        cfg = self._cfg
        h9_w  = int(cfg.get("remedy.goswami_h9_weight",      fallback=30))
        h2_w  = int(cfg.get("remedy.goswami_h2_weight",      fallback=20))
        h4_w  = int(cfg.get("remedy.goswami_h4_weight",      fallback=10))
        unb_w = int(cfg.get("remedy.goswami_unblock_weight", fallback=50))
        pair_w = int(cfg.get("remedy.goswami_pair_weight",   fallback=40))
        dbt_w = int(cfg.get("remedy.goswami_doubtful_weight",fallback=20))

        # Planet's data this annual year
        planet_annual_house = self._get_planet_house(annual_planets, planet)
        planet_annual_states = self._get_planet_states(annual_planets, planet)
        is_doubtful = "Doubtful" in planet_annual_states

        options: list[ShiftingOption] = []
        for h in safe_houses:
            score = 10  # base
            reasons: list[str] = []

            # House preference weights
            if h == 9:
                score += h9_w
                reasons.append("Preferred house H9")
            if h == 2:
                score += h2_w
                reasons.append("Preferred house H2")
            if h == 4:
                score += h4_w
                reasons.append("Preferred house H4")

            # Unblock rule: planet in H8 → H2 or H4 unlock [P148]
            if planet_annual_house == 8 and h in [2, 4]:
                score += unb_w
                reasons.append("Unblock from H8 [P148]")

            # Goswami pair rule
            pair_key = None
            for (pa, pb), targets in GOSWAMI_PAIR_TARGETS.items():
                if planet == pa:
                    companion = pb
                    companion_house = self._get_planet_house(annual_planets, companion)
                    # Companion must be at the same house as the planet this year
                    if companion_house == planet_annual_house and h in targets:
                        score += pair_w
                        reasons.append(f"Goswami pair {pa}+{pb} → H{h}")
                        break

            # Doubtful state boost
            if is_doubtful:
                score += dbt_w
                reasons.append("Doubtful planet boost")

            rank = self._score_to_rank(score)
            rationale = self._build_rationale(h, reasons)

            # Get physical articles from items_resolver
            try:
                articles = self._resolver.get_planet_items(planet, h)
            except Exception:
                articles = []

            options.append(ShiftingOption(
                house=h,
                score=score,
                rank=rank,
                rationale=rationale,
                articles=articles,
            ))

        return sorted(options, key=lambda o: o.score, reverse=True)

    # ------------------------------------------------------------------
    # Lifetime simulation
    # ------------------------------------------------------------------

    def simulate_lifetime_strength(
        self,
        birth_chart: dict,
        annual_charts: dict,
        applied_remedies: list[dict] | None = None,
    ) -> LifetimeStrengthProjection:
        """
        Projects strength[planet][age] baseline vs remedied across all years.

        Algorithm per planet per age:
          boost = SHIFTING_BOOST * multiplier if remedy applied this year
          residual += boost * RESIDUAL_IMPACT_FACTOR  (cumulative carry-forward)
          total = base + boost + residual
        """
        applied_remedies = applied_remedies or []
        shifting_boost    = float(self._cfg.get("remedy.shifting_boost",         fallback=2.5))
        residual_factor   = float(self._cfg.get("remedy.residual_impact_factor", fallback=0.05))
        safe_mult         = float(self._cfg.get("remedy.safe_multiplier",        fallback=1.0))
        unsafe_mult       = float(self._cfg.get("remedy.unsafe_multiplier",      fallback=0.5))

        all_ages = sorted(annual_charts.keys())
        result: dict[str, dict] = {}

        for planet in STANDARD_PLANETS:
            residual = 0.0
            baseline_list: list[float] = []
            remedy_list: list[float]   = []
            cum_b, cum_r = 0.0, 0.0
            cum_b_list: list[float] = []
            cum_r_list: list[float] = []

            for age in all_ages:
                pih = self._get_pih(annual_charts[age])
                base = float(pih.get(planet, {}).get("strength_total", 0.0))

                boost = 0.0
                for rem in applied_remedies:
                    if rem.get("planet") == planet and rem.get("age") == age:
                        mult = safe_mult if rem.get("is_safe", True) else unsafe_mult
                        boost = shifting_boost * mult
                        residual += boost * residual_factor

                total = base + boost + residual
                baseline_list.append(base)
                remedy_list.append(total)
                cum_b += base
                cum_r += total
                cum_b_list.append(cum_b)
                cum_r_list.append(cum_r)

            result[planet] = {
                "baseline":     baseline_list,
                "remedy":       remedy_list,
                "cum_baseline": cum_b_list,
                "cum_remedy":   cum_r_list,
            }

        return LifetimeStrengthProjection(ages=all_ages, planets=result)

    # ------------------------------------------------------------------
    # Life area aggregation
    # ------------------------------------------------------------------

    def analyze_life_area_potential(
        self,
        birth_chart: dict,
        annual_charts: dict,
        applied_remedies: list[dict] | None = None,
        current_age: int = 1,
    ) -> dict[str, LifeAreaSummary]:
        """Returns life area summaries from current_age to end of annual_charts."""
        applied_remedies = applied_remedies or []
        all_ages = sorted(annual_charts.keys())
        relevant_ages = [a for a in all_ages if a >= current_age]

        # Simulate with provided remedies
        proj_applied = self.simulate_lifetime_strength(birth_chart, annual_charts, applied_remedies)

        # Simulate max: apply shifting_boost to every planet in every age (safe=True)
        max_remedies: list[dict] = []
        for planet in STANDARD_PLANETS:
            for age in relevant_ages:
                max_remedies.append({"planet": planet, "age": age, "is_safe": True})
        proj_max = self.simulate_lifetime_strength(birth_chart, annual_charts, max_remedies)

        summaries: dict[str, LifeAreaSummary] = {}
        for area, planets_in_area in LIFE_AREA_GROUPS.items():
            fixed_fate = 0.0
            applied_sum = 0.0
            max_sum = 0.0

            for planet in planets_in_area:
                if planet not in proj_applied.planets:
                    continue
                p_data_applied = proj_applied.planets[planet]
                p_data_max = proj_max.planets[planet]

                for i, age in enumerate(all_ages):
                    if age < current_age:
                        continue
                    fixed_fate  += p_data_applied["baseline"][i]
                    applied_sum += p_data_applied["remedy"][i]
                    max_sum     += p_data_max["remedy"][i]

            current_remediation = applied_sum - fixed_fate
            max_remediable      = max_sum - fixed_fate
            untapped_potential  = max(0.0, max_remediable - current_remediation)
            denominator         = max(max_remediable, 0.1)  # avoid div by zero
            efficiency          = (current_remediation / denominator) * 100.0
            efficiency          = max(0.0, min(100.0, efficiency))

            summaries[area] = LifeAreaSummary(
                area=area,
                fixed_fate=fixed_fate,
                current_remediation=current_remediation,
                untapped_potential=untapped_potential,
                max_remediable=max_remediable,
                remediation_efficiency=efficiency,
            )

        return summaries

    # ------------------------------------------------------------------
    # Output helpers
    # ------------------------------------------------------------------

    def generate_remedy_hints(
        self,
        year_options: dict[str, PlanetShiftingResult],
        chart: dict | None = None,
    ) -> list[str]:
        """
        Returns top-3 CRITICAL/High priority hints as list[str].
        
        Enhancements (Phase F):
          1. Includes Birth Day "Helpful Remedy" if birth_time is present.
          2. Includes specific Mars remedies if mangal_badh_status is 'Active'.
          3. Sorts by Kendra priority (1 > 10 > 7 > 4) for equal Goswami scores.
        """
        all_opts: list[tuple[str, ShiftingOption]] = []
        for planet, result in year_options.items():
            for opt in result.safe_matches:
                if opt.rank in ("CRITICAL", "High"):
                    all_opts.append((planet, opt))

        # Kendra Priority: 1 > 10 > 7 > 4
        kendra_order = {1: 1, 10: 2, 7: 3, 4: 4}

        def sort_key(item):
            planet, opt = item
            # Primary: Goswami Score desc
            # Secondary: Kendra priority asc (1 is highest)
            # Tertiary: House number asc
            k_score = kendra_order.get(opt.house, 99)
            return (-opt.score, k_score, opt.house)

        all_opts.sort(key=sort_key)
        top3_raw = all_opts[:3]

        hints: list[str] = []
        
        # 1. Add Birth Day helpful hint (Page 164)
        if chart and "birth_time" in chart:
            try:
                from datetime import datetime
                # ISO format usually or YYYY-MM-DD
                bt_str = chart["birth_time"]
                # Try simple ISO first
                dt = datetime.fromisoformat(bt_str.replace("Z", "+00:00"))
                weekday = dt.strftime("%w") # 0=Sun, 1=Mon...
                day_remedies = self._cfg.get("remedy.birth_day_remedies", fallback={})
                if weekday in day_remedies:
                    hints.append(f"Helpful Remedy: {day_remedies[weekday]}")
            except Exception:
                pass

        # 2. Add Special Mars hints (Pages 158-163)
        if chart and chart.get("mangal_badh_status") == "Active":
            mars_hints = self._cfg.get("remedy.mangal_badh_hints", fallback=[])
            if mars_hints:
                # Add one prominent Mars hint if not already crowded
                hints.append(f"Mars Malefic (-): {mars_hints[0]}")

        # 3. Add Planet Shifting hints
        for planet, opt in top3_raw:
            articles_str = (
                ", ".join(opt.articles) if opt.articles else "keep related articles nearby"
            )
            hint = (
                f"Shift {planet} to House {opt.house} [{opt.rank}]: "
                f"{opt.rationale}. Articles: {articles_str}"
            )
            hints.append(hint)

        return hints[:4] # Allow up to 4 if special hints are added

    def get_llm_remedy_summary(
        self,
        birth_chart: dict,
        annual_chart: dict,
        age: int,
    ) -> str:
        """
        Returns a formatted markdown remedy roadmap string (for RLM context / LLM prompts).
        """
        annual_pih = self._get_pih(annual_chart)
        year_options = self.get_year_shifting_options(birth_chart, annual_chart, age)

        lines: list[str] = [f"## Remedy Options for Age {age}\n"]
        for planet, result in year_options.items():
            if not result.safe_matches:
                continue
            lines.append(f"### {planet} (currently in House {result.annual_house})")
            for opt in result.safe_matches:
                articles_str = ", ".join(opt.articles) if opt.articles else "—"
                lines.append(
                    f"- **[{opt.rank}]** House {opt.house} "
                    f"(score={opt.score}) — {opt.rationale}"
                )
                lines.append(f"  Articles: {articles_str}")
            lines.append("")

        return "\n".join(lines)
