"""
Neither Pattern Miner
======================
For all events classified as NEITHER (no Graha Phal or Rashi Phal natal promise),
run a deeper structural analysis across 6 pattern axes:

  1. HOUSE OCCUPANT   — a planet sits in the domain's primary house (no dignity, but present)
  2. DISPOSITION RULE — a DISPOSITION_RULE is active that affects a domain-relevant planet
  3. RIN (DEBT)       — a RIN_RULE is active involving the domain's primary house planets
  4. MASNUI           — a Masnui (artificial) planet forms in the domain's primary house
  5. CYCLE RULER      — the 35-year cycle ruler at the event age is a domain-relevant planet
  6. DORMANT LORD     — the domain's house lord is present but ALL its aspects are empty (dormant)

Reports the hit rate for each pattern across all 166 NEITHER events.
"""

import os
import sys
import json
from collections import defaultdict, Counter

sys.path.append(os.path.join(os.getcwd(), "backend"))

from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.lk_constants import (
    DOMAIN_HOUSE_MAP, DOMAIN_ALIASES,
    FIXED_HOUSE_LORDS,
    PLANET_PAKKA_GHAR, PLANET_EXALTATION, PLANET_DEBILITATION,
    DISPOSITION_RULES, RIN_RULES, MASNUI_FORMATION_RULES,
    HOUSE_ASPECT_TARGETS, get_35_year_ruler,
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

GROUND_TRUTH_DOMAIN_MAP = {
    "career_travel": "career",
    "career":        "career",
    "finance":       "wealth",
    "health":        "health",
    "marriage":      "marriage",
    "progeny":       "progeny",
    "legal":         "litigation",
}


def get_ppos(chart):
    return {p: d["house"] for p, d in chart.get("planets_in_houses", {}).items() if p != "Lagna"}


def resolve_domain(raw_domain):
    normed = GROUND_TRUTH_DOMAIN_MAP.get(raw_domain, raw_domain)
    return DOMAIN_ALIASES.get(normed, normed)


def get_domain_houses(domain):
    info = DOMAIN_HOUSE_MAP.get(domain, {})
    return info.get("primary", []) + info.get("secondary", [])


def get_domain_lords(domain):
    planets = set()
    for h in get_domain_houses(domain):
        for p in FIXED_HOUSE_LORDS.get(h, []):
            planets.add(p)
    return list(planets)


def has_dignity(planet, house):
    return (house == PLANET_PAKKA_GHAR.get(planet) or
            house in PLANET_EXALTATION.get(planet, []) or
            house in PLANET_DEBILITATION.get(planet, []))


# ─── Pattern checkers ────────────────────────────────────────────────────────

def pattern_house_occupant(natal_pos, domain):
    """Planet sits in primary domain house but with no dignity."""
    primary = DOMAIN_HOUSE_MAP.get(domain, {}).get("primary", [])
    hits = []
    for planet, house in natal_pos.items():
        if house in primary and not has_dignity(planet, house):
            hits.append(f"{planet} in H{house} (no dignity)")
    return hits


def pattern_disposition(natal_pos, domain):
    """A disposition rule fires involving a domain-relevant planet."""
    lords = set(get_domain_lords(domain))
    primary_houses = DOMAIN_HOUSE_MAP.get(domain, {}).get("primary", [])
    # Also include any planet sitting in the primary house
    occupants = {p for p, h in natal_pos.items() if h in primary_houses}
    relevant = lords | occupants
    hits = []
    for causer, causer_houses, affected, effect in DISPOSITION_RULES:
        c_house = natal_pos.get(causer)
        if c_house and c_house in causer_houses and affected in relevant:
            hits.append(f"{causer} in H{c_house} {effect}s {affected} ({effect})")
    return hits


def pattern_rin(natal_pos, domain):
    """A RIN (debt) rule is active whose trigger planets are domain lords."""
    lords = set(get_domain_lords(domain))
    primary_houses = DOMAIN_HOUSE_MAP.get(domain, {}).get("primary", [])
    hits = []
    for debt_name, planet_triggers, house_triggers in RIN_RULES:
        for planet in planet_triggers:
            house = natal_pos.get(planet)
            if house and house in house_triggers:
                # Relevant if the debt planet is a domain lord, OR the debt house is a domain house
                if planet in lords or house in primary_houses:
                    hits.append(f"{debt_name}: {planet} in H{house}")
    return hits


def pattern_masnui(natal_pos, domain):
    """A Masnui (artificial planet) forms in the domain's primary house."""
    primary = DOMAIN_HOUSE_MAP.get(domain, {}).get("primary", [])
    # Build house→planets map
    house_planets = defaultdict(set)
    for p, h in natal_pos.items():
        house_planets[h].add(p.lower())
    hits = []
    for house in primary:
        occupants = house_planets.get(house, set())
        for required_set, masnui_name in MASNUI_FORMATION_RULES:
            if required_set.issubset(occupants):
                hits.append(f"{masnui_name} forms in H{house}")
    return hits


def pattern_cycle_ruler(natal_pos, domain, age):
    """The 35-year cycle ruler at this age is a domain-relevant lord."""
    lords = set(get_domain_lords(domain))
    ruler = get_35_year_ruler(age)
    if ruler and ruler in lords:
        house = natal_pos.get(ruler, "?")
        return [f"35yr ruler {ruler} (H{house}) governs this domain"]
    return []


def pattern_dormant_lord(natal_pos, domain):
    """Domain house lord is present but all its aspect targets are empty (dormant)."""
    lords = get_domain_lords(domain)
    occupied = set(natal_pos.values())
    hits = []
    for planet in lords:
        house = natal_pos.get(planet)
        if not house:
            continue
        aspect_targets = HOUSE_ASPECT_TARGETS.get(house, [])
        if aspect_targets and all(t not in occupied for t in aspect_targets):
            hits.append(f"{planet} in H{house} is DORMANT (all aspects empty)")
    return hits


# ─── Main ────────────────────────────────────────────────────────────────────

def run_neither_pattern_miner():
    print("=== NEITHER Pattern Miner ===\n")

    generator = ChartGenerator()
    data_path = os.path.join("backend", "data", "public_figures_ground_truth.json")
    with open(data_path) as f:
        figures = json.load(f)

    # Pattern counters
    pattern_names = [
        "1. House Occupant (no dignity)",
        "2. Disposition Rule active",
        "3. RIN Debt active",
        "4. Masnui formation in house",
        "5. 35yr Cycle Ruler is domain lord",
        "6. Domain Lord is DORMANT",
    ]
    pattern_counts    = Counter()
    pattern_exclusive = Counter()  # counts events explained by ONLY this pattern
    domain_counts     = Counter()

    neither_events = []
    total_neither = 0

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
        except Exception:
            continue

        natal_chart = payload.get("chart_0")
        if not natal_chart:
            continue
        natal_pos = get_ppos(natal_chart)

        for event in fig.get("events", []):
            age    = event.get("age", 0)
            desc   = event.get("description", "")
            raw_d  = event.get("domain", "career_travel")
            domain = resolve_domain(raw_d)

            # Re-check this is a NEITHER event
            lords     = get_domain_lords(domain)
            primary   = DOMAIN_HOUSE_MAP.get(domain, {}).get("primary", [])
            secondary = DOMAIN_HOUSE_MAP.get(domain, {}).get("secondary", [])
            all_houses = primary + secondary

            is_gp = any(
                has_dignity(p, natal_pos[p])
                for p in lords if p in natal_pos
            ) or any(
                has_dignity(p, h)
                for p, h in natal_pos.items()
                if h in primary
            )
            is_rp = any(
                p["condition"](natal_pos)
                for p in DOUBTFUL_NATAL_PROMISES
                if not p["domain"] or p["domain"] == domain or domain in p["domain"]
            )

            if is_gp or is_rp:
                continue  # skip non-NEITHER

            total_neither += 1
            domain_counts[domain] += 1

            # Run all 6 patterns
            hits = {}
            hits["1. House Occupant (no dignity)"]     = pattern_house_occupant(natal_pos, domain)
            hits["2. Disposition Rule active"]          = pattern_disposition(natal_pos, domain)
            hits["3. RIN Debt active"]                  = pattern_rin(natal_pos, domain)
            hits["4. Masnui formation in house"]        = pattern_masnui(natal_pos, domain)
            hits["5. 35yr Cycle Ruler is domain lord"]  = pattern_cycle_ruler(natal_pos, domain, age)
            hits["6. Domain Lord is DORMANT"]           = pattern_dormant_lord(natal_pos, domain)

            fired = [k for k, v in hits.items() if v]
            for k in fired:
                pattern_counts[k] += 1
            if len(fired) == 1:
                pattern_exclusive[fired[0]] += 1

            neither_events.append({
                "figure": name, "age": age, "desc": desc, "domain": domain,
                "patterns": hits, "fired": fired,
            })

    # ── Print detail for first 20 NEITHER events ──────────────────────────────
    print(f"Sample NEITHER Events (first 20 of {total_neither}):")
    print("─" * 70)
    for ev in neither_events[:20]:
        fired_str = ", ".join(ev["fired"]) if ev["fired"] else "TRULY UNEXPLAINED"
        print(f"  [{ev['figure']}, Age {ev['age']}] {ev['desc'][:40]} | domain={ev['domain']}")
        print(f"    ↳ {fired_str}")
        for k, v in ev["patterns"].items():
            if v:
                print(f"       {k}: {v[0]}")

    # ── Summary ──────────────────────────────────────────────────────────────
    truly_unexplained = sum(1 for e in neither_events if not e["fired"])

    print(f"\n\n{'='*64}")
    print("  NEITHER PATTERN ANALYSIS SUMMARY")
    print(f"  ({total_neither} events with no Graha Phal or Rashi Phal promise)")
    print(f"{'='*64}")
    print(f"  {'Pattern':<40} {'Hits':>5}  {'% of NEITHER':>12}  {'Exclusive':>9}")
    print("  " + "─"*62)
    for name in pattern_names:
        cnt = pattern_counts[name]
        excl = pattern_exclusive[name]
        pct = cnt / total_neither * 100 if total_neither else 0
        print(f"  {name:<40} {cnt:>5}  {pct:>11.1f}%  {excl:>9}")

    covered_by_any = sum(1 for e in neither_events if e["fired"])
    print(f"\n  Covered by ≥1 pattern:  {covered_by_any} ({covered_by_any/total_neither*100:.1f}%)")
    print(f"  Truly unexplained:       {truly_unexplained} ({truly_unexplained/total_neither*100:.1f}%)")

    print(f"\n  NEITHER events by domain:")
    for dom, cnt in domain_counts.most_common():
        print(f"    {dom:<20} {cnt}")


if __name__ == "__main__":
    run_neither_pattern_miner()
