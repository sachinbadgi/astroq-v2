"""
RemedyEngine
============
Deterministic Lal Kitab Remedy Generator based on the 1952 methodology.
Uses the StateLedger (Trauma/Friction) to determine when a remedy is needed.

Also retains the legacy Graha Parivartan (Planet Shifting) API for backward
compatibility with existing tests and callers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from .lk_constants import (
    PLANET_HOUSE_ITEMS,
    FOUNDATIONAL_HOUSES,
    PUCCA_GHARS_EXTENDED,
    PLANET_EXALTATION as LK_PLANET_EXALTATION,
    ENEMIES as LK_ENEMIES,
)
from .data_contracts import LKPrediction, ChartData


# ---------------------------------------------------------------------------
# Legacy Constants (Graha Parivartan API)
# ---------------------------------------------------------------------------

_LEGACY_PUCCA_GHARS: dict[str, list[int]] = {
    "Sun": [1, 5],
    "Moon": [2, 4],
    "Mars": [3, 8, 10],
    "Mercury": [6, 7],
    "Jupiter": [2, 4, 5, 9, 11, 12],
    "Venus": [2, 7, 12],
    "Saturn": [7, 8, 10, 11],
    "Rahu": [3, 6, 12],
    "Ketu": [6, 9, 12],
}

_LEGACY_EXALTATION_HOUSES: dict[str, list[int]] = {
    "Sun": [1],
    "Moon": [2],
    "Mars": [10],
    "Mercury": [6],
    "Jupiter": [4],
    "Venus": [12],
    "Saturn": [7],
    "Rahu": [3, 6],
    "Ketu": [9, 12],
}

_LEGACY_ENEMIES: dict[str, list[str]] = {
    "Sun": ["Saturn", "Venus", "Rahu", "Ketu"],
    "Moon": ["Rahu", "Ketu"],
    "Mars": ["Mercury", "Ketu"],
    "Mercury": ["Moon"],
    "Jupiter": ["Mercury", "Venus"],
    "Venus": ["Sun", "Moon", "Rahu"],
    "Saturn": ["Sun", "Moon", "Mars"],
    "Rahu": ["Sun", "Venus", "Mars", "Moon", "Ketu"],
    "Ketu": ["Moon", "Mars", "Rahu"],
}

_MASNUI_TO_STANDARD: dict[str, str] = {
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

_GOSWAMI_PAIR_TARGETS: dict[tuple[str, str], list[int]] = {
    ("Moon", "Jupiter"): [2, 4, 10],
    ("Jupiter", "Moon"): [2, 4, 10],
    ("Sun", "Moon"): [1, 2, 4],
    ("Moon", "Sun"): [1, 2, 4],
    ("Mars", "Saturn"): [8, 10],
    ("Saturn", "Mars"): [8, 10],
}

_LIFE_AREA_GROUPS: dict[str, list[str]] = {
    "Wealth & Prosperity": ["Jupiter", "Venus", "Mercury"],
    "Health & Vitality": ["Sun", "Mars", "Saturn"],
    "Career & Status": ["Sun", "Mars", "Jupiter"],
    "Relationships & Joy": ["Venus", "Moon", "Jupiter"],
}

_LEGACY_STANDARD_PLANETS = [
    "Sun", "Moon", "Mars", "Mercury", "Jupiter",
    "Venus", "Saturn", "Rahu", "Ketu",
]

# Re-export for backward compatibility
STANDARD_PLANETS = _LEGACY_STANDARD_PLANETS


# ---------------------------------------------------------------------------
# Legacy Data Contracts
# ---------------------------------------------------------------------------

@dataclass
class ShiftingOption:
    house: int
    score: int
    rank: str
    rationale: str
    articles: list[str] = field(default_factory=list)


@dataclass
class PlanetShiftingResult:
    planet: str
    birth_house: int
    annual_house: int
    safe_matches: list[ShiftingOption]
    other_options: list[int]
    conflicts: dict[int, str]
    llm_hint: str = ""


@dataclass
class LifetimeStrengthProjection:
    ages: list[int]
    planets: dict[str, dict]


@dataclass
class LifeAreaSummary:
    area: str
    fixed_fate: float
    current_remediation: float
    untapped_potential: float
    max_remediable: float
    remediation_efficiency: float


# ---------------------------------------------------------------------------
# RemedyEngine
# ---------------------------------------------------------------------------

class RemedyEngine:
    """
    Generates remedies by mapping planetary trauma to canonical item substitutions.

    Accepts optional legacy params (config, items_resolver) for backward
    compatibility with the Graha Parivartan (Planet Shifting) API.
    """

    def __init__(self, config=None, items_resolver=None):
        # New API: config is optional
        self._cfg = config
        self._resolver = items_resolver
        self._birth_safe_cache: dict[str, tuple[list[int], dict[int, str]]] = {}

        # Biological/Living keywords for classification
        self.bio_keywords = [
            "Eyeball", "Nose", "Teeth", "Stomach", "Heart", "Skull", "Tongue",
            "Relatives", "Son", "Mother", "Father", "Brother", "Sister", "Wife", "Nephew",
            "Disease", "Asthma", "Epilepsy", "Baldness", "Sickly", "Body"
        ]

    # ------------------------------------------------------------------
    # New API (StateLedger-based)
    # ------------------------------------------------------------------

    def get_remedies_for_prediction(self, prediction: LKPrediction, ledger_state: Any, positions: Dict[str, int]) -> List[str]:
        remedies = []
        source_planets = prediction.source_planets

        for p_name in source_planets:
            if p_name not in ledger_state.planets or p_name not in positions:
                continue

            p_state = ledger_state.planets[p_name]
            house = positions[p_name]

            if p_state.is_burst or p_state.is_leaking:
                house_items = PLANET_HOUSE_ITEMS.get(p_name, {}).get(house, [])
                is_biological_hit = prediction.afflicts_living
                bio_items = [i for i in house_items if any(k.lower() in i.lower() for k in self.bio_keywords)]
                material_items = [i for i in house_items if i not in bio_items]

                if (is_biological_hit or bio_items) and material_items:
                    bio_target = bio_items[0] if bio_items else "Living Relative/Entity"
                    remedies.append(f"TRANSFERENCE: Safeguard '{bio_target}' (Biological) by using '{material_items[0]}' (Material).")
                elif material_items:
                    remedies.append(f"STRENGTHENING: Use {material_items[0]} to stabilize {p_name} in House {house}.")

                if p_state.modifier == "Startled Malefic":
                    remedies.append(f"COOLING: Planet is 'Startled'. Avoid iron and sharp objects associated with {p_name}.")

                if p_state.is_burst:
                    remedies.append(f"URGENT: Planet is Burst (Trauma {p_state.trauma_points:.1f}). Use 43-day continuous donation of {p_name} items.")

        if not remedies and getattr(prediction, "polarity", "") == "MALEFIC":
            for p_name in source_planets:
                houses = prediction.source_houses if prediction.source_houses else [positions.get(p_name)]
                for h in houses:
                    if not h:
                        continue
                    articles = PLANET_HOUSE_ITEMS.get(p_name, {}).get(h, [])
                    if articles:
                        remedies.append(f"Keep/Donate {articles[0]} related to {p_name} in House {h}.")
                        break

        return remedies

    def evaluate_remedy_impact(self, p_state: Any, remedy_type: str, safe_multiplier: float = 1.0, current_base_strength: float = 10.0, cumulative_residuals: float = 0.0) -> Dict[str, Any]:
        SHIFTING_BOOST = 2.5
        RESIDUAL_IMPACT_FACTOR = 0.05

        boost_current = SHIFTING_BOOST * safe_multiplier
        if remedy_type != "GRAHA_PARIVARTAN":
            boost_current = (0.5 if remedy_type == "TRANSFERENCE" else 0.2) * SHIFTING_BOOST

        new_residual = boost_current * RESIDUAL_IMPACT_FACTOR
        total_cumulative = cumulative_residuals + new_residual
        total_age_strength = current_base_strength + boost_current + cumulative_residuals

        max_possible = max(total_age_strength, 0.1)
        fixed_fate_percentage = (current_base_strength / max_possible) * 100
        max_remediable_percentage = ((boost_current + cumulative_residuals) / max_possible) * 100

        return {
            "leakage_reduction": 0.5 if remedy_type == "TRANSFERENCE" else 0.2,
            "can_reset_modifier": True if remedy_type == "COOLING" else False,
            "shifting_boost": boost_current,
            "new_cumulative_residual": total_cumulative,
            "total_projected_strength": total_age_strength,
            "fixed_fate_percentage": min(100.0, max(0.0, fixed_fate_percentage)),
            "max_remediable_percentage": min(100.0, max(0.0, max_remediable_percentage)),
        }

    def calculate_goswami_priority(self, planet: str, target_house: int, current_annual_house: int, annual_positions: Dict[str, int], p_state: Any = None) -> int:
        score = 10
        if target_house == 9:
            score += 30
        elif target_house == 2:
            score += 20
        elif target_house == 4:
            score += 10

        if current_annual_house == 8 and target_house in [2, 4]:
            score += 50

        friends_in_target = [
            p for p, h in annual_positions.items()
            if h == target_house and p != planet and p not in LK_ENEMIES.get(planet, [])
        ]
        if friends_in_target:
            score += 40

        if p_state and (getattr(p_state, 'modifier', '') == 'Doubtful' or getattr(p_state, 'is_startled', False)):
            score += 20

        return score

    def calculate_safe_houses(self, planet: str, birth_positions: Dict[str, int], annual_positions: Dict[str, int], p_state: Any = None) -> List[Dict[str, Any]]:
        base_houses = set(PUCCA_GHARS_EXTENDED.get(planet, []))
        if planet in LK_PLANET_EXALTATION:
            base_houses.update(LK_PLANET_EXALTATION[planet])

        planet_enemies = set(LK_ENEMIES.get(planet, []))

        def has_enemies(house: int, positions: Dict[str, int]) -> bool:
            for p, h in positions.items():
                if h == house and p in planet_enemies:
                    return True
            return False

        valid_targets = []
        for h in base_houses:
            if not has_enemies(h, birth_positions) and not has_enemies(h, annual_positions):
                valid_targets.append(h)

        current_annual_house = annual_positions.get(planet, 0)
        safe_houses = []
        for h in valid_targets:
            score = self.calculate_goswami_priority(planet, h, current_annual_house, annual_positions, p_state)
            if score >= 60:
                tier = "CRITICAL"
            elif score >= 40:
                tier = "High"
            elif score >= 20:
                tier = "Medium"
            else:
                tier = "Low"
            safe_houses.append({"house": h, "score": score, "tier": tier})

        def kendra_sort_key(item):
            base = item["score"] * 1000
            h = item["house"]
            kp = 0
            if h == 1:
                kp = 40
            elif h == 10:
                kp = 30
            elif h == 7:
                kp = 20
            elif h == 4:
                kp = 10
            return base + kp

        safe_houses.sort(key=kendra_sort_key, reverse=True)
        return safe_houses

    # ------------------------------------------------------------------
    # Legacy API (Graha Parivartan / Planet Shifting)
    # ------------------------------------------------------------------

    def _get_pih(self, chart: dict) -> dict:
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
        if self._cfg:
            critical = int(self._cfg.get("remedy.critical_score_threshold", fallback=60))
            high = int(self._cfg.get("remedy.high_score_threshold", fallback=40))
            medium = int(self._cfg.get("remedy.medium_score_threshold", fallback=20))
        else:
            critical, high, medium = 60, 40, 20
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

    def get_safe_houses(
        self,
        planet: str,
        chart: dict,
    ) -> tuple[list[int], dict[int, str]]:
        base_recs = sorted(
            set(_LEGACY_PUCCA_GHARS.get(planet, []) + _LEGACY_EXALTATION_HOUSES.get(planet, []))
        )
        pih = self._get_pih(chart)
        masnui_list = chart.get("masnui_grahas_formed", [])
        enemies = _LEGACY_ENEMIES.get(planet, [])

        safe: list[int] = []
        conflicts: dict[int, str] = {}

        for h in base_recs:
            blockers: list[str] = []
            for p, data in pih.items():
                if data.get("house") == h and p in enemies:
                    blockers.append(p)
            for m in masnui_list:
                m_name = m.get("name", "")
                m_house = m.get("house")
                if m_house == h and _MASNUI_TO_STANDARD.get(m_name) in enemies:
                    blockers.append(m_name)

            if blockers:
                conflicts[h] = f"Blocked by {', '.join(str(b) for b in blockers)}"
            else:
                safe.append(h)

        return safe, conflicts

    def get_year_shifting_options(
        self,
        birth_chart: dict,
        annual_chart: dict,
        age: int,
    ) -> dict[str, PlanetShiftingResult]:
        results: dict[str, PlanetShiftingResult] = {}
        birth_pih = self._get_pih(birth_chart)
        annual_pih = self._get_pih(annual_chart)

        for planet in _LEGACY_STANDARD_PLANETS:
            if planet not in self._birth_safe_cache:
                self._birth_safe_cache[planet] = self.get_safe_houses(planet, birth_chart)

            birth_safe, b_conflicts = self._birth_safe_cache[planet]
            annual_safe, a_conflicts = self.get_safe_houses(planet, annual_chart)

            safe_matches_houses = [h for h in birth_safe if h in annual_safe]

            birth_set = set(birth_safe)
            annual_set = set(annual_safe)
            other_options = sorted(
                (birth_set | annual_set) - set(safe_matches_houses)
            )

            conflict_map: dict[int, str] = {}
            for h, reason in b_conflicts.items():
                conflict_map[h] = f"Birth: {reason}"
            for h, reason in a_conflicts.items():
                if h in conflict_map:
                    conflict_map[h] += f" | Annual: {reason}"
                else:
                    conflict_map[h] = f"Annual: {reason}"

            ranked = self.rank_safe_houses(planet, safe_matches_houses, annual_chart, annual_pih)

            birth_house = self._get_planet_house(birth_pih, planet)
            annual_house = self._get_planet_house(annual_pih, planet)

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

    def rank_safe_houses(
        self,
        planet: str,
        safe_houses: list[int],
        annual_chart: dict,
        annual_planets: dict,
    ) -> list[ShiftingOption]:
        cfg = self._cfg
        h9_w = int(cfg.get("remedy.goswami_h9_weight", fallback=30)) if cfg else 30
        h2_w = int(cfg.get("remedy.goswami_h2_weight", fallback=20)) if cfg else 20
        h4_w = int(cfg.get("remedy.goswami_h4_weight", fallback=10)) if cfg else 10
        unb_w = int(cfg.get("remedy.goswami_unblock_weight", fallback=50)) if cfg else 50
        pair_w = int(cfg.get("remedy.goswami_pair_weight", fallback=40)) if cfg else 40
        dbt_w = int(cfg.get("remedy.goswami_doubtful_weight", fallback=20)) if cfg else 20

        planet_annual_house = self._get_planet_house(annual_planets, planet)
        planet_annual_states = self._get_planet_states(annual_planets, planet)
        is_doubtful = "Doubtful" in planet_annual_states

        options: list[ShiftingOption] = []
        for h in safe_houses:
            score = 10
            reasons: list[str] = []

            if h == 9:
                score += h9_w
                reasons.append("Preferred house H9")
            if h == 2:
                score += h2_w
                reasons.append("Preferred house H2")
            if h == 4:
                score += h4_w
                reasons.append("Preferred house H4")

            if planet_annual_house == 8 and h in [2, 4]:
                score += unb_w
                reasons.append("Unblock from H8 [P148]")

            for (pa, pb), targets in _GOSWAMI_PAIR_TARGETS.items():
                if planet == pa:
                    companion_house = self._get_planet_house(annual_planets, pb)
                    if companion_house == planet_annual_house and h in targets:
                        score += pair_w
                        reasons.append(f"Goswami pair {pa}+{pb} → H{h}")
                        break

            if is_doubtful:
                score += dbt_w
                reasons.append("Doubtful planet boost")

            rank = self._score_to_rank(score)
            rationale = self._build_rationale(h, reasons)

            articles = []
            if self._resolver:
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

    def simulate_lifetime_strength(
        self,
        birth_chart: dict,
        annual_charts: dict,
        applied_remedies: list[dict] | None = None,
    ) -> LifetimeStrengthProjection:
        applied_remedies = applied_remedies or []
        shifting_boost = float(self._cfg.get("remedy.shifting_boost", fallback=2.5)) if self._cfg else 2.5
        residual_factor = float(self._cfg.get("remedy.residual_impact_factor", fallback=0.05)) if self._cfg else 0.05
        safe_mult = float(self._cfg.get("remedy.safe_multiplier", fallback=1.0)) if self._cfg else 1.0
        unsafe_mult = float(self._cfg.get("remedy.unsafe_multiplier", fallback=0.5)) if self._cfg else 0.5

        all_ages = sorted(annual_charts.keys())
        result: dict[str, dict] = {}

        for planet in _LEGACY_STANDARD_PLANETS:
            residual = 0.0
            baseline_list: list[float] = []
            remedy_list: list[float] = []
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
                "baseline": baseline_list,
                "remedy": remedy_list,
                "cum_baseline": cum_b_list,
                "cum_remedy": cum_r_list,
            }

        return LifetimeStrengthProjection(ages=all_ages, planets=result)

    def analyze_life_area_potential(
        self,
        birth_chart: dict,
        annual_charts: dict,
        applied_remedies: list[dict] | None = None,
        current_age: int = 1,
    ) -> dict[str, LifeAreaSummary]:
        applied_remedies = applied_remedies or []
        all_ages = sorted(annual_charts.keys())
        relevant_ages = [a for a in all_ages if a >= current_age]

        proj_applied = self.simulate_lifetime_strength(birth_chart, annual_charts, applied_remedies)

        max_remedies: list[dict] = []
        for planet in _LEGACY_STANDARD_PLANETS:
            for age in relevant_ages:
                max_remedies.append({"planet": planet, "age": age, "is_safe": True})
        proj_max = self.simulate_lifetime_strength(birth_chart, annual_charts, max_remedies)

        summaries: dict[str, LifeAreaSummary] = {}
        for area, planets_in_area in _LIFE_AREA_GROUPS.items():
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
                    fixed_fate += p_data_applied["baseline"][i]
                    applied_sum += p_data_applied["remedy"][i]
                    max_sum += p_data_max["remedy"][i]

            current_remediation = applied_sum - fixed_fate
            max_remediable = max_sum - fixed_fate
            untapped_potential = max(0.0, max_remediable - current_remediation)
            denominator = max(max_remediable, 0.1)
            efficiency = (current_remediation / denominator) * 100.0
            efficiency = max(0.0, min(100.0, efficiency))

            summaries[area] = LifeAreaSummary(
                area=area,
                fixed_fate=fixed_fate,
                current_remediation=current_remediation,
                untapped_potential=untapped_potential,
                max_remediable=max_remediable,
                remediation_efficiency=efficiency,
            )

        return summaries

    def generate_remedy_hints(
        self,
        year_options: dict[str, PlanetShiftingResult],
        chart: dict | None = None,
    ) -> list[str]:
        all_opts: list[tuple[str, ShiftingOption]] = []
        for planet, result in year_options.items():
            for opt in result.safe_matches:
                if opt.rank in ("CRITICAL", "High"):
                    all_opts.append((planet, opt))

        kendra_order = {1: 1, 10: 2, 7: 3, 4: 4}

        def sort_key(item):
            planet, opt = item
            k_score = kendra_order.get(opt.house, 99)
            return (-opt.score, k_score, opt.house)

        all_opts.sort(key=sort_key)
        top3_raw = all_opts[:3]

        hints: list[str] = []

        for planet, opt in top3_raw:
            articles_str = (
                ", ".join(opt.articles) if opt.articles else "keep related articles nearby"
            )
            hint = (
                f"Shift {planet} to House {opt.house} [{opt.rank}]: "
                f"{opt.rationale}. Articles: {articles_str}"
            )
            hints.append(hint)

        if chart and "birth_time" in chart:
            try:
                from datetime import datetime
                bt_str = chart["birth_time"]
                dt = datetime.fromisoformat(bt_str.replace("Z", "+00:00"))
                weekday = dt.strftime("%w")
                day_remedies = self._cfg.get("remedy.birth_day_remedies", fallback={}) if self._cfg else {}
                if weekday in day_remedies:
                    hints.append(f"Helpful Remedy: {day_remedies[weekday]}")
            except Exception:
                pass

        if chart and chart.get("mangal_badh_status") == "Active" and self._cfg:
            mars_hints = self._cfg.get("remedy.mangal_badh_hints", fallback=[])
            if mars_hints:
                hints.append(f"Mars Malefic (-): {mars_hints[0]}")

        return hints[:4]

    def get_llm_remedy_summary(
        self,
        birth_chart: dict,
        annual_chart: dict,
        age: int,
    ) -> str:
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
