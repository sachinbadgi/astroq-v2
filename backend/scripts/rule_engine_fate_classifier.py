"""
Rule Engine Fate Classification  v2
=====================================
Classifies all 1145 rules in rules.db as:
  - GRAHA_PHAL  (Fixed Fate)   : unconditional natal structural dignity
  - RASHI_PHAL  (Doubtful Fate): conditional/conjunction/timing geometry
  - HYBRID      (Both)         : GP dignity state + conditional guard
  - CONTEXTUAL  (Karma/Context): 0-planet, house-count, social/relational
  - NEUTRAL     (Positional)   : single planet, non-dignity house, no qualifier

Graha Phal signals (condition tree):
  - planet_state: exalted/strong/pakka_ghar/debilitated/neech/uchha
  - planet placed in its specific Pakka Ghar / Exaltation / Debilitation house
  - house_status: empty  (blank house = structural fixed fate)

Rashi Phal signals:
  - conjunction / confrontation node (positional geometry)
  - house_health: afflicted / malefic
  - NOT guard (conditional block)
  - current_age node  (condition-tree timing gate)
  - 2+ distinct planets placed in different houses (implicit axis geometry)
  - age/timing words in description OR verdict text  (verdict-level time gate)

Contextual signals (new):
  - 0 planet placements in condition (house-count, social, relational rules)
"""

import sqlite3
import json
import os
import sys
from collections import Counter, defaultdict

sys.path.append(os.path.join(os.getcwd(), "backend"))
from astroq.lk_prediction.lk_constants import (
    PLANET_PAKKA_GHAR, PLANET_EXALTATION, PLANET_DEBILITATION
)

DB_PATH = "backend/data/rules.db"

# Houses that are Pakka Ghar or Exaltation for any planet
DIGNITY_HOUSES = set()
for p, h in PLANET_PAKKA_GHAR.items():
    DIGNITY_HOUSES.add(h)
for p, hs in PLANET_EXALTATION.items():
    DIGNITY_HOUSES.update(hs)
for p, hs in PLANET_DEBILITATION.items():
    DIGNITY_HOUSES.update(hs)

# planet_state values → Graha Phal (unconditional dignity)
GRAHA_STATES = {"exalted", "uchha", "pakka_ghar", "pakka", "debilitated", "neech", "strong", "dignified"}
# planet_state values → Rashi Phal (conditional/doubtful)
RASHI_STATES = {"weak", "malefic", "afflicted", "dormant", "sleeping", "functional_malefic"}

# Words in description/verdict that signal a time-gate (Rashi Phal)
TIMING_WORDS = {
    "age", "year", "after", "before", "until", "till", "at 22", "at 24", "at 36",
    "at 42", "at 48", "before marriage", "after marriage", "from the day",
    "eighth year", "delayed", "early", "late", "first child", "second child",
}


def extract_all_nodes(node):
    """Recursively extract all condition nodes from a condition tree."""
    nodes = []
    if isinstance(node, dict):
        nodes.append(node)
        for v in node.values():
            if isinstance(v, (dict, list)):
                nodes.extend(extract_all_nodes(v))
    elif isinstance(node, list):
        for item in node:
            nodes.extend(extract_all_nodes(item))
    return nodes


