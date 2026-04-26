"""
Fate Classification Report  v3
================================
Classifies each public figure life event as:
  - GRAHA PHAL (Fixed Fate)
  - RASHI PHAL (Doubtful Fate)
  - BOTH
  - NEITHER

Graha Phal (Fixed Fate) promise — any of:
  a) A FIXED_HOUSE_LORD of the domain's primary/secondary houses is in
     Pakka Ghar, Uchha, or Neech in the natal chart.
  b) A planet OCCUPYING the domain's primary house is in a dignity state.
  c) The domain's house lord is DORMANT (present but all aspect targets empty).
  d) A DISPOSITION_RULE is active that directly affects a domain-relevant planet.

Rashi Phal (Doubtful Fate) promise = Any DOUBTFUL_NATAL_PROMISES condition
  is active for the relevant domain in the natal chart.

Note: 'other' domain events have been reclassified to canonical domains.
"""

import os
import sys
import json

sys.path.append(os.path.join(os.getcwd(), "backend"))

from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.lk_constants import (
    DOMAIN_HOUSE_MAP,
    DOMAIN_ALIASES,
    FIXED_HOUSE_LORDS,
    PLANET_PAKKA_GHAR,
    PLANET_EXALTATION,
    PLANET_DEBILITATION,
    HOUSE_ASPECT_TARGETS,
    DISPOSITION_RULES,
)
from astroq.lk_prediction.doubtful_timing_engine import DOUBTFUL_NATAL_PROMISES

GEO_MAP = {
    "Allahabad, India": (25.4358, 81.8463, "+05:30"),
    "Mumbai, India": (19.0760, 72.8777, "+05:30"),
    "Vadnagar, India": (23.7801, 72.6373, "+05:30"),
    "San Francisco, California, US": (37.7749, -122.4194, "-08:00"),
    "Seattle, Washington, US": (47.6062, -122.3321, "-08:00"),
    "Sandringham, Norfolk, UK": (52.8311, 0.5054, "+00:00"),
    "New Delhi, India": (28.6139, 77.2090, "+05:30"),
    "Gary, Indiana, US": (41.5934, -87.3464, "-06:00"),
    "Pretoria, South Africa": (-25.7479, 28.2293, "+02:00"),
    "Porbandar, India": (21.6417, 69.6293, "+05:30"),
    "Raisen, India": (23.3308, 77.7788, "+05:30"),
    "Madanapalle, India": (13.5562, 78.5020, "+05:30"),
    "Indore, India": (22.7196, 75.8577, "+05:30"),
    "Jamshedpur, India": (22.8046, 86.2029, "+05:30"),
    "Jamaica Hospital, Queens, New York, US": (40.7028, -73.8152, "-05:00"),
    "Honolulu, Hawaii, US": (21.3069, -157.8583, "-10:00"),
    "Scranton, Pennsylvania, US": (41.4090, -75.6624, "-05:00"),
    "Mayfair, London, UK": (51.5100, -0.1458, "+00:00"),
    "Buckingham Palace, London, UK": (51.5014, -0.1419, "+00:00"),
    "Skopje, North Macedonia": (42.0003, 21.4280, "+01:00"),
}

# Normalise event domains (ground truth data uses "career_travel" not "career")
GROUND_TRUTH_DOMAIN_MAP = {
    "career_travel": "career",
    "career":        "career",
    "finance":       "wealth",
    "wealth":        "wealth",
    "health":        "health",
    "marriage":      "marriage",
    "progeny":       "progeny",
    "legal":         "litigation",
    "other":         "career",   # fallback for any remaining 'other'
}


def get_ppos(chart):
    return {p: d["house"] for p, d in chart.get("planets_in_houses", {}).items() if p != "Lagna"}


def resolve_domain(raw_domain: str) -> str:
    """Map ground-truth event domain to canonical lk_constants domain key."""
    normed = GROUND_TRUTH_DOMAIN_MAP.get(raw_domain, raw_domain)
    return DOMAIN_ALIASES.get(normed, normed)


