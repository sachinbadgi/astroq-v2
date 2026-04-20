"""
Detects 15 Lal Kitab grammar conditions and applies their respective strength
modifiers. Updates the `EnrichedPlanet` dicts in-place.

Key components:
  1. Mangal Badh: 17 rules (13 increments + 4 decrements)
  2. Disposition Rules: 16 rules for house-lord interactions
  3. BilMukabil: 3-step logic (friends + sig. aspect + enemy in foundational house)
  4. Sleeping Planet: uses canonical HOUSE_ASPECT_MAP
  5. Mangal Badh divisor: 16.0 (canonical reference)
"""

from __future__ import annotations

import math
from typing import Any

from astroq.lk_prediction.config import ModelConfig


# ---------------------------------------------------------------------------
# Canonical Lal Kitab constants — imported from single source of truth
# ---------------------------------------------------------------------------
from astroq.lk_prediction.lk_constants import (
    PLANET_PAKKA_GHAR as PAKKA_GHAR,
    STANDARD_PLANETS_SET as STANDARD_PLANETS,
    HOUSE_ASPECT_DATA,
    HOUSE_ASPECT_TARGETS as HOUSE_ASPECT_MAP,
    NATURAL_RELATIONSHIPS,
    FOUNDATIONAL_HOUSES,
    PLANET_EXALTATION as EXALTATION_HOUSES,
    PLANET_DEBILITATION as DEBILITATION_HOUSES,
    DISPOSITION_RULES as _DISPOSITION_RULES,
)

# Aspect types considered "significant" in BilMukabil (local-only, not in lk_constants)
SIGNIFICANT_ASPECT_TYPES: frozenset[str] = frozenset({"100 Percent", "50 Percent", "25 Percent"})