def classify_rule(rule_id, condition_json, description, verdict=""):
    """
    Returns (classification, reason, gp_signals, rp_signals)
    classification: 'GRAHA_PHAL' | 'RASHI_PHAL' | 'HYBRID' | 'CONTEXTUAL' | 'NEUTRAL'

    Fixes over v1:
      - Multi-planet positional rules (2+ planets in different houses, no conjunction
        keyword) are now detected as RASHI_PHAL (implicit axis geometry).
      - Timing/age words in description or verdict text are now detected as RASHI_PHAL
        (verdict-level time gate that was invisible to condition-tree analysis).
      - 0-planet house-only rules are now CONTEXTUAL, not NEUTRAL.
    """
    try:
        cond = json.loads(condition_json)
    except Exception:
        return "NEUTRAL", "parse_error", [], []

    nodes = extract_all_nodes(cond)

    gp_signals = []
    rp_signals = []

    # ── Collect placement data for multi-planet axis detection ────────────
    placement_planets = []
    placement_houses  = []

    for node in nodes:
        t = node.get("type", "")

        if t == "planet_state":
            state = node.get("condition", "").lower()
            if state in GRAHA_STATES:
                gp_signals.append(f"planet_state:{state}")
            elif state in RASHI_STATES:
                rp_signals.append(f"planet_state:{state}")

        elif t == "placement":
            planet = node.get("planet", "")
            houses = node.get("houses", [node.get("house")])
            if isinstance(houses, int):
                houses = [houses]
            houses = [h for h in (houses or []) if h]
            if planet and planet not in ("ANY", "P", "P1", "Any", "enemy", "Enemies"):
                placement_planets.append(planet)
                placement_houses.extend(houses)
                # Check if this planet is in its dignity house
                pakka = PLANET_PAKKA_GHAR.get(planet)
                exalt = PLANET_EXALTATION.get(planet, [])
                debit = PLANET_DEBILITATION.get(planet, [])
                if houses and (pakka in houses or
                               any(h in exalt for h in houses) or
                               any(h in debit for h in houses)):
                    gp_signals.append(f"{planet} dignity H{houses}")

        elif t == "conjunction":
            rp_signals.append("conjunction")

        elif t == "confrontation":
            rp_signals.append("confrontation")

        elif t == "house_health":
            state = node.get("condition", "").lower()
            if state in {"afflicted", "malefic"}:
                rp_signals.append(f"house_health:{state}")

        elif t == "house_status":
            state = node.get("state", "").lower()
            if state == "empty":
                gp_signals.append("blank_house")

        elif t == "NOT":
            rp_signals.append("NOT_guard")

        elif t == "current_age":
            rp_signals.append("condition_age_gate")

    # ── Gap fix 1: Multi-planet positional axis (implicit Rashi Phal) ─────
    unique_planets = list(dict.fromkeys(placement_planets))  # preserve order, dedupe
    unique_houses  = list(dict.fromkeys(placement_houses))
    if len(unique_planets) >= 2 and len(unique_houses) >= 2:
        # Two different planets in two different houses = axis/interaction geometry
        rp_signals.append(f"multi-planet axis ({'+'.join(unique_planets[:3])})")

    # ── Gap fix 2: Verdict/description timing words (Rashi Phal) ──────────
    combined_text = (description + " " + verdict).lower()
    timing_hits = [w for w in TIMING_WORDS if w in combined_text]
    if timing_hits:
        rp_signals.append(f"text_time_gate({timing_hits[0]})")

    # ── Gap fix 3: 0-planet rule = CONTEXTUAL ─────────────────────────────
    has_no_planets = len(unique_planets) == 0

    # Deduplicate
    gp_signals = list(dict.fromkeys(gp_signals))
    rp_signals = list(dict.fromkeys(rp_signals))

    has_gp = len(gp_signals) > 0
    has_rp = len(rp_signals) > 0

    if has_no_planets and not has_gp and not has_rp:
        return "CONTEXTUAL", "0-planet house/social rule", gp_signals, rp_signals
    elif has_gp and has_rp:
        return "HYBRID", "GP+RP signals", gp_signals, rp_signals
    elif has_gp:
        return "GRAHA_PHAL", "GP signals only", gp_signals, rp_signals
    elif has_rp:
        return "RASHI_PHAL", "RP signals only", gp_signals, rp_signals
    else:
        return "NEUTRAL", "single planet non-dignity placement", gp_signals, rp_signals