def get_domain_planets(domain: str):
    """
    Using DOMAIN_HOUSE_MAP + FIXED_HOUSE_LORDS, get all planets that are
    structural lords of the primary and secondary houses for this domain.
    """
    house_info = DOMAIN_HOUSE_MAP.get(domain)
    if not house_info:
        return []
    all_houses = house_info.get("primary", []) + house_info.get("secondary", [])
    planets = set()
    for h in all_houses:
        for p in FIXED_HOUSE_LORDS.get(h, []):
            planets.add(p)
    return list(planets)


def _is_dormant(planet: str, natal_pos: dict) -> bool:
    """Planet is dormant if all houses it aspects from its natal position are empty."""
    house = natal_pos.get(planet)
    if not house:
        return False
    targets = HOUSE_ASPECT_TARGETS.get(house, [])
    occupied = set(natal_pos.values())
    return bool(targets) and all(t not in occupied for t in targets)


def _disposition_hits(natal_pos: dict, domain_lords: set) -> list:
    """Return disposition rules that actively affect a domain-relevant planet."""
    hits = []
    for causer, causer_houses, affected, effect in DISPOSITION_RULES:
        c_house = natal_pos.get(causer)
        if c_house and c_house in causer_houses and affected in domain_lords:
            hits.append(f"{causer} H{c_house} {effect}s {affected}")
    return hits


def check_graha_phal_promise(natal_pos: dict, domain: str):
    """
    Graha Phal promise detected via any of 4 sub-patterns:
      a) Fixed House Lord in dignity (Pakka Ghar / Exalted / Debilitated)
      b) Primary house occupant in dignity
      c) Domain lord is DORMANT (sleeping = structurally locked fate)
      d) Disposition Rule actively suppresses/boosts a domain lord
    """
    hits = []
    domain_planets = get_domain_planets(domain)
    domain_lords_set = set(domain_planets)
    primary_houses = DOMAIN_HOUSE_MAP.get(domain, {}).get("primary", [])

    # (a) Fixed House Lord in dignity
    for planet in domain_planets:
        house = natal_pos.get(planet)
        if house is None:
            continue
        if house == PLANET_PAKKA_GHAR.get(planet):
            hits.append(f"{planet} Pakka Ghar H{house}")
        if house in PLANET_EXALTATION.get(planet, []):
            hits.append(f"{planet} Exalted H{house}")
        if house in PLANET_DEBILITATION.get(planet, []):
            hits.append(f"{planet} Debilitated H{house}")

    # (b) Primary house occupant in dignity
    for planet, house in natal_pos.items():
        if house in primary_houses:
            if house == PLANET_PAKKA_GHAR.get(planet):
                tag = f"{planet} Pakka Ghar H{house} (occupant)"
                if tag not in hits: hits.append(tag)
            if house in PLANET_EXALTATION.get(planet, []):
                tag = f"{planet} Exalted H{house} (occupant)"
                if tag not in hits: hits.append(tag)
            if house in PLANET_DEBILITATION.get(planet, []):
                tag = f"{planet} Debilitated H{house} (occupant)"
                if tag not in hits: hits.append(tag)

    # (c) Dormant domain lord
    for planet in domain_planets:
        if _is_dormant(planet, natal_pos):
            h = natal_pos.get(planet)
            hits.append(f"{planet} DORMANT in H{h} (blocked fixed fate)")

    # (d) Disposition rule affecting domain lord
    disp = _disposition_hits(natal_pos, domain_lords_set)
    hits.extend(disp)

    return hits


def check_rashi_phal_promise(natal_pos: dict, domain: str):
    """
    Rashi Phal promise: any DOUBTFUL_NATAL_PROMISES condition is active for
    the event domain.
    """
    hits = []
    for promise in DOUBTFUL_NATAL_PROMISES:
        p_domain = promise.get("domain", "")
        # Accept if domain matches or promise is domain-agnostic
        if p_domain and p_domain != domain and domain not in p_domain and p_domain not in domain:
            continue
        try:
            if promise["condition"](natal_pos):
                hits.append(promise["name"])
        except Exception:
            pass
    return hits


