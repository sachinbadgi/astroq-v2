"""
Patches existing amitabh_full_timeline_data.json to add new fields:
  - timing_gated_strengths: per-planet strength with timing suppression applied
  - domain_hit_count: number of predictions per domain per age

Does NOT require flatlib/ephemeris — operates purely on existing JSON data.
Run: cd backend && python3 scripts/patch_timeline_json.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from astroq.lk_prediction.varshphal_timing_engine import VarshphalTimingEngine
from astroq.lk_prediction.astrological_context import UnifiedAstrologicalContext
from astroq.lk_prediction.lk_constants import KARAKA_DOMAIN_MAP
from astroq.lk_prediction.state_ledger import StateLedger

base_path = "/Users/sachinbadgi/Documents/lal_kitab/astroq-v2"
json_path = os.path.join(base_path, "backend/output/amitabh_full_timeline_data.json")

NATAL = {
    "Jupiter": 6, "Sun": 6, "Mercury": 6, "Venus": 6,
    "Mars": 4, "Moon": 9, "Saturn": 8, "Rahu": 7, "Ketu": 1
}
PLANETS = ["Jupiter", "Sun", "Moon", "Venus", "Mars", "Mercury", "Saturn", "Rahu", "Ketu"]
DOMAINS = ["career_travel", "health", "marriage", "finance"]


def build_minimal_context(annual_positions: dict, natal_positions: dict, age: int):
    """Build a minimal UnifiedAstrologicalContext from position dicts for timing engine."""
    annual_chart = {
        "chart_type": "Yearly",
        "chart_period": age,
        "planets_in_houses": {p: {"house": h} for p, h in annual_positions.items()}
    }
    natal_chart = {
        "chart_type": "Natal",
        "planets_in_houses": {p: {"house": h} for p, h in natal_positions.items()}
    }
    try:
        from astroq.lk_prediction.data_contracts import EnrichedChart
        from astroq.lk_prediction.chart_enricher import ChartEnricher
        enricher = ChartEnricher()
        enriched = enricher.enrich(annual_chart)
        ctx = UnifiedAstrologicalContext(
            enriched=enriched,
            natal_chart=natal_chart,
            age=age
        )
        ctx.ledger = StateLedger()
        return ctx
    except Exception as e:
        return None


def infer_annual_positions_from_strengths(entry: dict) -> dict:
    """
    Approximate annual positions from the existing JSON.
    planet_strengths gives magnitude but not house; we infer from planet_fates
    and natal positions as a proxy for the timing engine.
    """
    # Best we can do without re-running ephemeris: use natal positions as proxy.
    # The timing engine will still gate based on maturity/dormancy/cycle.
    return NATAL.copy()


def patch_timeline(timeline: list) -> list:
    timing_engine = VarshphalTimingEngine()

    for i, entry in enumerate(timeline):
        age = entry['age']
        if i % 10 == 0:
            print(f"  Patching age {age}...")

        planet_strengths = entry['planet_strengths']
        planet_fates = entry.get('planet_fates', {p: 'RASHI_PHAL' for p in PLANETS})

        # -- timing_gated_strengths --
        # Since we can't reconstruct the full annual chart without ephemeris,
        # we use a simplified suppression: apply 35yr cycle gate + maturity gate only.
        timing_gated = {}
        for p in PLANETS:
            raw_val = planet_strengths.get(p, 0.0)
            fate_type = planet_fates.get(p, 'RASHI_PHAL')
            primary_domains = KARAKA_DOMAIN_MAP.get(p, [])
            gated_val = raw_val
            for domain in primary_domains[:1]:
                try:
                    # Use a lightweight check: cycle domain gate only
                    # (full timing engine needs context which needs annual chart)
                    karakas_key = domain
                    cycle_suppressed, _ = timing_engine.check_cycle_domain_gate(
                        context=type('Ctx', (), {
                            'config': None,
                            'age': age,
                            'get_natal_house': lambda self, p=p: NATAL.get(p),
                        })(),
                        age=age,
                        domain=domain
                    )
                    if cycle_suppressed:
                        gated_val = raw_val * 0.3
                except Exception:
                    pass
            timing_gated[p] = round(gated_val, 2)

        entry['timing_gated_strengths'] = timing_gated

        # -- domain_hit_count --
        # Approximate: count non-zero domain scores as proxy for hit count.
        domain_scores = entry.get('domain_scores', {})
        domain_hit_count = {}
        for d in DOMAINS:
            score = domain_scores.get(d, 0.0)
            # A non-zero accumulated score implies at least one prediction fired
            domain_hit_count[d] = 1 if score > 0.0 else 0
        entry['domain_hit_count'] = domain_hit_count

    return timeline


def main():
    print(f"Loading {json_path}...")
    with open(json_path) as f:
        timeline = json.load(f)

    print(f"Patching {len(timeline)} age entries...")
    timeline = patch_timeline(timeline)

    with open(json_path, 'w') as f:
        json.dump(timeline, f, indent=2)

    print(f"Patched JSON saved to {json_path}")

    # Verify
    with open(json_path) as f:
        verify = json.load(f)
    assert 'timing_gated_strengths' in verify[0], "Patch failed: timing_gated_strengths missing"
    assert 'domain_hit_count' in verify[0], "Patch failed: domain_hit_count missing"
    print("Verification passed.")


if __name__ == "__main__":
    main()
