"""
NatalFateView
=============
Reads a natal chart and classifies every life domain / modern event
as GRAHA_PHAL (fixed fate), RASHI_PHAL (conditional fate), HYBRID, or NEITHER.

Classification algorithm per domain entry:
  1. Extract planet→house positions from natal_chart["planets_in_houses"].
  2. Check primary_houses: any planet present → domain structurally active.
  3. For each key_planet, check dignity in any primary or supporting house:
       - Pakka Ghar match   → gp_signal
       - Exaltation match   → gp_signal
       - Debilitation match → rp_penalty
  4. Assign fate_type:
       - gp_signal AND NOT rp_penalty → GRAHA_PHAL
       - gp_signal AND rp_penalty     → HYBRID
       - primary house occupied, no gp_signal → RASHI_PHAL
       - all primary/supporting houses empty  → NEITHER

Output is a list[dict] — JSON-serializable and LLM/MCP tool-ready.

Usage:
    view = NatalFateView()
    entries = view.evaluate(natal_chart)
    print(view.format_as_table(entries))

    # As JSON for LLM context:
    import json
    print(json.dumps(entries, indent=2))
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .lk_constants import (
    PLANET_PAKKA_GHAR,
    PLANET_EXALTATION,
    PLANET_DEBILITATION,
    PUCCA_GHARS_EXTENDED,
    RULE_FATE_TYPE_LABELS,
)
from .lk_pattern_constants import EVENT_DOMAIN_CATALOGUE
from .dormancy_engine import DormancyEngine


# ---------------------------------------------------------------------------
# Output Schema (plain dict, JSON-serializable)
# ---------------------------------------------------------------------------
# Each entry returned by evaluate() has this structure:
#
#   {
#     "domain":          str,          # machine key, e.g. "cryptocurrency"
#     "label":           str,          # human label, e.g. "Cryptocurrency & Digital Assets"
#     "category":        str,          # grouping key, e.g. "modern_finance"
#     "fate_type":       str,          # "GRAHA_PHAL" | "RASHI_PHAL" | "HYBRID" | "NEITHER"
#     "fate_label":      str,          # human label for fate_type
#     "evidence":        list[str],    # reasons for the classification
#     "key_planets":     list[str],    # planets evaluated for this domain
#     "active_houses":   list[int],    # primary/supporting houses that are occupied
#     "dignity_details": dict[str,str] # { planet: "Pakka Ghar H7" | "Exalted H6" | ... }
#   }
#
# ---------------------------------------------------------------------------

_FATE_LABELS: Dict[str, str] = {
    "GRAHA_PHAL": "Fixed Fate (Graha Phal)",
    "RASHI_PHAL": "Conditional Fate (Rashi Phal)",
    "HYBRID":     "Fixed + Conditional (Hybrid)",
    "NEITHER":    "Domain Absent (Neither)",
}


class NatalFateView:
    """
    Stateless evaluator — takes a natal chart dict, returns list[dict].
    No database required; works purely from lk_constants.py dignity tables
    and EVENT_DOMAIN_CATALOGUE in lk_pattern_constants.py.
    """

    def __init__(self):
        self.dormancy_engine = DormancyEngine()

    def evaluate(
        self,
        natal_chart: Dict[str, Any],
        categories: Optional[List[str]] = None,
        include_neither: bool = True,
        db_rule_hits: Optional[list] = None,
    ) -> List[Dict[str, Any]]:
        """
        Classify every domain in EVENT_DOMAIN_CATALOGUE against the natal chart.

        Parameters
        ----------
        natal_chart : dict
            Standard chart payload with "planets_in_houses" key.
        categories : list[str] | None
            If given, only entries whose category is in this list are returned.
            None = return all 50+ domains.
        include_neither : bool
            If False, entries with fate_type == "NEITHER" are excluded.
        db_rule_hits : list | None
            Optional list of RuleHit objects from RulesEngine.evaluate_chart().
            When provided, DB rule fate_type signals are used to override the
            constants-based classification for canonical domains.

        Returns
        -------
        list[dict]  — JSON-serializable, LLM/MCP tool-ready.
        """
        positions = self._extract_positions(natal_chart)

        # Build a quick lookup: domain → best DB fate_type if hits supplied
        db_domain_fate: Dict[str, str] = {}
        if db_rule_hits:
            for hit in db_rule_hits:
                domain = getattr(hit, "domain", "")
                fate = getattr(hit, "fate_type", None) or ""
                if domain and fate in ("GRAHA_PHAL", "RASHI_PHAL", "HYBRID"):
                    # Promote: GRAHA_PHAL > HYBRID > RASHI_PHAL
                    prev = db_domain_fate.get(domain, "")
                    if self._fate_rank(fate) > self._fate_rank(prev):
                        db_domain_fate[domain] = fate

        results: List[Dict[str, Any]] = []

        for entry in EVENT_DOMAIN_CATALOGUE:
            if categories and entry["category"] not in categories:
                continue

            fate_entry = self._classify_domain(entry, positions, db_domain_fate, natal_chart)

            if not include_neither and fate_entry["fate_type"] == "NEITHER":
                continue

            results.append(fate_entry)

        return results

    # ------------------------------------------------------------------
    # Private: classification logic
    # ------------------------------------------------------------------

    def _classify_domain(
        self,
        entry: Dict[str, Any],
        positions: Dict[str, int],
        db_domain_fate: Dict[str, str],
        natal_chart: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Run the 5-step classification algorithm for a single domain entry."""
        primary_houses: List[int] = entry["primary_houses"]
        supporting_houses: List[int] = entry.get("supporting_houses", [])
        key_planets: List[str] = entry["key_planets"]
        all_houses = primary_houses + supporting_houses

        # Step 1: which primary/supporting houses are occupied?
        occupied_positions = set(positions.values())
        active_houses = [h for h in all_houses if h in occupied_positions]

        # Step 2: evaluate each key_planet's dignity
        gp_signals: List[str] = []
        rp_penalties: List[str] = []
        dignity_details: Dict[str, str] = {}

        for planet in key_planets:
            house = positions.get(planet)
            if house is None:
                dignity_details[planet] = "Absent"
                continue

            # Pakka Ghar (single permanent home)
            if PLANET_PAKKA_GHAR.get(planet) == house:
                label = f"Pakka Ghar H{house}"
                gp_signals.append(f"{planet} in {label}")
                dignity_details[planet] = label
                continue

            # Exaltation (one or more houses)
            if house in PLANET_EXALTATION.get(planet, []):
                label = f"Exalted H{house}"
                gp_signals.append(f"{planet} {label}")
                dignity_details[planet] = label
                continue

            # Debilitation
            if house in PLANET_DEBILITATION.get(planet, []):
                label = f"Debilitated H{house}"
                rp_penalties.append(f"{planet} {label}")
                dignity_details[planet] = label
                continue

            # Extended Pucca Ghars (broader safe houses — partial GP signal)
            if house in PUCCA_GHARS_EXTENDED.get(planet, []):
                label = f"Pucca Ghar H{house}"
                gp_signals.append(f"{planet} in {label} (extended)")
                dignity_details[planet] = label
                continue

            # Neutral — in chart but not dignified
            if house in all_houses:
                dignity_details[planet] = f"Neutral H{house}"
            else:
                dignity_details[planet] = f"Off-domain H{house}"

        # Step 3: check for structural activity
        primary_occupied = any(h in occupied_positions for h in primary_houses)
        any_key_planet_present = any(p in positions for p in key_planets)

        # Step 3.5: Conjunction bonus — multiple key planets co-located in primary houses
        # amplify the signal strength and can upgrade the classification.
        key_planets_in_primary = [
            p for p in key_planets
            if p in positions and positions[p] in primary_houses
        ]
        if len(key_planets_in_primary) >= 2:
            conjunction_house = positions[key_planets_in_primary[0]]
            if all(positions[p] == conjunction_house for p in key_planets_in_primary):
                gp_signals.append(
                    f"Conjunction: {', '.join(key_planets_in_primary)} co-located in H{conjunction_house} — amplified signal"
                )

        # Step 3.6: Domain-specific supporting-house dignity boost
        # For marriage, Venus or Mercury in H2 (supporting house) with dignity
        # is a strong enough signal to count toward GRAHA_PHAL independently.
        if entry["domain"] == "marriage":
            for planet in ["Venus", "Mercury"]:
                house = positions.get(planet)
                if house is not None and house in supporting_houses:
                    if (PLANET_PAKKA_GHAR.get(planet) == house or
                        house in PLANET_EXALTATION.get(planet, []) or
                        house in PUCCA_GHARS_EXTENDED.get(planet, [])):
                        if not any(planet in s for s in gp_signals):
                            gp_signals.append(
                                f"{planet} in supporting H{house} with dignity — marriage domain boost"
                            )

        # Step 4: classify
        if gp_signals and not rp_penalties:
            fate_type = "GRAHA_PHAL"
            evidence = gp_signals + [entry["gp_condition"]]
        elif gp_signals and rp_penalties:
            fate_type = "HYBRID"
            evidence = gp_signals + rp_penalties + ["Mixed dignity — promise exists but conditional guard active"]
        elif primary_occupied or any_key_planet_present:
            fate_type = "RASHI_PHAL"
            evidence = [entry["rp_condition"]] + rp_penalties
            if any_key_planet_present and not primary_occupied:
                evidence.append(f"Karaka planet {key_planets} present in chart but not in primary houses {primary_houses}. Fate is conditional (Rashi Phal).")
        else:
            fate_type = "NEITHER"
            evidence = [f"No planet in primary houses {primary_houses} and all key planets {key_planets} absent from chart"]

        # Step 4.5: Check for Dormancy (Soyi Hui)
        # If any planet in primary houses or key_planets is dormant, add to evidence
        is_any_dormant = False
        dormant_planets = []
        for planet in key_planets:
            if planet in positions:
                state = self.dormancy_engine.get_complex_state(planet, positions[planet], positions)
                if not state.is_awake:
                    is_any_dormant = True
                    dormant_planets.append(planet)
        
        if is_any_dormant and fate_type != "NEITHER":
            evidence.append(f"DORMANT: Key planets {dormant_planets} are Soya Hua (Dormant). Promise exists but needs 'Jagane Wala Grah' (Awakener).")

        # Step 5: DB override (only upgrades or confirms; never silently downgrades)
        db_fate = db_domain_fate.get(entry["domain"], "")
        if db_fate and self._fate_rank(db_fate) > self._fate_rank(fate_type):
            fate_type = db_fate
            evidence.insert(0, f"DB rule confirms {db_fate}")

        return {
            "domain":          entry["domain"],
            "label":           entry["label"],
            "category":        entry["category"],
            "fate_type":       fate_type,
            "fate_label":      _FATE_LABELS.get(fate_type, fate_type),
            "evidence":        evidence,
            "key_planets":     key_planets,
            "active_houses":   sorted(set(active_houses)),
            "dignity_details": dignity_details,
        }

    # ------------------------------------------------------------------
    # Private: helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_positions(natal_chart: Dict[str, Any]) -> Dict[str, int]:
        """Return {planet_name: house_number} from chart, excluding Lagna/Asc."""
        out: Dict[str, int] = {}
        for planet, data in natal_chart.get("planets_in_houses", {}).items():
            if planet in ("Lagna", "Asc"):
                continue
            h = data.get("house")
            if isinstance(h, list) and len(h) > 0:
                h = h[0]
            if h is not None:
                try:
                    out[planet] = int(h)
                except ValueError:
                    pass
        return out

    @staticmethod
    def _fate_rank(fate: str) -> int:
        """Priority for DB override: GRAHA_PHAL > HYBRID > RASHI_PHAL > NEITHER > ''."""
        return {"GRAHA_PHAL": 4, "HYBRID": 3, "RASHI_PHAL": 2, "NEITHER": 1}.get(fate, 0)

    # ------------------------------------------------------------------
    # Public: formatting
    # ------------------------------------------------------------------

    def format_as_table(self, entries: List[Dict[str, Any]]) -> str:
        """
        Renders entries as a plain-text table grouped by category.
        Suitable for CLI output, audit scripts, and markdown embedding.
        """
        if not entries:
            return "No entries to display."

        # Group by category
        groups: Dict[str, List[Dict]] = {}
        for e in entries:
            groups.setdefault(e["category"], []).append(e)

        category_labels = {
            "canonical":     "CANONICAL DOMAINS",
            "career_tech":   "CAREER & TECHNOLOGY",
            "finance":       "FINANCE & INVESTMENTS",
            "home_lifestyle":"HOME, LIFESTYLE & SUSTAINABILITY",
            "health_wellness":"HEALTH & WELLNESS",
            "tech_infra":    "TECHNOLOGY & DIGITAL INFRASTRUCTURE",
            "modern_finance":"MODERN FINANCE",
            "sustainable":   "SUSTAINABLE INNOVATION",
            "social_psych":  "SOCIAL & PSYCHOLOGICAL",
        }

        col_w = [32, 14, 30]  # label, fate_type, key_planets
        header = (
            f"{'Domain':<{col_w[0]}}  {'Fate Type':<{col_w[1]}}  "
            f"{'Key Planets & Dignity':<{col_w[2]}}"
        )
        sep = "─" * (col_w[0] + col_w[1] + col_w[2] + 4)

        lines: List[str] = []
        for cat, cat_entries in groups.items():
            lines.append("")
            lines.append(category_labels.get(cat, cat.upper()))
            lines.append(sep)
            lines.append(header)
            lines.append(sep)
            for e in cat_entries:
                dignity_str = ", ".join(
                    f"{p}: {d}" for p, d in e["dignity_details"].items()
                    if d != "Absent"
                )
                lines.append(
                    f"{e['label'][:col_w[0]]:<{col_w[0]}}  "
                    f"{e['fate_type']:<{col_w[1]}}  "
                    f"{dignity_str[:col_w[2]]}"
                )
            lines.append("")

        return "\n".join(lines)