def run_fate_classification():
    print("=== Fate Classification Report v2 (using lk_constants canonical mapping) ===\n")

    generator = ChartGenerator()
    data_path = os.path.join("backend", "data", "public_figures_ground_truth.json")
    with open(data_path) as f:
        figures = json.load(f)

    total_events = 0
    only_graha  = 0
    only_rashi  = 0
    both        = 0
    neither     = 0
    figure_summaries = []

    for fig in figures:
        name  = fig["name"]
        dob   = fig["dob"]
        tob   = fig["tob"]
        if len(tob.split(":")) == 2:
            tob += ":00"
        place = fig.get("birth_place", "New Delhi, India")
        lat, lon, tz = GEO_MAP.get(place, (28.6139, 77.2090, "+05:30"))

        try:
            payload = generator.build_full_chart_payload(
                dob_str=dob, tob_str=tob, place_name=place,
                latitude=lat, longitude=lon, utc_string=tz, chart_system="vedic"
            )
        except Exception as e:
            print(f"  [SKIP] {name}: {e}")
            continue

        natal_chart = payload.get("chart_0")
        if not natal_chart:
            continue

        natal_pos = get_ppos(natal_chart)
        fig_g = fig_r = fig_b = fig_n = 0

        print(f"\n{'─'*60}")
        print(f"  {name}")
        print(f"{'─'*60}")

        for event in fig.get("events", []):
            age    = event.get("age")
            desc   = event.get("description", "")
            raw_d  = event.get("domain", "career_travel")
            domain = resolve_domain(raw_d)
            total_events += 1

            gp_hits = check_graha_phal_promise(natal_pos, domain)
            rp_hits = check_rashi_phal_promise(natal_pos, domain)

            has_gp = len(gp_hits) > 0
            has_rp = len(rp_hits) > 0

            if has_gp and has_rp:
                tag = "🔵 BOTH"
                fig_b += 1; both += 1
            elif has_gp:
                tag = "🟢 GRAHA PHAL"
                fig_g += 1; only_graha += 1
            elif has_rp:
                tag = "🟡 RASHI PHAL"
                fig_r += 1; only_rashi += 1
            else:
                tag = "⚪ NEITHER"
                fig_n += 1; neither += 1

            gp_str = f" | GP: {gp_hits[0]}" if gp_hits else ""
            rp_str = f" | RP: {rp_hits[0]}" if rp_hits else ""
            print(f"  [Age {age:>3}] {tag:<20} {desc[:45]:<45}{gp_str}{rp_str}")

        fig_t = fig_g + fig_r + fig_b + fig_n
        figure_summaries.append({
            "name": name, "total": fig_t,
            "graha": fig_g, "rashi": fig_r, "both": fig_b, "neither": fig_n,
        })

    # ── Summary ──────────────────────────────────────────────────────────────
    total = total_events
    print("\n\n" + "=" * 64)
    print("  FATE CLASSIFICATION SUMMARY")
    print("  (using DOMAIN_HOUSE_MAP + FIXED_HOUSE_LORDS from lk_constants)")
    print("=" * 64)
    print(f"  Total Events:             {total}")
    print(f"  Graha Phal ONLY:        {only_graha:>5}  ({only_graha/total*100:.1f}%)")
    print(f"  Rashi Phal ONLY:        {only_rashi:>5}  ({only_rashi/total*100:.1f}%)")
    print(f"  BOTH (GP + RP):         {both:>5}  ({both/total*100:.1f}%)")
    print(f"  NEITHER:                {neither:>5}  ({neither/total*100:.1f}%)")
    print(f"\n  GP-explainable total:   {only_graha+both:>5}  ({(only_graha+both)/total*100:.1f}%)")
    print(f"  RP-explainable total:   {only_rashi+both:>5}  ({(only_rashi+both)/total*100:.1f}%)")

    print("\n\n" + "=" * 72)
    print("  PER-FIGURE BREAKDOWN")
    print(f"  {'Figure':<32} {'Total':>5} {'GP':>5} {'RP':>5} {'Both':>5} {'Neither':>7}")
    print("=" * 72)
    for s in figure_summaries:
        print(f"  {s['name']:<32} {s['total']:>5} {s['graha']:>5} {s['rashi']:>5} {s['both']:>5} {s['neither']:>7}")


if __name__ == "__main__":
    run_fate_classification()