class GrammarAnalyser:
    """
    Applies Lal Kitab grammar rules to enriched planets.

    Parameters
    ----------
    config : ModelConfig
        Centralised configuration instance.
    """

    def __init__(self, config: ModelConfig) -> None:
        self._cfg = config
        self._cache_weights()

    def _cache_weights(self) -> None:
        c = self._cfg
        self.w_sleep = c.get("strength.sleeping_planet_factor", fallback=0.0)
        self.w_kaayam = c.get("strength.kaayam_boost", fallback=1.15)
        self.w_dharmi = c.get("strength.dharmi_planet_boost", fallback=1.50)
        self.w_dharmi_kundli = c.get("strength.dharmi_kundli_boost", fallback=1.20)
        self.w_sathi = c.get("strength.sathi_boost_per_companion", fallback=1.00)
        self.w_bilmukabil = c.get("strength.bilmukabil_penalty_per_hostile", fallback=1.50)
        # FIX: divisor should be 16.0 to match reference formula
        self.w_mangal = c.get("strength.mangal_badh_divisor", fallback=16.0)
        self.w_masnui = c.get("strength.masnui_parent_feedback", fallback=0.30)
        self.w_dhoka = c.get("strength.dhoka_graha_factor", fallback=0.70)
        self.w_achanak = c.get("strength.achanak_chot_penalty", fallback=2.00)
        self.w_rin = c.get("strength.rin_penalty_factor", fallback=0.85)
        self.w_35yr = c.get("strength.cycle_35yr_boost", fallback=1.25)
        self.w_spoiler = c.get("strength.spoiler_factor", fallback=0.50)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def apply_grammar_rules(
        self, chart: dict[str, Any], enriched: dict[str, Any]
    ) -> None:
        """
        Run the grammar detection and adjustment pipeline.  Mutates *enriched* in-place.
        """
        if not enriched:
            return

        planets_data = chart.get("planets_in_houses", {})
        house_status = chart.get("house_status", {})
        chart_type = chart.get("chart_type", "Birth")
        chart_period = chart.get("chart_period", 0)

        # ── Phase 1: Run all detectors ─────────────────────────────────
        chart["masnui_grahas_formed"] = self.detect_masnui(chart)
        chart["dhoka_graha_triggers"] = self.detect_dhoka(chart)
        chart["achanak_chot_triggers"] = self.detect_achanak_chot_triggers(chart)
        chart["lal_kitab_debts"] = self.detect_rin(chart)
        chart["lal_kitab_dispositions"] = self.detect_dispositions(chart)
        chart["dharmi_kundli_status"] = "Dharmi Teva" if self.detect_dharmi_kundli(chart) else "Normal"
        mangal_badh_counter = self.detect_mangal_badh(chart)
        chart["mangal_badh_status"] = "Active" if mangal_badh_counter > 0 else "Inactive"
        chart["mangal_badh_count"] = mangal_badh_counter
        chart["andhi_kundli_status"] = self.detect_andhi_kundli(chart)

        # Note: Masnui integration is handled in Phase 5 via _integrate_masnui()
        # to ensure correct strength (canonical 5.0) and aspects are applied
        # AFTER per-planet adjustments, not before.

        dharmi_kundli = chart.get("dharmi_kundli_status") == "Dharmi Teva"
        mangal_badh_active = chart.get("mangal_badh_status") == "Active"

        masnui_parents: set[str] = set()
        for m in chart.get("masnui_grahas_formed", []):
            masnui_parents.update(m.get("components", []))

        dhoka_grahas = {d.get("planet") for d in chart.get("dhoka_graha_triggers", [])}
        achanak_targets: set[str] = set()
        for a in chart.get("achanak_chot_triggers", []):
            achanak_targets.update(a.get("planets", []))

        rin_list = chart.get("lal_kitab_debts", [])
        # Build per-planet rin map: each debt type is assigned to the triggering planet
        per_planet_rin = self._build_per_planet_rin(planets_data, rin_list)
        disposition_list = chart.get("lal_kitab_dispositions", [])

        ruler_name = self._get_35_year_ruler(chart_period) if chart_type == "Yearly" else None
        if ruler_name:
            chart["35_year_cycle_ruler"] = ruler_name
            # Note: intermediary_ruler is currently not yielded by this engine method
            ruler_35 = ruler_name
        else:
            ruler_35 = None

        # ── Phase 2: Disposition detection only (no strength yet) ──────
        # Strength application happens inside _apply_adjustments AFTER sleeping

        # ── Phase 3: Per-planet flag assignment ────────────────────────
        for planet, ep in enriched.items():
            pd = planets_data.get(planet, {})
            self._init_grammar_fields(ep)

            # Sleeping: check Sleeping House FIRST (explicit override), then aspect-map detection
            if house_status.get(str(ep["house"])) == "Sleeping House":
                ep["sleeping_status"] = "Sleeping House"
            elif pd.get("sleeping_status", ""):
                # Upstream pre-computed status takes priority over detection
                ep["sleeping_status"] = pd.get("sleeping_status")
            elif self.detect_sleeping(planet, planets_data):
                ep["sleeping_status"] = "Sleeping Planet"

            # Nikami (Inert)
            if self.detect_nikami(planet, chart):
                ep["is_nikami"] = True

            # Kaayam
            states = pd.get("states", [])
            if "Kaayam" in states or self.detect_kaayam(planet, enriched):
                ep["kaayam_status"] = "Kaayam"

            # Dharmi — Kundli-level (Dharmi Teva) takes highest priority
            if dharmi_kundli:
                ep["dharmi_status"] = "Dharmi Teva"
            elif pd.get("dharmi_status"):
                ep["dharmi_status"] = pd.get("dharmi_status")
            else:
                dharmi_val = self.detect_dharmi(planet, planets_data)
                if dharmi_val:
                    ep["dharmi_status"] = dharmi_val

            # Sathi & BilMukabil
            self._find_companions_and_hostiles(planet, ep, planets_data)

            # Aspects (for UI rendering)
            self._find_aspects(planet, ep, planets_data)

            # Masnui, Dhoka, Achanak, Rin
            ep["is_masnui"] = planet.lower().startswith("artificial") or pd.get("is_masnui", False)
            ep["is_masnui_parent"] = planet in masnui_parents
            ep["dhoka_graha"] = planet in dhoka_grahas
            ep["achanak_chot_active"] = planet in achanak_targets
            # Assign rin debts per-planet (the triggering planet carries the debt)
            ep["rin_debts"] = per_planet_rin.get(planet, [])

            # Dispositions (informational; strength already applied above)
            ep["dispositions_active"] = [
                d for d in disposition_list if planet in d.get("affected_planets", [])
            ]

        # Phase 4: Structural Classification (Nagrik/Nashtik)
        self.apply_structural_classification(chart)

        # ── Phase 4: Apply per-planet strength adjustments ─────────────
        # Pass causer side-table so dispositions can be applied after sleeping
        causer_strengths: dict[str, float] = {}
        for p, ep in enriched.items():
            # Snapshot raw_aspect_strength as causer base (pre-adjustment)
            causer_strengths[p] = float(ep.get("raw_aspect_strength",
                                                ep.get("strength_total", 0.0)))

        for planet, ep in enriched.items():
            self._apply_adjustments(
                planet, ep, mangal_badh_active, ruler_35, mangal_badh_counter,
                planets_data, causer_strengths
            )

        # ── Phase 5: Masnui Formation & Feedback ───────────────────────
        self._integrate_masnui(chart, enriched)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _init_grammar_fields(self, ep: dict[str, Any]) -> None:
        ep.setdefault("sleeping_status", "")
        ep.setdefault("kaayam_status", "")
        ep.setdefault("dharmi_status", "")
        ep.setdefault("is_nikami", False)
        ep.setdefault("sathi_companions", [])
        ep.setdefault("bilmukabil_hostile_to", [])
        ep.setdefault("is_masnui", False)
        ep.setdefault("is_masnui_parent", False)
        ep.setdefault("dhoka_graha", False)
        ep.setdefault("achanak_chot_active", False)
        ep.setdefault("rin_debts", [])
        ep.setdefault("dispositions_active", [])

        bd = ep.setdefault("strength_breakdown", {})
        for key in [
            "sleeping", "kaayam", "disposition", "dharmi", "sathi", "bilmukabil",
            "mangal_badh", "masnui_feedback", "dhoka", "achanak_chot", "rin", "cycle_35yr",
            "spoiler"
        ]:
            bd.setdefault(key, 0.0)

    def _build_per_planet_rin(
        self, planets_data: dict[str, Any], rin_list: list[dict[str, Any]]
    ) -> dict[str, list[str]]:
        """
        Distribute rin debts to the specific planet(s) that triggered the rule.
        Returns {planet_name: [debt_name, ...]} mapping.
        """
        per_planet: dict[str, list[str]] = {}
        active_names = {d["debt_name"] for d in rin_list if d.get("active")}

        def h(p: str) -> int | None:
            return planets_data.get(p, {}).get("house")

        rin_rules = [
            ("Ancestral Debt (Pitra Rin)",             ["Venus", "Mercury", "Rahu"], [2, 5, 9, 12]),
            ("Self Debt (Swayam Rin)",                  ["Venus", "Rahu"],            [5]),
            ("Maternal Debt (Matri Rin)",               ["Ketu"],                     [4]),
            ("Family/Wife/Woman Debt (Stri Rin)",       ["Sun", "Rahu", "Ketu"],      [2, 7]),
            ("Relative/Brother Debt (Bhai-Bandhu Rin)", ["Mercury", "Ketu"],          [1, 8]),
            ("Daughter/Sister Debt (Behen/Beti Rin)",   ["Moon"],                     [3, 6]),
            ("Oppression/Atrocious Debt (Zulm Rin)",    ["Sun", "Moon", "Mars"],      [10, 11]),
            ("Debt of the Unborn (Ajanma Rin)",         ["Venus", "Sun", "Rahu"],     [12]),
            ("Negative Speech Debt (Manda Bol Rin)",    ["Moon", "Mars", "Ketu"],     [6]),
        ]
        for name, plist, hlist in rin_rules:
            if name not in active_names:
                continue
            for p in plist:
                if h(p) in hlist:
                    per_planet.setdefault(p, []).append(name)
        return per_planet



    def _apply_disposition_strength(
        self, planets_data: dict[str, Any], enriched: dict[str, Any]
    ) -> None:
        """
        Apply all 16 disposition rules.  The causer planet's absolute strength is
        added (Good) or subtracted (Bad) from the affected planet's strength_total.
        This happens BEFORE per-planet adjustments (including Mangal Badh).
        """
        for causer, causer_houses, affected, effect in _DISPOSITION_RULES:
            causer_data = planets_data.get(causer)
            if causer_data is None:
                continue
            causer_h = causer_data.get("house")
            if causer_h not in causer_houses:
                continue
            if affected not in enriched:
                continue

            causer_ep = enriched.get(causer)
            causer_strength = abs(float(causer_ep["strength_total"])) if causer_ep else 0.0

            if causer_strength == 0.0:
                continue

            delta = causer_strength if effect == "Good" else -causer_strength
            enriched[affected]["strength_total"] = (
                float(enriched[affected].get("strength_total", 0.0)) + delta
            )
            # Track in breakdown
            enriched[affected].setdefault("strength_breakdown", {})
            enriched[affected]["strength_breakdown"].setdefault("disposition", 0.0)
            enriched[affected]["strength_breakdown"]["disposition"] += delta

    def _find_companions_and_hostiles(
        self, planet: str, ep: dict[str, Any], planets_data: dict[str, Any]
    ) -> None:
        house = ep["house"]
        pd = planets_data.get(planet, {})

        # Sathi: same house co-tenants
        for other, opd in planets_data.items():
            if other != planet and opd.get("house") == house:
                ep["sathi_companions"].append(other)

        # BilMukabil:friends but enemy in foundational house
        for other in planets_data:
            if other == planet:
                continue
            if self.detect_bilmukabil(planet, other, planets_data):
                if other not in ep["bilmukabil_hostile_to"]:
                    ep["bilmukabil_hostile_to"].append(other)

    def _find_aspects(self, planet: str, ep: dict[str, Any], planets_data: dict[str, Any]) -> None:
        """Find all planets aspected by the current planet using HOUSE_ASPECT_DATA."""
        base_planet = self._normalize_planet_name(planet)
        if base_planet not in STANDARD_PLANETS:
            return

        house = ep.get("house")
        if not house:
            return
        
        aspect_config = HOUSE_ASPECT_DATA.get(house, {})
        ep["aspects"] = []
        
        for aspect_type, target_val in aspect_config.items():
            # target_val can be int or list[int]
            target_houses = [target_val] if isinstance(target_val, int) else (target_val if isinstance(target_val, list) else [])
            
            for h in target_houses:
                # Who is in house h?
                for other, opd in planets_data.items():
                    if other == planet:
                        continue
                        
                    # Consider both standard and masnui planets as aspect targets
                    base_other = self._normalize_planet_name(other)
                    if (base_other in STANDARD_PLANETS or opd.get("is_masnui")) and opd.get("house") == h:
                        rel = self._get_relationship(planet, other)
                        ep["aspects"].append({
                            "target": other,
                            "target_house": h,
                            "relationship": rel,
                            "aspect_type": aspect_type
                        })

    def _get_relationship(self, p1: str, p2: str) -> str:
        """Return 'friend', 'enemy', or 'neutral' based on NATURAL_RELATIONSHIPS."""
        base_p1 = self._normalize_planet_name(p1)
        base_p2 = self._normalize_planet_name(p2)
        
        # Only handle standard planets for relationships
        if base_p1 not in STANDARD_PLANETS or base_p2 not in STANDARD_PLANETS:
            return "neutral"
            
        rels = NATURAL_RELATIONSHIPS.get(base_p1, {})
        if base_p2 in rels.get("Friends", []): return "friend"
        if base_p2 in rels.get("Enemies", []): return "enemy"
        return "neutral"

    def _normalize_planet_name(self, name: str) -> str:
        """Map 'Artificial Jupiter' -> 'Jupiter'."""
        if name in STANDARD_PLANETS:
            return name
        for p in STANDARD_PLANETS:
            if p.lower() in name.lower():
                return p
        return name

    def _integrate_masnui(self, chart: dict, enriched: dict) -> None:
        """Inject Masnui virtual planets into enriched data and compute their aspects."""
        masnuis = chart.get("masnui_grahas_formed", [])
        if not masnuis:
            return

        planets_data = chart.setdefault("planets_in_houses", {})
        
        for m in masnuis:
            name = m["masnui_graha_name"]
            # Ensure unique name
            v_name = name.replace("Artificial", "Masnui")
            if v_name in enriched:
                v_name = f"{v_name} (Formed)"
                
            house = m["formed_in_house"]
            
            # 1. Create virtual entry in planets_data for others to see
            planets_data[v_name] = {
                "house": house,
                "is_masnui": True,
                "formed_by": m.get("components", []),
            }
            
            # 2. Create enriched entry
            # Base Masnui strength is typically high (like 100% or based on parents)
            # We use a default of 5.0 (similar to exalted) or sum of parents?
            # Lal Kitab says masnui is 'active' and 'strong'.
            ep = {"house": house, "strength_total": 5.0, "is_masnui": True}
            self._init_grammar_fields(ep)
            enriched[v_name] = ep
            
            # 3. Compute aspects FOR this Masnui
            self._find_aspects(v_name, ep, planets_data)
            
            # 4. Update aspects OF other planets to include this Masnui
            for other_p, other_ep in enriched.items():
                if other_p == v_name: continue
                self._find_aspects(other_p, other_ep, planets_data)

            # 5. Feedback strength back to parents
            feedback_factor = self._cfg.get("strength.masnui_parent_feedback", fallback=0.30)
            components = m.get("components", [])
            for comp in components:
                    # Provide feedback boost to parents
                    boost = float(ep["strength_total"]) * feedback_factor
                    enriched[comp]["strength_total"] += boost
                    # Update breakdown for summation consistency
                    enriched[comp].setdefault("strength_breakdown", {})
                    enriched[comp]["strength_breakdown"]["masnui_feedback"] = (
                        enriched[comp]["strength_breakdown"].get("masnui_feedback", 0.0) + boost
                    )
                    # Mark it in states for transparency
                    if "states" not in enriched[comp]: enriched[comp]["states"] = []
                    enriched[comp]["states"].append(f"Masnui Feedback (+{boost:.1f})")

    def _apply_adjustments(
        self,
        planet: str,
        ep: dict[str, Any],
        mangal_active: bool,
        ruler_35: str | None,
        mangal_counter: int = 0,
        planets_data: dict[str, Any] | None = None,
        causer_strengths: dict[str, float] | None = None,
    ) -> None:
        total = float(ep.get("strength_total", 0.0))
        bd = ep["strength_breakdown"]
        is_sleeping = bool(ep.get("sleeping_status"))

        # 1. Sleeping (zeroes out base strength — must come first per Lal Kitab canon)
        #    A sleeping planet cannot simultaneously be Kaayam or Dharmi.
        if is_sleeping:
            delta = total * self.w_sleep - total
            bd["sleeping"] += delta
            total += delta

        # 2. Disposition rules (external causer effects, applied before intrinsic boosts)
        #    This ensures external planetary harm/help registers on the base value.
        if planets_data and causer_strengths:
            for causer, causer_houses, affected, effect in _DISPOSITION_RULES:
                if affected != planet:
                    continue
                causer_data = planets_data.get(causer)
                if causer_data is None:
                    continue
                if causer_data.get("house") not in causer_houses:
                    continue
                adj = abs(causer_strengths.get(causer, 0.0))
                if adj == 0.0:
                    continue
                delta = adj if effect == "Good" else -adj
                bd["disposition"] += delta
                total += delta

        # 3. Kaayam (powerful established state — only applies if not sleeping)
        if not is_sleeping and ep["kaayam_status"] == "Kaayam":
            delta = abs(total) * (self.w_kaayam - 1.0)
            bd["kaayam"] += delta
            total += delta

        # 4. Dharmi (pious/protected state — applies regardless of sleeping state)
        #    Per canonical Lal Kitab: Dharmi status is divine protection that
        #    transcends the mechanical sleeping condition. A sleeping Dharmi planet's
        #    protection is computed from its raw natal strength, not the zeroed total.
        if ep["dharmi_status"]:
            boost = self.w_dharmi_kundli if ep["dharmi_status"] == "Dharmi Teva" else self.w_dharmi
            # Use raw base for sleeping planets (their total is 0 after sleeping)
            dharmi_base = float(ep.get("raw_aspect_strength", 0.0)) if is_sleeping and total == 0.0 else abs(total)
            delta = dharmi_base * (boost - 1.0)
            bd["dharmi"] += delta
            total += delta

        # 5. Sathi
        if ep["sathi_companions"]:
            delta = len(ep["sathi_companions"]) * self.w_sathi
            bd["sathi"] += delta
            total += delta

        # 6. BilMukabil
        if ep["bilmukabil_hostile_to"]:
            delta = -abs(total) * (1.0 - (1.0 / self.w_bilmukabil))
            bd["bilmukabil"] += delta
            total += delta

        # 7. Mangal Badh — formula per canonical 17-rule Goswami spec.
        #    The formula defines the TARGET final value for Mars:
        #      mars_final = initial_strength - initial_strength * (1 + counter / divisor)
        #                 = - initial_strength * counter / divisor
        #    The delta brings the running total TO this target.
        if mangal_active and planet == "Mars":
            mars_base = abs(float(ep.get("raw_aspect_strength", abs(total))))
            counter = max(0, mangal_counter)
            target_final = mars_base - mars_base * (1.0 + counter / self.w_mangal)
            delta = target_final - total
            bd["mangal_badh"] += delta
            total = target_final

        # Note: Masnui parent feedback is applied separately in Phase 5 (_integrate_masnui),
        # not here, to avoid double-counting. The virtual Masnui planet must exist first
        # (with its canonical strength_total=5.0) before feedback is distributed.

        # 9. Dhoka
        if ep["dhoka_graha"]:
            delta = -abs(total) * (1.0 - self.w_dhoka)
            bd["dhoka"] += delta
            total += delta

        # 10. Achanak Chot
        if ep["achanak_chot_active"]:
            delta = -self.w_achanak
            bd["achanak_chot"] += delta
            total += delta

        # 11. Rin
        if ep.get("rin_debts"):
            delta = -abs(total) * (1.0 - self.w_rin)
            bd["rin"] += delta
            total += delta

        # 12. 35 Year Cycle
        if ruler_35 == planet:
            delta = abs(total) * (self.w_35yr - 1.0)
            bd["cycle_35yr"] += delta
            total += delta

        ep["strength_total"] = total



    # ------------------------------------------------------------------
    # Public detectors
    # ------------------------------------------------------------------

    def detect_sleeping(self, planet: str, planets: dict) -> bool:
        """
        Sleeping if planet is NOT in its Pakka Ghar AND neither casts nor receives
        a significant aspect (using canonical HOUSE_ASPECT_MAP).
        """
        p_data = planets.get(planet)
        if not p_data:
            return False

        planet_house = p_data.get("house")
        if not planet_house:
            return False

        # Never sleeping if in pakka ghar
        if planet_house == PAKKA_GHAR.get(planet):
            return False

        # 1. Does it CAST an aspect on any occupied house?
        aspected_houses = HOUSE_ASPECT_MAP.get(planet_house, [])
        for house in aspected_houses:
            occupied = [p for p, d in planets.items() if p != planet and d.get("house") == house]
            if occupied:
                return False  # Awake (Casting)

        # 2. Does it RECEIVE a significant aspect from any occupied house?
        for other_p, other_data in planets.items():
            if other_p == planet: continue
            other_house = other_data.get("house")
            if not other_house: continue
            
            # If the other planet hits our house via a significant aspect
            if planet_house in HOUSE_ASPECT_MAP.get(other_house, []):
                return False # Awake (Receiving)

        return True # Neither casts nor receives significant hits

    def detect_kaayam(self, planet: str, planets: dict) -> bool:
        """Kaayam if base strength > 0 and NO enemy/equal aspects received."""
        p_data = planets.get(planet)
        if not p_data:
            return False

        # If it has some positive base strength, it's a candidate for stability
        if p_data.get("strength_total", 0.0) <= 0.0:
            return False

        target_house = p_data.get("house")
        for caster, c_data in planets.items():
            if caster == planet:
                continue
            
            # Use canonical HOUSE_ASPECT_DATA to check if caster hits target_house
            caster_house = c_data.get("house")
            if not caster_house: continue
            
            aspects_from_caster = HOUSE_ASPECT_DATA.get(caster_house, {})
            is_hitting = False
            for target_houses in aspects_from_caster.values():
                t_list = [target_houses] if isinstance(target_houses, int) else target_houses
                if target_house in t_list:
                    is_hitting = True
                    break
            
            if is_hitting:
                # Is caster an enemy or equal?
                rel = self._get_relationship(caster, planet)
                if rel in ("enemy", "equal"):
                    return False
        return True

    def detect_dharmi_kundli(self, chart: dict) -> bool:
        """
        Dharmi Teva (Kundli-level): Saturn and Jupiter are conjunct in the same house.
        This is the highest dharmi state, elevating all planets in the chart.
        Individual planet dharmi (e.g. Jupiter in H4, Saturn in H11) is handled by detect_dharmi().
        """
        planets = chart.get("planets_in_houses", {})
        sat = planets.get("Saturn", {}).get("house")
        jup = planets.get("Jupiter", {}).get("house")
        return bool(sat and jup and sat == jup)

    def detect_dharmi(self, planet: str, planets: dict) -> str:
        """
        Dharmi (Pious/Protected) detection per canonical Lal Kitab rules.
        Returns a specific dharmi label describing the condition, or '' if none.
        """
        p_data = planets.get(planet)
        if not p_data: return ""

        house = p_data.get("house")
        if not house: return ""

        # 1. Rahu in H4
        if planet == "Rahu" and house == 4:
            return "Dharmi Rahu (Poison Neutralized)"

        # 2. Saturn in H11
        if planet == "Saturn" and house == 11:
            return "Dharmi Saturn (Watchdog)"

        # 3. Conjunction Jupiter + Saturn (individual planet label for the conjunct case)
        if planet in ["Jupiter", "Saturn"]:
            other = "Saturn" if planet == "Jupiter" else "Jupiter"
            if planets.get(other, {}).get("house") == house:
                return "Dharmi Conjunction (Jup+Sat)"

        # 4. Standard Jupiter (Not in H10)
        if planet == "Jupiter" and house != 10:
            return "Dharmi Jupiter"

        return ""

    def apply_structural_classification(self, chart: dict):
        """Tags chart as Nagrik (H1-H6 focus) or Nashtik (H7-H12 focus)."""
        pih = chart.get("planets_in_houses", {})
        occupied_houses = {d.get("house") for d in pih.values() if d.get("house")}
        
        upper_half = {1, 2, 3, 4, 5, 6}
        lower_half = {7, 8, 9, 10, 11, 12}
        
        if occupied_houses and occupied_houses.issubset(upper_half):
            chart["structural_type"] = "Nagrik (Active/Self)"
        elif occupied_houses and occupied_houses.issubset(lower_half):
            chart["structural_type"] = "Nashtik (Passive/Social)"
        else:
            chart["structural_type"] = "Mixed"

    def detect_nikami(self, planet: str, chart: dict) -> bool:
        """
        Nikami (Inert) if in an enemy house AND 7th house (opposition) is empty.
        Source: Lal Kitab 1952.
        """
        pih = chart.get("planets_in_houses", {})
        p_data = pih.get(planet)
        if not p_data: return False
        
        house = p_data.get("house")
        if not house: return False
        
        # 1. Is it in an enemy house? (Pakka Lord of that house is an enemy)
        from .lk_constants import PLANET_PAKKA_GHAR, ENEMIES
        
        # Find who owns this house
        house_owner = None
        for p, h in PLANET_PAKKA_GHAR.items():
            if h == house:
                house_owner = p
                break
        
        if not house_owner: return False
        
        is_enemy_house = house_owner in ENEMIES.get(planet, [])
        if not is_enemy_house: return False
        
        # 2. Is 7th house from this planet empty?
        opposition_house = (house + 6 - 1) % 12 + 1
        
        # Check if anyone is in opposition house
        is_opposition_empty = True
        for p, data in pih.items():
            if data.get("house") == opposition_house:
                is_opposition_empty = False
                break
        
        return is_opposition_empty

    def detect_sathi(self, p1: str, p2: str, planets: dict) -> bool:
        """Sathi if mutual exchange of houses (Exaltation/Debilitation/Pakka)."""
        p1_h = planets.get(p1, {}).get("house")
        p2_h = planets.get(p2, {}).get("house")

        def _exchange_houses(p: str) -> set[int]:
            houses: set[int] = set()
            ex = EXALTATION_HOUSES.get(p)
            deb = DEBILITATION_HOUSES.get(p)
            pak = PAKKA_GHAR.get(p)
            if ex is not None:
                houses.update([ex] if isinstance(ex, int) else ex)
            if deb is not None:
                houses.update([deb] if isinstance(deb, int) else deb)
            if pak is not None:
                houses.add(pak)
            return houses

        return p2_h in _exchange_houses(p1) and p1_h in _exchange_houses(p2)

    def detect_bilmukabil(self, p1: str, p2: str, planets: dict) -> bool:
        """
        BilMukabil requires ALL THREE conditions:
        1. p1 and p2 are natural friends.
        2. Either casts a significant aspect (100%, 50%, 25%) on the other.
        3. An enemy of either is in a foundational house of the other.
        """
        # Step 1: Natural friends
        if p2 not in NATURAL_RELATIONSHIPS.get(p1, {}).get("Friends", []):
            return False

        # Step 2: Significant mutual aspect
        d1 = planets.get(p1, {})
        d2 = planets.get(p2, {})

        p1_aspects_p2 = any(
            a.get("aspecting_planet") == p2 and a.get("aspect_type") in SIGNIFICANT_ASPECT_TYPES
            for a in d1.get("aspects", [])
        )
        p2_aspects_p1 = any(
            a.get("aspecting_planet") == p1 and a.get("aspect_type") in SIGNIFICANT_ASPECT_TYPES
            for a in d2.get("aspects", [])
        )
        if not (p1_aspects_p2 or p2_aspects_p1):
            return False

        # Step 3: Enemy of either in foundational house of the other
        enemies_p1 = NATURAL_RELATIONSHIPS.get(p1, {}).get("Enemies", [])
        enemies_p2 = NATURAL_RELATIONSHIPS.get(p2, {}).get("Enemies", [])
        foundational_p1 = FOUNDATIONAL_HOUSES.get(p1, [])
        foundational_p2 = FOUNDATIONAL_HOUSES.get(p2, [])

        for enemy in enemies_p1:
            if enemy in planets and planets[enemy].get("house") in foundational_p2:
                return True
        for enemy in enemies_p2:
            if enemy in planets and planets[enemy].get("house") in foundational_p1:
                return True

        return False

    def detect_mangal_badh(self, chart: dict) -> int:
        """
        Complete 17-rule Mangal Badh counter (13 increments, 4 decrements).
        Source: Mars_special_rules.py → calculate_mangal_badh()
        """
        planets = chart.get("planets_in_houses", {})
        if "Mars" not in planets:
            return 0

        def h(p: str) -> int | None:
            return planets.get(p, {}).get("house")

        def conjunct(pa: str, pb: str) -> bool:
            ha, hb = h(pa), h(pb)
            return bool(ha and hb and ha == hb)

        def in_house(p: str, house: int) -> bool:
            return h(p) == house

        def in_houses(p: str, houses: list[int]) -> bool:
            return h(p) in houses

        def aspects(planet_a: str, planet_b: str) -> bool:
            """Uses canonical HOUSE_ASPECT_MAP to check if planet_a aspects planet_b's house."""
            ha, hb = h(planet_a), h(planet_b)
            if not ha or not hb:
                return False
            return hb in HOUSE_ASPECT_MAP.get(ha, [])

        counter = 0

        # ── Increment rules ───────────────────────────────────────────
        # R1: Sun+Saturn conjunct
        if conjunct("Sun", "Saturn"):
            counter += 1
        # R2: Sun exists and does NOT aspect Mars
        if h("Sun") and not aspects("Sun", "Mars"):
            counter += 1
        # R3: Moon exists and does NOT aspect Mars
        if h("Moon") and not aspects("Moon", "Mars"):
            counter += 1
        # R4: Mercury in H6 AND Ketu in H6
        if in_house("Mercury", 6) and in_house("Ketu", 6):
            counter += 1
        # R5: Mars+Mercury conjunct OR Mars+Ketu conjunct
        if conjunct("Mars", "Mercury") or conjunct("Mars", "Ketu"):
            counter += 1
        # R6: Ketu in H1
        if in_house("Ketu", 1):
            counter += 1
        # R7: Ketu in H8
        if in_house("Ketu", 8):
            counter += 1
        # R8: Mars in H3
        if in_house("Mars", 3):
            counter += 1
        # R9: Venus in H9
        if in_house("Venus", 9):
            counter += 1
        # R10: Sun in H6/H7/H10/H12
        if in_houses("Sun", [6, 7, 10, 12]):
            counter += 1
        # R11: Mars in H6
        if in_house("Mars", 6):
            counter += 1
        # R12: Mercury in H1/H3/H8
        if in_houses("Mercury", [1, 3, 8]):
            counter += 1
        # R13: Rahu in H5/H9
        if in_houses("Rahu", [5, 9]):
            counter += 1

        # ── Decrement rules ───────────────────────────────────────────
        # D1: Sun+Mercury conjunct
        if conjunct("Sun", "Mercury"):
            counter -= 1
        # D2: Mars in H8 AND Mercury in H8
        if in_house("Mars", 8) and in_house("Mercury", 8):
            counter -= 1
        # D3: Sun in H3 AND Mercury in H3
        if in_house("Sun", 3) and in_house("Mercury", 3):
            counter -= 1
        # D4: Moon in H1/H2/H3/H4/H8/H9
        if in_houses("Moon", [1, 2, 3, 4, 8, 9]):
            counter -= 1

        return max(0, counter)

    def detect_masnui(self, chart: dict) -> list[dict]:
        """Detect Masnui (Artificial) planets formed by specific conjunctions."""
        res = []
        planets_data = chart.get("planets_in_houses", {})
        if not planets_data:
            return res

        house_occupants: dict[int, set[str]] = {i: set() for i in range(1, 13)}
        for p_name, p_info in planets_data.items():
            h = p_info.get("house")
            if h and 1 <= h <= 12:
                house_occupants[h].add(p_name.lower())

        rules = [
            ({"sun", "venus"},   "Artificial Jupiter"),
            ({"mercury", "venus"}, "Artificial Sun"),
            ({"sun", "jupiter"}, "Artificial Moon"),
            ({"rahu", "ketu"},   "Artificial Venus (Note: Unusual Conjunction)"),
            ({"sun", "mercury"}, "Artificial Mars (Auspicious)"),
            ({"sun", "saturn"},  "Artificial Mars (Malefic)"),
            ({"sun", "saturn"},  "Artificial Rahu (Debilitated Rahu)"),
            ({"jupiter", "rahu"}, "Artificial Mercury"),
            ({"venus", "jupiter"}, "Artificial Saturn (Like Ketu)"),
            ({"mars", "mercury"}, "Artificial Saturn (Like Rahu)"),
            ({"saturn", "mars"}, "Artificial Rahu (Exalted Rahu)"),
            ({"venus", "saturn"}, "Artificial Ketu (Exalted Ketu)"),
            ({"moon", "saturn"}, "Artificial Ketu (Debilitated Ketu)"),
        ]

        # Build a reverse map: lowercase planet name → title-case chart key
        actual_name_map = {p.lower(): p for p in planets_data}

        for h_num, occupants_lc in house_occupants.items():
            if not occupants_lc:
                continue
            for required_set, result_name in rules:
                if required_set.issubset(occupants_lc):
                    # Map lowercase back to actual planet names in the chart
                    components = [actual_name_map.get(p, p.capitalize()) for p in occupants_lc]
                    res.append({
                        "formed_in_house": h_num,
                        "masnui_graha_name": result_name,
                        "components": components,
                    })
        return res

    def detect_dhoka(self, chart: dict) -> list[dict]:
        """Detect Dhoka Graha (Planet of Deceit) based on 4 types of triggers."""
        res = []
        planets = chart.get("planets_in_houses", {})
        if not planets:
            return res

        c_type = chart.get("chart_type", "Birth")

        def get_in_house(h_num: int) -> str | None:
            in_h = [p for p, d in planets.items() if d.get("house") == h_num]
            return in_h[0] if len(in_h) == 1 else None

        # Type 2: Birth H10 Planet
        if c_type == "Birth":
            h10_planet = get_in_house(10)
            if h10_planet:
                res.append({"type": 2, "planet": h10_planet, "effect": "Birth H10 Dhoka"})

        elif c_type == "Yearly":
            age = chart.get("chart_period", 0)
            h8_ref = get_in_house(8) or "Mars"
            h9_ref = get_in_house(9) or "Jupiter"
            h12_ref = get_in_house(12) or "Jupiter"
            base_sequence = [
                "Sun", "Moon", "Ketu", "Mars", "Mercury", "Saturn",
                "Rahu", h8_ref, h9_ref, "Jupiter", "Venus", h12_ref,
            ]
            if age > 0:
                col_index = (age - 1) % 12
                res.append({"type": 1, "planet": base_sequence[col_index], "effect": "Age Sequence"})

            h10_annuals = [p for p, d in planets.items() if d.get("house") == 10]
            for p in h10_annuals:
                h8_occ = any(d.get("house") == 8 for d in planets.values())
                effect = "Manda" if h8_occ else "Umda"
                res.append({"type": 4, "planet": p, "effect": effect})

            mock_birth = chart.get("_mock_birth_chart", chart)
            b_planets = mock_birth.get("planets_in_houses", {})
            birth_pairs = {2: 11, 5: 2, 3: 12, 4: 1}

            for p_A in h10_annuals:
                birth_h = b_planets.get(p_A, {}).get("house")
                if birth_h in birth_pairs:
                    target_h = birth_pairs[birth_h]
                    targets = [p_B for p_B, d in b_planets.items() if d.get("house") == target_h]
                    for p_B in targets:
                        res.append({"type": 3, "giver": p_A, "receiver": p_B, "effect": "Dhoka Trigger"})

        return res

    def detect_achanak_chot_triggers(self, chart: dict) -> list[dict]:
        """Detect Achanak Chot (Sudden Strike) based on house pairs and annual aspects."""
        res = []
        if chart.get("chart_type") != "Yearly":
            return res

        mock_birth = chart.get("_mock_birth_chart", chart)
        b_planets = mock_birth.get("planets_in_houses", {})
        a_planets = chart.get("planets_in_houses", {})

        pairs = [{1, 3}, {2, 4}, {4, 6}, {5, 7}, {7, 9}, {8, 10}, {10, 12}, {1, 11}]
        sig_aspects = {"100 Percent", "50 Percent", "25 Percent"}

        potentials = []
        b_names = list(b_planets.keys())
        for i in range(len(b_names)):
            for j in range(i + 1, len(b_names)):
                p1, p2 = b_names[i], b_names[j]
                h1 = b_planets[p1].get("house")
                h2 = b_planets[p2].get("house")
                if h1 and h2 and h1 != h2 and {h1, h2} in pairs:
                    potentials.append((p1, p2, h1, h2))

        for p1, p2, h1, h2 in potentials:
            p1_annual_house = a_planets.get(p1, {}).get("house")
            p2_annual_house = a_planets.get(p2, {}).get("house")
            if not p1_annual_house or not p2_annual_house:
                continue

            def has_sig_aspect(from_house: int, to_house: int) -> bool:
                """Check if from_house has a significant aspect (100%/50%/25%) to to_house."""
                h_data = HOUSE_ASPECT_DATA.get(from_house, {})
                for asp_type, asp_target in h_data.items():
                    if asp_type not in sig_aspects:
                        continue
                    targets = [asp_target] if isinstance(asp_target, int) else (asp_target if isinstance(asp_target, list) else [])
                    if to_house in targets:
                        return True
                return False

            def has_explicit_aspect(planet_a: str, planet_b: str) -> bool:
                """Check pre-injected aspect list (upstream data). Supports both key schemas."""
                for asp in a_planets.get(planet_a, {}).get("aspects", []):
                    target = asp.get("aspecting_planet") or asp.get("target", "")
                    if target == planet_b and asp.get("aspect_type") in sig_aspects:
                        return True
                return False

            triggered = (
                has_sig_aspect(p1_annual_house, p2_annual_house) or
                has_sig_aspect(p2_annual_house, p1_annual_house) or
                has_explicit_aspect(p1, p2) or
                has_explicit_aspect(p2, p1)
            )
            if triggered:
                res.append({"planets": [p1, p2], "birth_chart_houses": [h1, h2]})

        return res

    def detect_rin(self, chart: dict) -> list[dict[str, Any]]:
        """Detect 9 standard Lal Kitab Debts (Rin) based on planet-house occupancy."""
        res = []
        planets = chart.get("planets_in_houses", {})
        if not planets:
            return res

        def get_triggering_houses(plist: list[str], hlist: list[int]) -> list[int]:
            triggers = []
            for p in plist:
                house = planets.get(p, {}).get("house")
                if house in hlist:
                    triggers.append(house)
            return sorted(list(set(triggers)))

        rin_rules = [
            ("Ancestral Debt (Pitra Rin)",            ["Venus", "Mercury", "Rahu"], [2, 5, 9, 12]),
            ("Self Debt (Swayam Rin)",                 ["Venus", "Rahu"],            [5]),
            ("Maternal Debt (Matri Rin)",              ["Ketu"],                     [4]),
            ("Family/Wife/Woman Debt (Stri Rin)",      ["Sun", "Rahu", "Ketu"],      [2, 7]),
            ("Relative/Brother Debt (Bhai-Bandhu Rin)", ["Mercury", "Ketu"],         [1, 8]),
            ("Daughter/Sister Debt (Behen/Beti Rin)",  ["Moon"],                     [3, 6]),
            ("Oppression/Atrocious Debt (Zulm Rin)",   ["Sun", "Moon", "Mars"],      [10, 11]),
            ("Debt of the Unborn (Ajanma Rin)",        ["Venus", "Sun", "Rahu"],     [12]),
            ("Negative Speech Debt (Manda Bol Rin)",   ["Moon", "Mars", "Ketu"],     [6]),
        ]

        for name, plist, hlist in rin_rules:
            triggers = get_triggering_houses(plist, hlist)
            if triggers:
                res.append({
                    "debt_name": name,
                    "active": True,
                    "trigger_houses": triggers
                })
        return res

    def detect_dispositions(self, chart: dict) -> list[dict]:
        """Detect Lal Kitab disposition (spoiling/boosting) rules — informational only.
        
        The strength adjustments are applied separately in _apply_disposition_strength().
        This returns a list of triggered rules for logging/debugging.
        """
        res = []
        planets_data = chart.get("planets_in_houses", {})
        if not planets_data:
            return res

        def h(p: str) -> int | None:
            return planets_data.get(p, {}).get("house")

        def has_aspect(p1: str, p2: str) -> bool:
            return any(
                a.get("aspecting_planet") == p2
                for a in planets_data.get(p1, {}).get("aspects", [])
            )

        # 1. Sun-Saturn Conflict affecting Venus
        h_sun, h_sat = h("Sun"), h("Saturn")
        if h_sun and h_sat and (has_aspect("Sun", "Saturn") or has_aspect("Saturn", "Sun")):
            res.append({
                "rule_name": f"Sun(H{h_sun})-Saturn(H{h_sat}) Conflict",
                "affected_planets": ["Venus"],
                "effect": "Destructive",
            })

        # 2. Mars-Ketu Scapegoat (Sun H6 + Mars H10)
        if h("Sun") == 6 and h("Mars") == 10:
            res.append({
                "rule_name": "Sun(H6)-Mars(H10) Scapegoat",
                "affected_planets": ["Ketu"],
                "effect": "Destructive",
            })

        # 3. Mercury destructive aspects
        h_merc = h("Mercury")
        if h_merc == 3:
            res.append({
                "rule_name": "Mercury(H3) Destructive",
                "affected_planets": ["Jupiter", "Saturn"],
                "effect": "Destructive",
            })
        elif h_merc == 12:
            res.append({
                "rule_name": "Mercury(H12) Destructive",
                "affected_planets": ["Ketu"],
                "effect": "Destructive",
            })

        # 4. Jupiter-Rahu Destruction
        h_jup, h_rahu = h("Jupiter"), h("Rahu")
        if h_jup and h_rahu and (
            h_jup == h_rahu or has_aspect("Jupiter", "Rahu") or has_aspect("Rahu", "Jupiter")
        ):
            res.append({
                "rule_name": "Jupiter-Rahu Suppression",
                "affected_planets": ["Jupiter"],
                "effect": "Destructive",
            })

        return res

    def _integrate_masnui_planets(self, chart: dict, enriched: dict) -> None:
        """Create virtual planets in enriched for each Masnui trigger."""
        triggers = chart.get("masnui_grahas_formed", [])
        for trig in triggers:
            raw_name = trig["masnui_graha_name"]
            # Use "Masnui" prefix for enriched entries (canonical user-facing name)
            name = raw_name.replace("Artificial ", "Masnui ")
            h_num = trig["formed_in_house"]
            components = trig["components"]
            
            # Strength is average or component-based
            base_total = sum(enriched.get(c, {}).get("strength_total", 0.0) for c in components)
            
            from astroq.lk_prediction.lk_constants import MASNUI_TO_STANDARD
            base_planet = MASNUI_TO_STANDARD.get(name, "Sun")
            
            enriched[name] = {
                "house": h_num,
                "is_masnui": True,
                "components": components,
                "base_standard_planet": base_planet,
                "strength_total": base_total,
                "raw_aspect_strength": 0.0,
                "dignity_score": 0.0,
                "strength_breakdown": {"masnui_foundation": base_total},
                "aspects": [],
                "states": ["Masnui"]
            }
            # Feedback to parents
            for c in components:
                feedback = base_total * self.w_masnui
                if c in enriched:
                    enriched[c]["strength_total"] = enriched[c].get("strength_total", 0.0) + feedback
                    bd = enriched[c].setdefault("strength_breakdown", {})
                    bd["masnui_feedback"] = bd.get("masnui_feedback", 0.0) + feedback
                    # Add state tag for transparency and test verifiability
                    enriched[c].setdefault("states", [])
                    enriched[c]["states"].append(f"Masnui Feedback (+{feedback:.1f})")

    def _get_35_year_ruler(self, age: int) -> str:
        """Calculate the 35-year cycle ruler for a given age (1-based annual chart_period)."""
        if age <= 0:
            return ""
        period = (age - 1) % 35 + 1
        if 1  <= period <= 6:  return "Saturn"
        if 7  <= period <= 12: return "Rahu"
        if 13 <= period <= 15: return "Ketu"
        if 16 <= period <= 21: return "Jupiter"
        if 22 <= period <= 23: return "Sun"
        if period == 24:       return "Moon"
        if 25 <= period <= 27: return "Venus"
        if 28 <= period <= 33: return "Mars"
        if 34 <= period <= 35: return "Mercury"
        return ""

    def detect_andhi_kundli(self, chart: dict) -> str:
        """Andhi Kundli (Blind Horoscope) detection."""
        planets = chart.get("planets_in_houses", {})
        h = lambda p: planets.get(p, {}).get("house")
        if h("Sun") == 4 and h("Saturn") == 7:
            return "Active (Sun 4, Sat 7)"
        malefics_in_10 = [p for p in ["Saturn", "Rahu", "Ketu"] if h(p) == 10]
        if len(malefics_in_10) >= 2:
            return "Active (Malefics cluster in 10)"
        return "Inactive"