def run():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT id, domain, description, condition, scale, scoring_type FROM deterministic_rules")
    rules = cur.fetchall()

    classification_counts = Counter()
    domain_breakdown = defaultdict(Counter)
    scale_breakdown = defaultdict(Counter)
    sample_rules = defaultdict(list)

    for rule in rules:
        cls, reason, gp_sigs, rp_sigs = classify_rule(
            rule["id"], rule["condition"], rule["description"],
            verdict=rule["verdict"] if "verdict" in rule.keys() else ""
        )
        classification_counts[cls] += 1
        domain_breakdown[rule["domain"]][cls] += 1
        scale_breakdown[rule["scale"]][cls] += 1
        if len(sample_rules[cls]) < 5:
            sample_rules[cls].append({
                "id": rule["id"],
                "domain": rule["domain"],
                "desc": rule["description"][:80],
                "scale": rule["scale"],
                "scoring_type": rule["scoring_type"],
                "gp": gp_sigs[:2],
                "rp": rp_sigs[:2],
            })

    total = sum(classification_counts.values())

    # ── Print summary ──────────────────────────────────────────────────────
    print("=" * 64)
    print("  RULE ENGINE FATE CLASSIFICATION")
    print(f"  ({total} rules in deterministic_rules)")
    print("=" * 64)
    print(f"\n  {'Classification':<18} {'Count':>6}  {'%':>6}")
    print("  " + "─" * 34)
    for cls in ["GRAHA_PHAL", "RASHI_PHAL", "HYBRID", "CONTEXTUAL", "NEUTRAL"]:
        cnt = classification_counts[cls]
        pct = cnt / total * 100
        icon = {"GRAHA_PHAL": "🟢", "RASHI_PHAL": "🟡", "HYBRID": "🔵",
                "CONTEXTUAL": "🟣", "NEUTRAL": "⚪"}.get(cls, "")
        print(f"  {icon} {cls:<16} {cnt:>6}  {pct:>5.1f}%")

    # ── By domain ──────────────────────────────────────────────────────────
    print("\n\n  BY DOMAIN (GP | RP | Hybrid | Neutral)")
    print("  " + "─" * 60)
    all_domains = sorted(domain_breakdown.keys())
    for dom in all_domains:
        d = domain_breakdown[dom]
        tot_d = sum(d.values())
        gp = d.get("GRAHA_PHAL", 0)
        rp = d.get("RASHI_PHAL", 0)
        hy = d.get("HYBRID", 0)
        cx = d.get("CONTEXTUAL", 0)
        ne = d.get("NEUTRAL", 0)
        print(f"  {dom:<22} {tot_d:>4}  GP:{gp:>3} RP:{rp:>3} Hyb:{hy:>3} Ctx:{cx:>3} Neu:{ne:>3}")

    # ── By scale ───────────────────────────────────────────────────────────
    print("\n\n  BY SCALE (GP | RP | Hybrid | Neutral)")
    print("  " + "─" * 60)
    for scale in sorted(scale_breakdown.keys()):
        d = scale_breakdown[scale]
        tot_s = sum(d.values())
        gp = d.get("GRAHA_PHAL", 0)
        rp = d.get("RASHI_PHAL", 0)
        hy = d.get("HYBRID", 0)
        cx = d.get("CONTEXTUAL", 0)
        ne = d.get("NEUTRAL", 0)
        print(f"  {scale:<22} {tot_s:>4}  GP:{gp:>3} RP:{rp:>3} Hyb:{hy:>3} Ctx:{cx:>3} Neu:{ne:>3}")

    # ── Sample rules per class ─────────────────────────────────────────────
    for cls in ["GRAHA_PHAL", "RASHI_PHAL", "HYBRID", "CONTEXTUAL"]:
        print(f"\n\n  SAMPLE {cls} RULES:")
        print("  " + "─" * 60)
        for s in sample_rules[cls]:
            gp_str = ", ".join(s["gp"]) or "—"
            rp_str = ", ".join(s["rp"]) or "—"
            print(f"  [{s['domain']}] {s['desc']}")
            print(f"    scale={s['scale']} | GP: {gp_str} | RP: {rp_str}")


if __name__ == "__main__":
    run()
