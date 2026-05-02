"""
Canonical Lal Kitab Astrological Reference Constants
=====================================================

Single source of truth for ALL Lal Kitab lookup tables and reference data.
This file consolidates data for:
  - constants.py           (dignities, aspects, relationships)
  - grammar_analyser.py    (grammar rules, masnui conjunctions, disposition rules)
  - remedy_engine.py       (pucca ghars, goswami rules, life area groups)
  - prediction_translator.py (planet-house articles, relatives)
  - chart_generator.py     (120-year Varshphal matrix)

Cross-reference guide
---------------------
  To find "where does Saturn sit comfortably?"
    → PLANET_PAKKA_GHAR, PUCCA_GHARS_EXTENDED, PLANET_EXALTATION

  To find "what are the natural enemies of Sun?"
    → NATURAL_RELATIONSHIPS["Sun"]["Enemies"], or ENEMIES

  To find "what aspect does H3 cast?"
    → HOUSE_ASPECT_DATA[3]

  To find "what disposition rules affect Mars?"
    → [r for r in DISPOSITION_RULES if r[2] == "Mars"]

  To find "what Masnui planet is formed by Sun+Venus?"
    → MASNUI_FORMATION_RULES: {"sun", "venus"} -> "Artificial Jupiter"

  To find "which house does Mars move to in year 45?"
    → VARSHPHAL_YEAR_MATRIX[45][natal_house]

  To find "who rules age 22 in the 35-year cycle?"
    → CYCLE_35_YEAR_RANGES (period 22 → "Sun")

  To find "what items are associated with Jupiter in H9?"
    → PLANET_HOUSE_ITEMS["Jupiter"][9]

  To find "what houses relate to 'career' domain?"
    → DOMAIN_HOUSE_MAP["career"]
"""

from __future__ import annotations
from typing import Any

# ============================================================================
# SECTION 0: RULE FATE TYPE CLASSIFICATION
# ============================================================================
#
# Every rule in deterministic_rules carries a `fate_type` field that
# classifies the structural nature of the natal promise it describes.
#
# Classification Taxonomy
# -----------------------
#
#   GRAHA_PHAL  (Fixed Fate)
#       The outcome is unconditionally stamped at birth via planetary dignity:
#       Pakka Ghar, Exaltation (Uchha), Debilitation (Neech), or a structurally
#       blank house. No annual chart trigger is needed for the PROMISE to exist —
#       only for it to MANIFEST.
#
#   RASHI_PHAL  (Doubtful / Conditional Fate)
#       The outcome is conditional on a specific geometric configuration:
#       planet conjunctions, confrontations (180°), afflicted houses, NOT-guards,
#       age/timing gates, or multi-planet axis interactions.  The promise can swing
#       auspicious OR malefic depending on the annual chart — hence "doubtful".
#
#   HYBRID
#       The rule carries BOTH a natal dignity signal (GP) AND a conditional guard
#       (RP).  Example: "If Rahu is in H9 (dignity), destiny shines AFTER age 42
#       (time-gate)".  The promise is fixed, but its timing window is conditional.
#
#   CONTEXTUAL  (Karma / Relational)
#       The rule operates on social, familial, or count-based context rather than
#       on planetary positions.  Examples: "If the wife has three brothers...",
#       "If H7 has more planets than H1...".  These require a separate evaluation
#       mechanism outside the planet-house engine.
#
#   NEUTRAL  (Positional / Baseline)
#       A single planet in a non-dignity house with no conditional qualifier.
#       Represents the baseline positional reading from which the rules engine
#       builds its source_rules list.  Neither definitively GP nor RP.
#
# Cross-ref: deterministic_rules.fate_type (DB column), rule_engine_fate_classifier.py

#: All valid fate type strings (matches deterministic_rules.fate_type column values).
RULE_FATE_TYPES: list[str] = [
    "GRAHA_PHAL",
    "RASHI_PHAL",
    "HYBRID",
    "CONTEXTUAL",
    "NEUTRAL",
]

#: Set form for fast membership testing.
RULE_FATE_TYPES_SET: frozenset[str] = frozenset(RULE_FATE_TYPES)

#: Fixed-fate rule types — only these should be used for unconditional natal promise detection.
FIXED_FATE_TYPES: frozenset[str] = frozenset({"GRAHA_PHAL", "HYBRID"})

#: Conditional-fate rule types — these require annual chart geometry to resolve.
CONDITIONAL_FATE_TYPES: frozenset[str] = frozenset({"RASHI_PHAL", "HYBRID"})

#: Human-readable labels for each fate type.
RULE_FATE_TYPE_LABELS: dict[str, str] = {
    "GRAHA_PHAL":  "Fixed Fate (Graha Phal)",
    "RASHI_PHAL":  "Doubtful Fate (Rashi Phal)",
    "HYBRID":      "Fixed + Conditional (Hybrid)",
    "CONTEXTUAL":  "Contextual / Karmic (Karma Phal)",
    "NEUTRAL":     "Positional Baseline (Neutral)",
}


# ============================================================================
# SECTION 1: PLANETS — CORE LISTS
# ============================================================================

#: All 9 standard Lal Kitab planets (excludes Lagna/Asc from most calculations)
STANDARD_PLANETS: list[str] = [
    "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"
]

STANDARD_PLANETS_SET: frozenset[str] = frozenset(STANDARD_PLANETS)


# ============================================================================
# SECTION 2: DIGNITIES — PAKKA GHAR, EXALTATION, DEBILITATION
# ============================================================================

#: Single canonical Pakka Ghar (permanent home) per planet — used in strength scoring
#: and sleeping-planet detection.
#: Source: Lal Kitab 1952 Edition, p.71
#: Cross-ref: PUCCA_GHARS_EXTENDED (broader remedy targets), FIXED_HOUSE_LORDS (reverse map)
PLANET_PAKKA_GHAR: dict[str, int] = {
    "Sun":     1,
    "Moon":    4,
    "Mars":    3,
    "Mercury": 7,
    "Jupiter": 2,
    "Venus":   7,
    "Saturn":  10,
    "Rahu":    12,
    "Ketu":    6,
}

#: Extended Pucca Ghars — all "safe" houses for each planet, used for remedy shifting.
#: Broader than PLANET_PAKKA_GHAR (which is a single primary house).
#: Source: Goswami remedy rules + Lal Kitab reference houses
#: Cross-ref: PLANET_PAKKA_GHAR (primary/single), PLANET_EXALTATION (dignity)
PUCCA_GHARS_EXTENDED: dict[str, list[int]] = {
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

#: Houses where each planet is Exalted (high dignity).
#: Rahu and Ketu have multiple exaltation houses.
#: Cross-ref: PLANET_DEBILITATION (opposite), PLANET_PAKKA_GHAR (permanent home)
PLANET_EXALTATION: dict[str, list[int]] = {
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

#: Houses where each planet is Debilitated (weakened).
#: Cross-ref: PLANET_EXALTATION (opposite), PLANET_PAKKA_GHAR
PLANET_DEBILITATION: dict[str, list[int]] = {
    "Sun":     [7],
    "Moon":    [8],
    "Mars":    [4],
    "Mercury": [12],
    "Jupiter": [10],
    "Venus":   [6],
    "Saturn":  [1],
    "Rahu":    [9, 12],
    "Ketu":    [3, 6],
}

#: Reverse map: house → [planets that are Fixed House Lords of that house].
#: Used to award the "Fixed House Lord" dignity bonus in strength calculation.
#: Cross-ref: PLANET_PAKKA_GHAR (forward map)
FIXED_HOUSE_LORDS: dict[int, list[str]] = {
    1:  ["Sun"],
    2:  ["Jupiter"],
    3:  ["Mars"],
    4:  ["Moon"],
    5:  ["Jupiter"],
    6:  ["Ketu"],
    7:  ["Venus", "Mercury"],  # Mercury's Pakka Ghar is H7 (see PLANET_PAKKA_GHAR)
    8:  ["Mars", "Saturn"],
    9:  ["Jupiter"],
    10: ["Saturn"],
    11: ["Jupiter"],
    12: ["Rahu"],
}


# ============================================================================
# SECTION 3: PLANET RELATIONSHIPS
# ============================================================================

#: Complete natural planet relationships: Friends, Enemies, and Even (neutral).
#: Source: Lal Kitab p.71
#: Cross-ref: FRIENDS (simple list), ENEMIES (simple list), ASPECT_STRENGTH_DATA
NATURAL_RELATIONSHIPS: dict[str, dict[str, list[str]]] = {
    "Jupiter": {"Friends": ["Sun", "Moon", "Mars"],       "Enemies": ["Venus", "Mercury"],          "Even": ["Rahu", "Ketu", "Saturn"]},
    "Sun":     {"Friends": ["Jupiter", "Mars", "Moon"],   "Enemies": ["Venus", "Saturn", "Rahu"],   "Even": ["Mercury", "Ketu"]},
    "Moon":    {"Friends": ["Sun", "Mercury"],             "Enemies": ["Ketu"],                      "Even": ["Venus", "Saturn", "Mars", "Jupiter", "Rahu"]},
    "Venus":   {"Friends": ["Saturn", "Mercury", "Ketu"], "Enemies": ["Sun", "Moon", "Rahu"],        "Even": ["Mars", "Jupiter"]},
    "Mars":    {"Friends": ["Sun", "Moon", "Jupiter"],    "Enemies": ["Mercury", "Ketu"],            "Even": ["Venus", "Saturn", "Rahu"]},
    "Mercury": {"Friends": ["Sun", "Venus", "Rahu"],      "Enemies": ["Moon"],                       "Even": ["Saturn", "Ketu", "Mars", "Jupiter"]},
    "Saturn":  {"Friends": ["Mercury", "Venus", "Rahu"],  "Enemies": ["Sun", "Moon", "Mars"],        "Even": ["Ketu", "Jupiter"]},
    "Rahu":    {"Friends": ["Mercury", "Saturn", "Ketu"], "Enemies": ["Sun", "Venus", "Mars"],       "Even": ["Jupiter", "Moon"]},
    "Ketu":    {"Friends": ["Venus", "Rahu"],              "Enemies": ["Moon", "Mars"],               "Even": ["Jupiter", "Saturn", "Mercury", "Sun"]},
}

#: Simple friend list per planet (subset of NATURAL_RELATIONSHIPS).
#: Cross-ref: NATURAL_RELATIONSHIPS (full including "Even"), ENEMIES
FRIENDS: dict[str, list[str]] = {p: v["Friends"] for p, v in NATURAL_RELATIONSHIPS.items()}

#: Simple enemy list per planet (subset of NATURAL_RELATIONSHIPS).
#: Cross-ref: NATURAL_RELATIONSHIPS (full including "Even"), FRIENDS
ENEMIES: dict[str, list[str]] = {p: v["Enemies"] for p, v in NATURAL_RELATIONSHIPS.items()}


# ============================================================================
# SECTION 4: SCAPEGOATS (STRENGTH REDISTRIBUTION)
# ============================================================================

#: When a planet has negative strength, its burden is redistributed to scapegoats.
#: Format: {source_planet: {target_planet: proportion_of_negative_strength}}
#: Proportions must sum to ≤ 1.0 per source. Source planet strength → 0 after distribution.
SCAPEGOATS: dict[str, dict[str, float]] = {
    "Saturn":  {"Rahu": 0.5, "Ketu": 0.3, "Venus": 0.2},
    "Mercury": {"Venus": 1.0},
    "Mars":    {"Ketu": 1.0},
    "Venus":   {"Moon": 1.0},
    "Jupiter": {"Ketu": 1.0},
    "Sun":     {"Ketu": 1.0},
    "Moon":    {"Jupiter": 0.4, "Sun": 0.3, "Mars": 0.3},
    "Rahu":    {},
    "Ketu":    {},
}


# ============================================================================
# SECTION 5: HOUSE ASPECTS
# ============================================================================

#: Complete Lal Kitab House Aspect Map.
#: Each house casts different types of aspects onto other houses.
#: Aspect types: "100 Percent" (full/direct), "50 Percent" (partial), "25 Percent" (weak),
#:               "Outside Help", "General Condition", "Confrontation", "Foundation", "Deception"
#: Note: "Confrontation" aspects are negative; "Foundation"/"Outside Help" are positive.
#: Cross-ref: HOUSE_ASPECT_TARGETS (simple target-house list), ASPECT_STRENGTH_DATA (strength matrix)
HOUSE_ASPECT_DATA: dict[int, dict[str, Any]] = {
    1:  {"100 Percent": 7, "Outside Help": 5, "General Condition": 7, "Confrontation": 8, "Foundation": 9,  "Deception": 10},
    2:  {"25 Percent":  6, "Outside Help": 6, "General Condition": 8, "Confrontation": 9, "Foundation": 10, "Deception": 11},
    3:  {"50 Percent":  [9, 11], "Outside Help": 7, "General Condition": 9, "Confrontation": 10, "Foundation": 11, "Deception": 12},
    4:  {"100 Percent": 10, "Outside Help": 8, "General Condition": 10, "Confrontation": 11, "Foundation": 12, "Deception": 1},
    5:  {"50 Percent":  9, "Outside Help": 9, "General Condition": 11, "Confrontation": 12, "Foundation": 1,  "Deception": 2},
    6:  {"Outside Help": 10, "General Condition": 12, "Confrontation": 1, "Foundation": 2,  "Deception": 3},
    7:  {"Outside Help": 11, "General Condition": 1,  "Confrontation": 2, "Foundation": 3,  "Deception": 4},
    8:  {"25 Percent":  2, "Outside Help": 12, "General Condition": 2, "Confrontation": 3, "Foundation": 4,  "Deception": 5},
    9:  {"Outside Help": 1, "General Condition": 3,  "Confrontation": 4, "Foundation": 5,  "Deception": 6},
    10: {"Outside Help": 2, "General Condition": 4,  "Confrontation": 5, "Foundation": 6,  "Deception": 7},
    11: {"Outside Help": 3, "General Condition": 5,  "Confrontation": 6, "Foundation": 7,  "Deception": 8},
    12: {"Outside Help": 4, "General Condition": 6,  "Confrontation": 7, "Foundation": 8,  "Deception": 9},
}

#: Derived simple lookup: source_house → list of all aspected houses (significant aspects only).
#: Used for sleeping-planet detection and Mangal Badh checks.
#: Includes: "100 Percent", "50 Percent", "25 Percent", "Outside Help"
#: Cross-ref: HOUSE_ASPECT_DATA (full detail)
HOUSE_ASPECT_TARGETS: dict[int, list[int]] = {}
_SIGNIFICANT_TYPES = {"100 Percent", "50 Percent", "25 Percent", "Outside Help"}
for _h, _v in HOUSE_ASPECT_DATA.items():
    _targets: list[int] = []
    for _a_type in _SIGNIFICANT_TYPES:
        _t = _v.get(_a_type)
        if isinstance(_t, int):
            _targets.append(_t)
        elif isinstance(_t, list):
            _targets.extend(_t)
    HOUSE_ASPECT_TARGETS[_h] = sorted(set(_targets))


#: Planet-vs-planet aspect strength matrix — indexed by CASTER then RECEIVER.
#: Read as: ASPECT_STRENGTH_DATA[casting_planet][receiving_planet] = strength_value
#: The relationship is ASYMMETRIC: Jupiter casting on Sun (2.0) ≠ Sun casting on Jupiter (0.667).
#: Negative values indicate malefic aspects. Used in raw aspect strength calculations.
#: Cross-ref: ASPECT_STRENGTH_RECEIVED (transposed / receiver-first view), NATURAL_RELATIONSHIPS
ASPECT_STRENGTH_DATA: dict[str, dict[str, float]] = {
    #                    Jup       Sun       Moon      Venus     Mars      Mercury   Saturn    Rahu      Ketu
    "Jupiter": {"Jupiter": 0,    "Sun": 2,       "Moon": 0.5,    "Venus": 3.75,    "Mars": 2,       "Mercury": 2,      "Saturn": 3,       "Rahu": 2,    "Ketu": 0.83333},
    "Sun":     {"Jupiter": 0.666667, "Sun": 0,   "Moon": 0.75,   "Venus": 0.75,   "Mars": 2,       "Mercury": 0.5,    "Saturn": -5,      "Rahu": -5,   "Ketu": 0.5},
    "Moon":    {"Jupiter": 2,    "Sun": 2,       "Moon": 0,      "Venus": 2,      "Mars": 1,       "Mercury": 2,      "Saturn": 0.333333,"Rahu": 0.5,  "Ketu": -5},
    "Venus":   {"Jupiter": 0.5,  "Sun": 0.75,    "Moon": 0.5,    "Venus": 0,      "Mars": 1.333333,"Mercury": 1,      "Saturn": 0.333333,"Rahu": 2,    "Ketu": 2},
    "Mars":    {"Jupiter": 2,    "Sun": 2,       "Moon": 2,      "Venus": 0.333333,"Mars": 0,       "Mercury": 2,      "Saturn": 1.333333,"Rahu": 0,    "Ketu": 0.5},
    "Mercury": {"Jupiter": 0.5,  "Sun": 2,       "Moon": 0.5,    "Venus": 1,      "Mars": 1,       "Mercury": 0,      "Saturn": 1.25,    "Rahu": 2,    "Ketu": 0.25},
    "Saturn":  {"Jupiter": 1.25, "Sun": 0.666667,"Moon": 0.333333,"Venus": 1.333333,"Mars": 0.333333,"Mercury": 0.8,   "Saturn": 0,       "Rahu": 2,    "Ketu": 0.5},
    "Rahu":    {"Jupiter": 0,    "Sun": -5,      "Moon": 0.5,    "Venus": 0.5,    "Mars": 1,       "Mercury": 2,      "Saturn": 2,       "Rahu": 0,    "Ketu": 1},
    "Ketu":    {"Jupiter": 2,    "Sun": 0.5,     "Moon": -5,     "Venus": 2,      "Mars": 0.5,     "Mercury": 0.75,   "Saturn": 2,       "Rahu": 1,    "Ketu": 0},
}

#: Transposed / receiver-first view of ASPECT_STRENGTH_DATA.
#: Read as: ASPECT_STRENGTH_RECEIVED[receiving_planet][casting_planet] = strength_value
#:
#: Use this when the question is "how strongly is Mars being aspected by Saturn?"
#:   → ASPECT_STRENGTH_RECEIVED["Mars"]["Saturn"] = 0.333333
#: versus the forward question "how strong is Saturn's aspect on Mars?"
#:   → ASPECT_STRENGTH_DATA["Saturn"]["Mars"] = 0.333333   (same value, different lookup path)
#:
#: Important: values are identical to ASPECT_STRENGTH_DATA — this is purely a lookup convenience.
#: Do NOT edit this directly; edit ASPECT_STRENGTH_DATA above and this will stay in sync.
#: Cross-ref: ASPECT_STRENGTH_DATA (caster-first / authoritative source)
ASPECT_STRENGTH_RECEIVED: dict[str, dict[str, float]] = {
    receiver: {
        caster: ASPECT_STRENGTH_DATA[caster][receiver]
        for caster in ASPECT_STRENGTH_DATA
    }
    for receiver in ASPECT_STRENGTH_DATA
}


# ============================================================================
# SECTION 6: SUDDEN STRIKE (ACHANAK CHOT) HOUSE PAIRS
# ============================================================================

#: House pairs that form potential Sudden Strike relationships in the Natal Chart.
#: If planets sit in these paired houses at birth, and aspect each other in an annual
#: chart, an Achanak Chot (Sudden Strike) is triggered.
#: Cross-ref: HOUSE_ASPECT_TARGETS (for aspect detection)
SUDDEN_STRIKE_HOUSE_PAIRS: list[set[int]] = [
    {1, 3}, {2, 4}, {4, 6}, {5, 7}, {7, 9}, {8, 10}, {10, 12}, {1, 11}
]


# ============================================================================
# SECTION 7: GRAMMAR RULES — FOUNDATIONAL HOUSES & DISPOSITION RULES
# ============================================================================

#: Foundational (associated) houses per planet — used in BilMukabil detection.
#: A planet in an enemy's foundational house triggers the hostile condition.
#: Cross-ref: PLANET_PAKKA_GHAR (primary home), PUCCA_GHARS_EXTENDED (remedy targets)
FOUNDATIONAL_HOUSES: dict[str, list[int]] = {
    "Sun":     [1, 5],
    "Moon":    [4],
    "Mars":    [1, 3, 8],
    "Mercury": [3, 6, 7],
    "Jupiter": [2, 5, 9, 11, 12],
    "Venus":   [2, 7],
    "Saturn":  [8, 10, 11],
    "Rahu":    [11, 12],
    "Ketu":    [6],
}

#: All 19 Lal Kitab planet disposition rules.
#: Format: (causer_planet, causer_houses, affected_planet, effect)
#:   - causer_houses: list of houses; rule fires if causer is in ANY of these houses
#:   - effect: "Good" (boosts affected) or "Bad" (penalises affected)
#: Causer's absolute strength is added/subtracted from affected planet's strength_total.
#: Cross-ref: NATURAL_RELATIONSHIPS (relationship context), SCAPEGOATS (redistribution)
DISPOSITION_RULES: list[tuple[str, list[int], str, str]] = [
    # (causer_planet, causer_houses, affected_planet, effect)
    ("Jupiter",  [7],           "Venus",   "Bad"),
    ("Rahu",     [11],          "Jupiter", "Bad"),
    ("Rahu",     [12],          "Jupiter", "Bad"),
    ("Sun",      [6],           "Saturn",  "Bad"),
    ("Sun",      [10],          "Mars",    "Bad"),
    ("Sun",      [10],          "Ketu",    "Bad"),
    ("Sun",      [11],          "Mars",    "Bad"),
    ("Moon",     [1, 3, 8],     "Mars",    "Good"),
    ("Venus",    [9],           "Mars",    "Bad"),
    ("Venus",    [2, 5, 12],    "Jupiter", "Bad"),
    ("Mercury",  [3, 6, 8, 12], "Moon",    "Bad"),
    ("Mercury",  [2, 5, 9],     "Jupiter", "Bad"),
    ("Saturn",   [4, 6, 10],    "Moon",    "Bad"),
    ("Rahu",     [2, 5, 6, 9],  "Jupiter", "Bad"),
    ("Ketu",     [11, 12],      "Jupiter", "Bad"),
    ("Ketu",     [11, 12],      "Mars",    "Bad"),
    ("Ketu",     [11, 12],      "Venus",   "Good"),
    ("Moon",     [6],           "Mars",    "Bad"),
    ("Moon",     [6],           "Venus",   "Good"),
]

#: Lal Kitab Debt (Rin) rules. A debt is active if ANY of the listed planets
#: sits in ANY of the listed houses.
#: Format: (debt_name, [planet_triggers], [house_triggers])
#: Cross-ref: FOUNDATIONAL_HOUSES (related), DISPOSITION_RULES (related karma rules)
RIN_RULES: list[tuple[str, list[str], list[int]]] = [
    ("Ancestral Debt (Pitra Rin)",              ["Venus", "Mercury", "Rahu"], [2, 5, 9, 12]),
    ("Self Debt (Swayam Rin)",                  ["Venus", "Rahu"],            [5]),
    ("Maternal Debt (Matri Rin)",               ["Ketu"],                     [4]),
    ("Family/Wife/Woman Debt (Stri Rin)",       ["Sun", "Rahu", "Ketu"],      [2, 7]),
    ("Relative/Brother Debt (Bhai-Bandhu Rin)", ["Mercury", "Ketu"],          [1, 8]),
    ("Daughter/Sister Debt (Behen/Beti Rin)",   ["Moon"],                     [3, 6]),
    ("Oppression/Atrocious Debt (Zulm Rin)",    ["Sun", "Moon", "Mars"],      [10, 11]),
    ("Debt of the Unborn (Ajanma Rin)",         ["Venus", "Sun", "Rahu"],     [12]),
    ("Negative Speech Debt (Manda Bol Rin)",    ["Moon", "Mars", "Ketu"],     [6]),
]


# ============================================================================
# SECTION 8: MASNUI (ARTIFICIAL) PLANETS
# ============================================================================

#: Masnui (artificial) planet formation rules.
#: A Masnui planet is formed when a specific pair of planets are conjunct (same house).
#: Format: (frozenset({planet_a_lower, planet_b_lower}), "Artificial Planet Name")
#: Usage: iterate and check if frozenset(house_occupants) == required_set
#: Cross-ref: MASNUI_TO_STANDARD (reverse map to base planet)
MASNUI_FORMATION_RULES: list[tuple[frozenset[str], str]] = [
    (frozenset({"sun",     "venus"}),   "Artificial Jupiter"),
    (frozenset({"mercury", "venus"}),   "Artificial Sun"),
    (frozenset({"sun",     "jupiter"}), "Artificial Moon"),
    (frozenset({"rahu",    "ketu"}),    "Artificial Venus (Note: Unusual Conjunction)"),
    (frozenset({"sun",     "mercury"}), "Artificial Mars (Auspicious)"),
    (frozenset({"sun",     "saturn"}),  "Artificial Mars (Malefic)"),
    (frozenset({"sun",     "saturn"}),  "Artificial Rahu (Debilitated Rahu)"),
    (frozenset({"jupiter", "rahu"}),    "Artificial Mercury"),
    (frozenset({"venus",   "jupiter"}), "Artificial Saturn (Like Ketu)"),
    (frozenset({"mars",    "mercury"}), "Artificial Saturn (Like Rahu)"),
    (frozenset({"saturn",  "mars"}),    "Artificial Rahu (Exalted Rahu)"),
    (frozenset({"venus",   "saturn"}),  "Artificial Ketu (Exalted Ketu)"),
    (frozenset({"moon",    "saturn"}),  "Artificial Ketu (Debilitated Ketu)"),
]

#: Maps Masnui (artificial) planet names → their base standard planet.
#: Used for applying relationship and enemy checks via the standard planet.
#: Cross-ref: MASNUI_FORMATION_RULES (forward), NATURAL_RELATIONSHIPS, ENEMIES
MASNUI_TO_STANDARD: dict[str, str] = {
    "Artificial Jupiter":                  "Jupiter",
    "Artificial Sun":                      "Sun",
    "Artificial Moon":                     "Moon",
    "Artificial Venus (Note: Unusual Conjunction)": "Venus",
    "Artificial Mars (Auspicious)":        "Mars",
    "Artificial Mars (Malefic)":           "Mars",
    "Artificial Mercury":                  "Mercury",
    "Artificial Saturn (Like Ketu)":       "Saturn",
    "Artificial Saturn (Like Rahu)":       "Saturn",
    "Artificial Rahu (Debilitated Rahu)":  "Rahu",
    "Artificial Rahu (Exalted Rahu)":      "Rahu",
    "Artificial Ketu (Exalted Ketu)":      "Ketu",
    "Artificial Ketu (Debilitated Ketu)":  "Ketu",
}


# ============================================================================
# SECTION 9: 35-YEAR PLANETARY CYCLE
# ============================================================================

#: 35-year life cycle period rulers.
#: Lal Kitab divides each 35-year cycle into sub-periods ruled by specific planets.
#: Format: list of (start_period, end_period, ruling_planet) — inclusive ranges.
#: Usage: for a given age, compute period = (age - 1) % 35 + 1, then match range.
#: Cross-ref: PLANET_EFFECTIVE_AGES (planet maturity ages, different concept)
CYCLE_35_YEAR_RANGES: list[tuple[int, int, str]] = [
    (1,  6,  "Saturn"),
    (7,  12, "Rahu"),
    (13, 15, "Ketu"),
    (16, 21, "Jupiter"),
    (22, 23, "Sun"),
    (24, 24, "Moon"),
    (25, 27, "Venus"),
    (28, 33, "Mars"),
    (34, 35, "Mercury"),
]


def get_35_year_ruler(age: int) -> str:
    """
    Returns the ruling planet for a given age in the 35-year Lal Kitab cycle.

    Args:
        age: The annual chart period (1-based age of life).

    Returns:
        Planet name string, or "" if age <= 0.

    Cross-ref: CYCLE_35_YEAR_RANGES
    """
    if age <= 0:
        return ""
    period = (age - 1) % 35 + 1
    for start, end, planet in CYCLE_35_YEAR_RANGES:
        if start <= period <= end:
            return planet
    return ""


# ============================================================================
# SECTION 10: PLANET EFFECTIVE (MATURITY) AGES
# ============================================================================

#: Age at which each planet's energy fully matures in a person's life.
#: Used in research agent for identifying timing rationale and delays.
#: Cross-ref: CYCLE_35_YEAR_RANGES (cycle context), DOMAIN_HOUSE_MAP (life domains)
PLANET_EFFECTIVE_AGES: dict[str, int] = {
    "Jupiter": 16,
    "Sun":     22,
    "Moon":    24,
    "Venus":   25,
    "Mars":    28,
    "Mercury": 34,
    "Saturn":  36,
    "Rahu":    42,
    "Ketu":    48,
}


# ============================================================================
# SECTION 11: LIFE DOMAINS
# ============================================================================

#: Canonical Lal Kitab domain → house mapping.
#: Primary houses are directly responsible; secondary houses are supporting.
#: Cross-ref: DOMAIN_ALIASES (alternate spelling normalisation)
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

#: Alternate domain label → canonical domain key normalisation.
#: Cross-ref: DOMAIN_HOUSE_MAP (canonical keys)
DOMAIN_ALIASES: dict[str, str] = {
    "profession":    "career",
    "vocation":      "career",
    "matrimony":     "marriage",
    "spouse":        "marriage",
    "ill-health":    "health",
    "disease":       "health",
    "children":      "progeny",
    "offspring":     "progeny",
    "abroad":        "foreign",
    "foreign_travel": "foreign",
    "gains":         "wealth",
    "income":        "wealth",
    "money":         "wealth",
}

#: Life area → constituent planets for aggregate strength analysis.
#: Used by RemedyEngine to project life area improvement potential.
#: Cross-ref: DOMAIN_HOUSE_MAP (life area to houses)
LIFE_AREA_PLANETS: dict[str, list[str]] = {
    "Wealth & Prosperity": ["Jupiter", "Venus", "Mercury"],
    "Health & Vitality":   ["Sun", "Mars", "Saturn"],
    "Career & Status":     ["Sun", "Mars", "Jupiter"],
    "Relationships & Joy": ["Venus", "Moon", "Jupiter"],
}

#: Maps canonical domains to timing engine domains.
TIMING_DOMAIN_MAP: dict[str, str] = {
    "marriage": "marriage", 
    "finance": "finance", 
    "career": "career_travel",
    "health": "health", 
    "progeny": "progeny", 
    "property": "real_estate",
    "money": "finance"
}

#: Maps planets to their strict karaka domains for timing analysis.
KARAKA_DOMAIN_MAP: dict[str, list[str]] = {
    "Venus": ["marriage"],
    "Jupiter": ["career_travel", "progeny", "finance"],
    "Mercury": ["career_travel", "finance"],
    "Sun": ["career_travel", "health"],
    "Moon": ["health", "marriage"],
    "Mars": ["health", "career_travel"],
    "Saturn": ["career_travel", "health"],
    "Rahu": ["health", "career_travel"],
    "Ketu": ["progeny", "health"]
}


# ============================================================================
# SECTION 12: REMEDY — GOSWAMI RULES
# ============================================================================

#: Goswami companion pairs: if planet_a and planet_b are conjunct (same annual house),
#: preferred target houses are provided for planet shifting remedies.
#: Cross-ref: PUCCA_GHARS_EXTENDED (safe houses), ENEMIES (conflict detection)
GOSWAMI_PAIR_TARGETS: dict[tuple[str, str], list[int]] = {
    ("Moon",    "Jupiter"): [2, 4, 10],
    ("Jupiter", "Moon"):    [2, 4, 10],
    ("Sun",     "Moon"):    [1, 2, 4],
    ("Moon",    "Sun"):     [1, 2, 4],
    ("Mars",    "Saturn"):  [8, 10],
    ("Saturn",  "Mars"):    [8, 10],
}


# ============================================================================
# SECTION 13: PLANET HOUSE ARTICLES (REMEDY ITEMS)
# ============================================================================

#: Physical articles/items associated with each planet in each house.
#: Source: 'Items of planets.xlsx' Sheets 1, 17, 19, 21, 23
#: Used by RemedyEngine to suggest physical remedy articles for planet shifting.
#: Cross-ref: PLANET_RELATIVES (family members per planet/house)
PLANET_HOUSE_ITEMS: dict[str, dict[int, list[str]]] = {
    "Jupiter": {
        1:  ["Goldsmith", "yellow colour", "male lion", "Sadhu on the move"],
        2:  ["Cowshed", "hospitality", "worship", "wealth", "grams (pulse)", "Turmeric"],
        3:  ["Durga poojan", "education", "worldly affairs"],
        4:  ["Queen", "gold", "Rain"],
        5:  ["Nose", "saffron"],
        6:  ["Deer", "musk", "apples", "Chicken"],
        7:  ["Books", "asthma", "frog", "vagabond Sadhu", "dirty air"],
        8:  ["Rumour", "unemployment", "donation or Yagna of a Fakir"],
        9:  ["Ancestral house", "place of worship", "gas", "Temple", "Mosque", "Gurudwara"],
        10: ["Dry peepal tree", "loss of gold", "end of education", "Sulphur"],
        11: ["Sulphur with nickel (gilt)"],
        12: ["Green peepal tree", "worldly affairs", "breath"],
    },
    "Sun": {
        1:  ["Daytime", "Right side", "White salt", "Copper", "Gur"],
        2:  ["Wheat", "Barely"],
        3:  ["Progeny", "Nephews"],
        4:  ["Son of father's sister", "Right eyeball"],
        5:  ["Lone son", "Red faced monkey"],
        6:  ["Wheatish colour", "Disease of feet"],
        7:  ["Red cow"],
        8:  ["Chariot", "Self generated fire"],
        9:  ["Brown beer", "Sun after eclipse"],
        10: ["Brown Mongoose", "Brown buffalo", "stone gum"],
        11: ["Bright copper"],
        12: ["Brown ant", "Damaged brain"],
    },
    "Moon": {
        1:  ["Left eyeball", "Heart", "Silver", "Milk"],
        2:  ["Mother milk", "Rice", "White Horse"],
        3:  ["Fiery Horse", "Shiva"],
        4:  ["Well", "pool", "Spring", "Subsoil water", "peace"],
        5:  ["Patridge (Chakor)", "Swallow wort", "Milk"],
        6:  ["Male rabbit", "Travel"],
        7:  ["Agriculture land of ice"],
        8:  ["Sea", "Epilepsy", "Chicken hearted"],
        9:  ["Ancestral property", "Sea"],
        10: ["Night time", "Bitter water", "Foundation", "Bitter opium"],
        11: ["Silky Pearl-(Milky)", "Bloody well", "Floating clouds"],
        12: ["White cat", "Rain water", "Rain stone", "Camphor"],
    },
    "Mars": {
        1:  ["Teeth 32/31", "Grainstore", "Aniseed"],
        2:  ["Leopard", "Deer"],
        3:  ["Stomach", "Lips", "Chest"],
        4:  ["Deer skin", "Sword", "Dhak"],
        5:  ["Brother", "Neem tree"],
        6:  ["Partridge", "Musk Rat"],
        7:  ["Lentil", "Thymol"],
        8:  ["Body without arms"],
        9:  ["Bloody red colour"],
        10: ["Honey sweet", "Food Sugar"],
        11: ["Red colour of Vermilion"],
        12: ["Driver of loud elephant"],
    },
    "Venus": {
        1:  ["Other woman"],
        2:  ["White cow", "Female Elephant", "Ghee", "Ginger", "Camphor"],
        3:  ["Marriage", "contended wife"],
        4:  ["Curd", "Four wheeled", "Birds"],
        5:  ["Brick", "Brass utensil"],
        6:  ["Sparrows", "Eunuch"],
        7:  ["White cow", "Barley (white)"],
        8:  ["Sweet Potato", "Carrot"],
        9:  ["Curds colour"],
        10: ["Sweet", "Cotton"],
        11: ["Cotton", "white colour", "Pearl", "Curd"],
        12: ["Kamdhenu cow", "Lakshmi's foot", "Family", "wife comfort"],
    },
    "Mercury": {
        1:  ["Tongue", "Skull"],
        2:  ["Kidney Beans", "Sister-in-law", "Musical instruments", "peas"],
        3:  ["Brother's daughter", "Bat", "Cactus", "Termite"],
        4:  ["Parrot", "Soldering metal", "Vertical egg", "Father's sister"],
        5:  ["Bamboo", "Milch goat", "Grand daughter"],
        6:  ["Fruit", "Daughter", "Grand daughter", "Vertical egg"],
        7:  ["Green grass", "Cow without tail", "Female parrot"],
        8:  ["Lying egg", "Dead body", "Flower", "Sister"],
        9:  ["Ghosts", "Bat", "Green colour forest", "Lisping"],
        10: ["Teeth", "Dry grass", "Liquor", "Stairs", "Musical Drums", "Heeng"],
        11: ["Parrot", "Seashell", "Alum", "Diamond"],
        12: ["Egg", "Toys", "Dirty egg"],
    },
    "Saturn": {
        1:  ["Crow", "Black Salt", "Acacia (Kikkar)", "Insects"],
        2:  ["Full Black pulse", "Black paper", "Black grams", "Sandalwood"],
        3:  ["Butte Frondosa (Dhaak Tree)", "Precious wood", "Mulberry"],
        4:  ["Black insects", "oil", "Marble", "Wood of Diyar and pine"],
        5:  ["Black antimony", "Stupid son"],
        6:  ["Crow", "Kite", "Plum", "Coal", "Stone", "Cotton seeds"],
        7:  ["Black cow", "White antimony", "Eyes", "Condiments"],
        8:  ["Scorpion", "Walls without roof", "Temple (Body)"],
        9:  ["Old wood", "Swallow-Wort-(Aak)", "Seesam Tree"],
        10: ["Crocodile", "Snake", "Oil", "Soap", "Laundry"],
        11: ["Iron", "Steel", "Tin"],
        12: ["Artificial copper", "Fish", "Almonds", "Baldness"],
    },
    "Rahu": {
        1:  ["Chin", "Mother's parents"],
        2:  ["Soil of elephant feet", "Mustard", "Raw smoke"],
        3:  ["Lower position of tongue", "Elephant"],
        4:  ["Dream time", "Coriander"],
        5:  ["Roof"],
        6:  ["Pitch black dog"],
        7:  ["Coconut"],
        8:  ["Swing", "disease", "Smoke of Chimney", "Agate"],
        9:  ["Watch", "Door step", "Blue colour"],
        10: ["Latrine", "Outlet for dirty water", "Roasting furnace"],
        11: ["Blue sapphire", "Aluminium", "Zinc", "copper Sulphate"],
        12: ["Elephant", "Sea Tendua", "Raw Coal"],
    },
    "Ketu": {
        1:  ["Leg", "Maternal House"],
        2:  ["Tamarind", "Sesame"],
        3:  ["Spinal chord", "Boils"],
        4:  ["Hearing", "Ears"],
        5:  ["Urinal"],
        6:  ["Male sparrow", "Rabbit", "Onion", "Bedstead", "Garlic"],
        7:  ["Second son", "Donkey", "Pig"],
        8:  ["Ear", "Hearing power", "Deceiving nature"],
        9:  ["Two coloured dog"],
        10: ["Rat", "Mouse"],
        11: ["Twin coloured stone (black and white)"],
        12: ["Lizard", "Adopted Son", "bed", "Banana"],
    },
}

#: Relatives/family members associated with each planet in specific houses.
#: Source: 'Items of planets.xlsx' Sheet 21
#: Cross-ref: PLANET_HOUSE_ITEMS (physical articles)
PLANET_RELATIVES: dict[str, dict[int, str]] = {
    "Jupiter": {1: "Father/Grandfather",  2: "In-laws of woman", 3: "Head of Family",   4: "Magnanimous father"},
    "Sun":     {1: "Self",                2: "Religious minister", 3: "Aggressive friend", 9: "Kind friend"},
    "Moon":    {1: "Queen",               4: "Mother or her sister", 6: "Mother's mother"},
    "Venus":   {1: "Wife/Husband",        7: "Life long spouse"},
    "Mars":    {1: "Brother",             2: "Elder brother",     7: "Real brother"},
    "Mercury": {1: "Eldest daughter",     3: "Elder sister",      6: "Own daughter"},
    "Saturn":  {1: "Officer",             7: "Helpful person",    10: "Honorable paternal uncle"},
    "Rahu":    {2: "Father-in-law",       3: "Sincere friend",    4: "Maternal uncle"},
    "Ketu":    {1: "Lone son",            3: "Brother's son",     7: "Second son",       9: "Loyal son"},
}


# ============================================================================
# SECTION 14: VARSHPHAL (ANNUAL CHART) 120-YEAR MOVEMENT MATRIX
# ============================================================================
#
# Authentic 120-Year Lal Kitab Varshphal Movement Matrix (1952 Edition).
# Maps: Age (year of life) → {Natal House → Annual House}
# Usage: annual_house = VARSHPHAL_YEAR_MATRIX[age][natal_house]
# Only years 1–75 are typically used (as the pipeline generates up to 75 annual charts).
# Years 76–120 are included for completeness and future extension.
# Cross-ref: PLANET_PAKKA_GHAR, PLANET_EXALTATION (for annual dignity calculation)

VARSHPHAL_YEAR_MATRIX: dict[int, dict[int, int]] = {
    1:   {1: 1,  2: 9,  3: 10, 4: 3,  5: 5,  6: 2,  7: 11, 8: 7,  9: 6,  10: 12, 11: 4,  12: 8},
    2:   {1: 4,  2: 1,  3: 12, 4: 9,  5: 3,  6: 7,  7: 5,  8: 6,  9: 2,  10: 8,  11: 10, 12: 11},
    3:   {1: 9,  2: 4,  3: 1,  4: 2,  5: 8,  6: 3,  7: 10, 8: 5,  9: 7,  10: 11, 11: 12, 12: 6},
    4:   {1: 3,  2: 8,  3: 4,  4: 1,  5: 10, 6: 9,  7: 6,  8: 11, 9: 5,  10: 7,  11: 2,  12: 12},
    5:   {1: 11, 2: 3,  3: 8,  4: 4,  5: 1,  6: 5,  7: 9,  8: 2,  9: 12, 10: 6,  11: 7,  12: 10},
    6:   {1: 5,  2: 12, 3: 3,  4: 8,  5: 4,  6: 11, 7: 2,  8: 9,  9: 1,  10: 10, 11: 6,  12: 7},
    7:   {1: 7,  2: 6,  3: 9,  4: 5,  5: 12, 6: 4,  7: 1,  8: 10, 9: 11, 10: 2,  11: 8,  12: 3},
    8:   {1: 2,  2: 7,  3: 6,  4: 12, 5: 9,  6: 10, 7: 3,  8: 1,  9: 8,  10: 5,  11: 11, 12: 4},
    9:   {1: 12, 2: 2,  3: 7,  4: 6,  5: 11, 6: 1,  7: 8,  8: 4,  9: 10, 10: 3,  11: 5,  12: 9},
    10:  {1: 10, 2: 11, 3: 2,  4: 7,  5: 6,  6: 12, 7: 4,  8: 8,  9: 3,  10: 1,  11: 9,  12: 5},
    11:  {1: 8,  2: 5,  3: 11, 4: 10, 5: 7,  6: 6,  7: 12, 8: 3,  9: 9,  10: 4,  11: 1,  12: 2},
    12:  {1: 6,  2: 10, 3: 5,  4: 11, 5: 2,  6: 8,  7: 7,  8: 12, 9: 4,  10: 9,  11: 3,  12: 1},
    13:  {1: 1,  2: 5,  3: 10, 4: 8,  5: 11, 6: 6,  7: 7,  8: 2,  9: 12, 10: 3,  11: 9,  12: 4},
    14:  {1: 4,  2: 1,  3: 3,  4: 2,  5: 5,  6: 7,  7: 8,  8: 11, 9: 6,  10: 12, 11: 10, 12: 9},
    15:  {1: 9,  2: 4,  3: 1,  4: 6,  5: 8,  6: 5,  7: 2,  8: 7,  9: 11, 10: 10, 11: 12, 12: 3},
    16:  {1: 3,  2: 9,  3: 4,  4: 1,  5: 12, 6: 8,  7: 6,  8: 5,  9: 2,  10: 7,  11: 11, 12: 10},
    17:  {1: 11, 2: 3,  3: 9,  4: 4,  5: 1,  6: 10, 7: 5,  8: 6,  9: 7,  10: 8,  11: 2,  12: 12},
    18:  {1: 5,  2: 11, 3: 6,  4: 9,  5: 4,  6: 1,  7: 12, 8: 8,  9: 10, 10: 2,  11: 3,  12: 7},
    19:  {1: 7,  2: 10, 3: 11, 4: 3,  5: 9,  6: 4,  7: 1,  8: 12, 9: 8,  10: 5,  11: 6,  12: 2},
    20:  {1: 2,  2: 7,  3: 5,  4: 12, 5: 3,  6: 9,  7: 10, 8: 1,  9: 4,  10: 6,  11: 8,  12: 11},
    21:  {1: 12, 2: 2,  3: 8,  4: 5,  5: 10, 6: 3,  7: 9,  8: 4,  9: 1,  10: 11, 11: 7,  12: 6},
    22:  {1: 10, 2: 12, 3: 2,  4: 7,  5: 6,  6: 11, 7: 3,  8: 9,  9: 5,  10: 1,  11: 4,  12: 8},
    23:  {1: 8,  2: 6,  3: 12, 4: 10, 5: 7,  6: 2,  7: 11, 8: 3,  9: 9,  10: 4,  11: 1,  12: 5},
    24:  {1: 6,  2: 8,  3: 7,  4: 11, 5: 2,  6: 12, 7: 4,  8: 10, 9: 3,  10: 9,  11: 5,  12: 1},
    25:  {1: 1,  2: 6,  3: 10, 4: 3,  5: 2,  6: 8,  7: 7,  8: 4,  9: 11, 10: 5,  11: 12, 12: 9},
    26:  {1: 4,  2: 1,  3: 3,  4: 8,  5: 6,  6: 7,  7: 2,  8: 11, 9: 12, 10: 9,  11: 5,  12: 10},
    27:  {1: 9,  2: 4,  3: 1,  4: 5,  5: 10, 6: 11, 7: 12, 8: 7,  9: 6,  10: 8,  11: 2,  12: 3},
    28:  {1: 3,  2: 9,  3: 4,  4: 1,  5: 11, 6: 5,  7: 6,  8: 8,  9: 7,  10: 2,  11: 10, 12: 12},
    29:  {1: 11, 2: 3,  3: 9,  4: 4,  5: 1,  6: 6,  7: 8,  8: 2,  9: 10, 10: 12, 11: 7,  12: 5},
    30:  {1: 5,  2: 11, 3: 8,  4: 9,  5: 4,  6: 1,  7: 3,  8: 12, 9: 2,  10: 10, 11: 6,  12: 7},
    31:  {1: 7,  2: 5,  3: 11, 4: 12, 5: 9,  6: 4,  7: 1,  8: 10, 9: 8,  10: 6,  11: 3,  12: 2},
    32:  {1: 2,  2: 7,  3: 5,  4: 11, 5: 3,  6: 12, 7: 10, 8: 6,  9: 4,  10: 1,  11: 9,  12: 8},
    33:  {1: 12, 2: 2,  3: 6,  4: 10, 5: 8,  6: 3,  7: 9,  8: 1,  9: 5,  10: 7,  11: 4,  12: 11},
    34:  {1: 10, 2: 12, 3: 2,  4: 7,  5: 5,  6: 9,  7: 11, 8: 3,  9: 1,  10: 4,  11: 8,  12: 6},
    35:  {1: 8,  2: 10, 3: 12, 4: 6,  5: 7,  6: 2,  7: 4,  8: 5,  9: 9,  10: 3,  11: 11, 12: 1},
    36:  {1: 6,  2: 8,  3: 7,  4: 2,  5: 12, 6: 10, 7: 5,  8: 9,  9: 3,  10: 11, 11: 1,  12: 4},
    37:  {1: 1,  2: 3,  3: 10, 4: 6,  5: 9,  6: 12, 7: 7,  8: 5,  9: 11, 10: 2,  11: 4,  12: 8},
    38:  {1: 4,  2: 1,  3: 3,  4: 8,  5: 6,  6: 5,  7: 2,  8: 7,  9: 12, 10: 10, 11: 11, 12: 9},
    39:  {1: 9,  2: 4,  3: 1,  4: 12, 5: 8,  6: 2,  7: 10, 8: 11, 9: 6,  10: 3,  11: 5,  12: 7},
    40:  {1: 3,  2: 9,  3: 4,  4: 1,  5: 11, 6: 8,  7: 6,  8: 12, 9: 2,  10: 5,  11: 7,  12: 10},
    41:  {1: 11, 2: 7,  3: 9,  4: 4,  5: 1,  6: 6,  7: 8,  8: 2,  9: 10, 10: 12, 11: 3,  12: 5},
    42:  {1: 5,  2: 11, 3: 8,  4: 9,  5: 12, 6: 1,  7: 3,  8: 4,  9: 7,  10: 6,  11: 10, 12: 2},
    43:  {1: 7,  2: 5,  3: 11, 4: 2,  5: 3,  6: 4,  7: 1,  8: 10, 9: 8,  10: 9,  11: 12, 12: 6},
    44:  {1: 2,  2: 10, 3: 5,  4: 3,  5: 4,  6: 9,  7: 12, 8: 8,  9: 1,  10: 7,  11: 6,  12: 11},
    45:  {1: 12, 2: 2,  3: 6,  4: 5,  5: 10, 6: 7,  7: 9,  8: 1,  9: 3,  10: 11, 11: 8,  12: 4},
    46:  {1: 10, 2: 12, 3: 2,  4: 7,  5: 5,  6: 3,  7: 11, 8: 6,  9: 4,  10: 8,  11: 9,  12: 1},
    47:  {1: 8,  2: 6,  3: 12, 4: 10, 5: 7,  6: 11, 7: 4,  8: 9,  9: 5,  10: 1,  11: 2,  12: 3},
    48:  {1: 6,  2: 8,  3: 7,  4: 11, 5: 2,  6: 10, 7: 5,  8: 3,  9: 9,  10: 4,  11: 1,  12: 12},
    49:  {1: 1,  2: 7,  3: 10, 4: 6,  5: 12, 6: 2,  7: 8,  8: 4,  9: 11, 10: 9,  11: 3,  12: 5},
    50:  {1: 4,  2: 1,  3: 8,  4: 3,  5: 6,  6: 12, 7: 5,  8: 11, 9: 2,  10: 7,  11: 10, 12: 9},
    51:  {1: 9,  2: 4,  3: 1,  4: 2,  5: 8,  6: 3,  7: 12, 8: 6,  9: 7,  10: 10, 11: 5,  12: 11},
    52:  {1: 3,  2: 9,  3: 4,  4: 1,  5: 11, 6: 7,  7: 2,  8: 12, 9: 5,  10: 8,  11: 6,  12: 10},
    53:  {1: 11, 2: 10, 3: 7,  4: 4,  5: 1,  6: 6,  7: 3,  8: 9,  9: 12, 10: 5,  11: 8,  12: 2},
    54:  {1: 5,  2: 11, 3: 3,  4: 9,  5: 4,  6: 1,  7: 6,  8: 2,  9: 10, 10: 12, 11: 7,  12: 8},
    55:  {1: 7,  2: 5,  3: 11, 4: 8,  5: 3,  6: 9,  7: 1,  8: 10, 9: 6,  10: 4,  11: 2,  12: 12},
    56:  {1: 2,  2: 3,  3: 5,  4: 11, 5: 9,  6: 4,  7: 10, 8: 1,  9: 8,  10: 6,  11: 12, 12: 7},
    57:  {1: 12, 2: 2,  3: 6,  4: 5,  5: 10, 6: 8,  7: 9,  8: 7,  9: 4,  10: 11, 11: 1,  12: 3},
    58:  {1: 10, 2: 12, 3: 2,  4: 7,  5: 5,  6: 11, 7: 4,  8: 8,  9: 3,  10: 1,  11: 9,  12: 6},
    59:  {1: 8,  2: 6,  3: 12, 4: 10, 5: 7,  6: 5,  7: 11, 8: 3,  9: 9,  10: 2,  11: 4,  12: 1},
    60:  {1: 6,  2: 8,  3: 9,  4: 12, 5: 2,  6: 10, 7: 7,  8: 5,  9: 1,  10: 3,  11: 11, 12: 4},
    61:  {1: 1,  2: 11, 3: 10, 4: 6,  5: 12, 6: 2,  7: 4,  8: 7,  9: 8,  10: 9,  11: 5,  12: 3},
    62:  {1: 4,  2: 1,  3: 6,  4: 8,  5: 3,  6: 12, 7: 2,  8: 10, 9: 9,  10: 5,  11: 7,  12: 11},
    63:  {1: 9,  2: 4,  3: 1,  4: 2,  5: 8,  6: 6,  7: 12, 8: 11, 9: 7,  10: 3,  11: 10, 12: 5},
    64:  {1: 3,  2: 9,  3: 4,  4: 1,  5: 6,  6: 8,  7: 7,  8: 12, 9: 5,  10: 2,  11: 11, 12: 10},
    65:  {1: 11, 2: 2,  3: 9,  4: 4,  5: 1,  6: 5,  7: 8,  8: 3,  9: 10, 10: 12, 11: 6,  12: 7},
    66:  {1: 5,  2: 10, 3: 3,  4: 9,  5: 2,  6: 1,  7: 6,  8: 8,  9: 11, 10: 7,  11: 12, 12: 4},
    67:  {1: 7,  2: 5,  3: 11, 4: 3,  5: 10, 6: 4,  7: 1,  8: 9,  9: 12, 10: 6,  11: 8,  12: 2},
    68:  {1: 2,  2: 3,  3: 5,  4: 11, 5: 9,  6: 7,  7: 10, 8: 1,  9: 6,  10: 8,  11: 4,  12: 12},
    69:  {1: 12, 2: 8,  3: 7,  4: 5,  5: 11, 6: 3,  7: 9,  8: 4,  9: 1,  10: 10, 11: 2,  12: 6},
    70:  {1: 10, 2: 12, 3: 2,  4: 7,  5: 5,  6: 11, 7: 3,  8: 6,  9: 4,  10: 1,  11: 9,  12: 8},
    71:  {1: 8,  2: 6,  3: 12, 4: 10, 5: 7,  6: 9,  7: 11, 8: 5,  9: 2,  10: 4,  11: 3,  12: 1},
    72:  {1: 6,  2: 7,  3: 8,  4: 12, 5: 4,  6: 10, 7: 5,  8: 2,  9: 3,  10: 11, 11: 1,  12: 9},
    73:  {1: 1,  2: 4,  3: 10, 4: 6,  5: 12, 6: 11, 7: 7,  8: 8,  9: 2,  10: 5,  11: 9,  12: 3},
    74:  {1: 4,  2: 2,  3: 3,  4: 8,  5: 6,  6: 12, 7: 1,  8: 11, 9: 7,  10: 10, 11: 5,  12: 9},
    75:  {1: 9,  2: 10, 3: 1,  4: 3,  5: 8,  6: 6,  7: 2,  8: 7,  9: 5,  10: 4,  11: 12, 12: 11},
    76:  {1: 3,  2: 9,  3: 6,  4: 1,  5: 2,  6: 8,  7: 5,  8: 11, 9: 11, 10: 7,  11: 10, 12: 4},
    77:  {1: 11, 2: 3,  3: 9,  4: 4,  5: 1,  6: 2,  7: 8,  8: 10, 9: 12, 10: 6,  11: 7,  12: 5},
    78:  {1: 5,  2: 11, 3: 4,  4: 9,  5: 7,  6: 1,  7: 6,  8: 2,  9: 10, 10: 12, 11: 3,  12: 8},
    79:  {1: 7,  2: 5,  3: 11, 4: 2,  5: 9,  6: 4,  7: 12, 8: 6,  9: 3,  10: 1,  11: 8,  12: 10},
    80:  {1: 2,  2: 8,  3: 5,  4: 11, 5: 4,  6: 7,  7: 10, 8: 3,  9: 1,  10: 9,  11: 6,  12: 12},
    81:  {1: 12, 2: 1,  3: 7,  4: 5,  5: 11, 6: 10, 7: 9,  8: 4,  9: 8,  10: 3,  11: 2,  12: 6},
    82:  {1: 10, 2: 12, 3: 2,  4: 7,  5: 5,  6: 3,  7: 4,  8: 9,  9: 6,  10: 8,  11: 11, 12: 1},
    83:  {1: 8,  2: 6,  3: 12, 4: 10, 5: 3,  6: 5,  7: 11, 8: 1,  9: 9,  10: 2,  11: 4,  12: 7},
    84:  {1: 6,  2: 7,  3: 8,  4: 12, 5: 10, 6: 9,  7: 3,  8: 5,  9: 4,  10: 11, 11: 1,  12: 2},
    85:  {1: 1,  2: 3,  3: 10, 4: 6,  5: 12, 6: 2,  7: 8,  8: 11, 9: 5,  10: 4,  11: 9,  12: 7},
    86:  {1: 4,  2: 1,  3: 8,  4: 3,  5: 6,  6: 12, 7: 11, 8: 2,  9: 7,  10: 9,  11: 10, 12: 5},
    87:  {1: 9,  2: 4,  3: 1,  4: 7,  5: 3,  6: 8,  7: 12, 8: 5,  9: 2,  10: 6,  11: 11, 12: 10},
    88:  {1: 3,  2: 9,  3: 4,  4: 1,  5: 8,  6: 10, 7: 2,  8: 7,  9: 12, 10: 5,  11: 6,  12: 11},
    89:  {1: 11, 2: 10, 3: 9,  4: 4,  5: 1,  6: 6,  7: 7,  8: 12, 9: 3,  10: 8,  11: 5,  12: 2},
    90:  {1: 5,  2: 11, 3: 6,  4: 9,  5: 4,  6: 1,  7: 3,  8: 8,  9: 10, 10: 2,  11: 7,  12: 12},
    91:  {1: 7,  2: 5,  3: 11, 4: 2,  5: 10, 6: 4,  7: 6,  8: 9,  9: 8,  10: 3,  11: 12, 12: 1},
    92:  {1: 2,  2: 7,  3: 5,  4: 11, 5: 9,  6: 3,  7: 10, 8: 4,  9: 1,  10: 12, 11: 8,  12: 6},
    93:  {1: 12, 2: 8,  3: 7,  4: 5,  5: 2,  6: 11, 7: 9,  8: 1,  9: 6,  10: 10, 11: 3,  12: 4},
    94:  {1: 10, 2: 12, 3: 2,  4: 8,  5: 11, 6: 5,  7: 4,  8: 6,  9: 9,  10: 7,  11: 1,  12: 3},
    95:  {1: 8,  2: 6,  3: 12, 4: 10, 5: 5,  6: 7,  7: 1,  8: 3,  9: 4,  10: 11, 11: 2,  12: 9},
    96:  {1: 6,  2: 2,  3: 3,  4: 12, 5: 7,  6: 9,  7: 5,  8: 10, 9: 11, 10: 1,  11: 4,  12: 9},
    97:  {1: 1,  2: 9,  3: 10, 4: 6,  5: 12, 6: 2,  7: 7,  8: 5,  9: 3,  10: 4,  11: 8,  12: 11},
    98:  {1: 4,  2: 1,  3: 6,  4: 8,  5: 10, 6: 12, 7: 11, 8: 2,  9: 9,  10: 7,  11: 3,  12: 5},
    99:  {1: 9,  2: 4,  3: 1,  4: 2,  5: 6,  6: 8,  7: 12, 8: 11, 9: 5,  10: 3,  11: 10, 12: 7},
    100: {1: 3,  2: 10, 3: 8,  4: 1,  5: 5,  6: 7,  7: 6,  8: 12, 9: 2,  10: 9,  11: 11, 12: 4},
    101: {1: 11, 2: 3,  3: 9,  4: 4,  5: 1,  6: 6,  7: 8,  8: 10, 9: 7,  10: 5,  11: 12, 12: 2},
    102: {1: 5,  2: 11, 3: 3,  4: 9,  5: 4,  6: 1,  7: 2,  8: 6,  9: 8,  10: 12, 11: 7,  12: 10},
    103: {1: 7,  2: 5,  3: 11, 4: 3,  5: 9,  6: 4,  7: 1,  8: 8,  9: 12, 10: 10, 11: 2,  12: 6},
    104: {1: 2,  2: 7,  3: 5,  4: 11, 5: 3,  6: 9,  7: 10, 8: 1,  9: 6,  10: 8,  11: 4,  12: 12},
    105: {1: 12, 2: 2,  3: 4,  4: 5,  5: 11, 6: 3,  7: 9,  8: 7,  9: 10, 10: 6,  11: 1,  12: 8},
    106: {1: 10, 2: 12, 3: 2,  4: 7,  5: 8,  6: 5,  7: 3,  8: 9,  9: 4,  10: 11, 11: 6,  12: 1},
    107: {1: 8,  2: 6,  3: 12, 4: 10, 5: 7,  6: 11, 7: 4,  8: 3,  9: 1,  10: 2,  11: 5,  12: 9},
    108: {1: 6,  2: 8,  3: 7,  4: 12, 5: 2,  6: 10, 7: 5,  8: 4,  9: 11, 10: 1,  11: 9,  12: 3},
    109: {1: 1,  2: 9,  3: 10, 4: 6,  5: 12, 6: 2,  7: 7,  8: 11, 9: 5,  10: 3,  11: 4,  12: 8},
    110: {1: 4,  2: 1,  3: 6,  4: 8,  5: 10, 6: 12, 7: 3,  8: 5,  9: 7,  10: 2,  11: 11, 12: 9},
    111: {1: 9,  2: 4,  3: 1,  4: 2,  5: 5,  6: 8,  7: 12, 8: 10, 9: 6,  10: 7,  11: 3,  12: 11},
    112: {1: 3,  2: 10, 3: 8,  4: 9,  5: 11, 6: 7,  7: 4,  8: 1,  9: 2,  10: 12, 11: 6,  12: 5},
    113: {1: 11, 2: 3,  3: 9,  4: 4,  5: 1,  6: 6,  7: 2,  8: 7,  9: 10, 10: 5,  11: 8,  12: 12},
    114: {1: 5,  2: 11, 3: 3,  4: 1,  5: 4,  6: 10, 7: 6,  8: 8,  9: 12, 10: 9,  11: 7,  12: 2},
    115: {1: 7,  2: 5,  3: 11, 4: 3,  5: 9,  6: 4,  7: 1,  8: 12, 9: 8,  10: 10, 11: 2,  12: 6},
    116: {1: 2,  2: 7,  3: 5,  4: 11, 5: 3,  6: 9,  7: 10, 8: 6,  9: 4,  10: 8,  11: 12, 12: 1},
    117: {1: 12, 2: 2,  3: 4,  4: 5,  5: 6,  6: 1,  7: 8,  8: 9,  9: 3,  10: 11, 11: 10, 12: 7},
    118: {1: 10, 2: 12, 3: 2,  4: 7,  5: 8,  6: 11, 7: 9,  8: 3,  9: 1,  10: 6,  11: 5,  12: 4},
    119: {1: 8,  2: 6,  3: 12, 4: 10, 5: 7,  6: 5,  7: 11, 8: 2,  9: 9,  10: 4,  11: 1,  12: 3},
    120: {1: 6,  2: 8,  3: 7,  4: 12, 5: 2,  6: 3,  7: 5,  8: 4,  9: 11, 10: 1,  11: 9,  12: 10},
}


# ============================================================================
# SECTION 15: HOUSE DIVISIONS (INNER / OUTER HALVES)
# ============================================================================

#: The 12 houses split into two symbolic halves (Purbardh / Uttarardh).
#: Houses 1–6 represent inner/personal life; houses 7–12 represent outer/worldly life.
#: Source: Lal Kitab 1952 Edition, introductory house theory
#: Cross-ref: HOUSE_BODY_PARTS (anatomical mapping per house)
HOUSE_HALF_GROUPS: dict[str, list[int]] = {
    "Inner (Purbardh)":  [1, 2, 3, 4, 5, 6],
    "Outer (Uttarardh)": [7, 8, 9, 10, 11, 12],
}

#: Descriptive metadata for each half of the horoscope.
HOUSE_HALF_METADATA: dict[str, dict[str, str]] = {
    "Inner (Purbardh)": {
        "lk_name":     "Purbardh",
        "description": "Inner / Hidden Houses",
        "life_phase":  "Early life and personal/internal development",
        "body_side":   "Right side of the body",
        "nature":      "Personal efforts, self-growth, and foundational karma",
        "activation":  "Awakened by planets placed in the Outer half (H7–H12)",
    },
    "Outer (Uttarardh)": {
        "lk_name":     "Uttarardh",
        "description": "Outer / Visible Houses",
        "life_phase":  "Later life, external affairs, and worldly interactions",
        "body_side":   "Left side of the body",
        "nature":      "Destiny, public life, spouse, and outward manifestations",
        "activation":  "Planets here naturally awaken corresponding Inner houses",
    },
}

#: Kendra (angular) houses — the four pillars of destiny.
#: Called 'Band Muthi Ke Khane' (Closed Fist / Core Houses) in Lal Kitab.
#: Planets placed here carry the strongest karmic weight of the native's life.
#: Cross-ref: HOUSE_HALF_GROUPS, PLANET_PAKKA_GHAR
KENDRA_HOUSES: list[int] = [1, 4, 7, 10]

#: Trikona (trine) houses — houses of fortune and dharma.
TRIKONA_HOUSES: list[int] = [1, 5, 9]

#: Upachaya (growth) houses — results improve over time.
UPACHAYA_HOUSES: list[int] = [3, 6, 10, 11]

#: Dusthana (difficult) houses — houses of loss, debt, and hidden struggle.
DUSTHANA_HOUSES: list[int] = [6, 8, 12]


# ============================================================================
# SECTION 16: HOUSE BODY PARTS (KAAL PURUSH ANATOMY)
# ============================================================================

#: Anatomical regions governed by each house, per the Kaal Purush (Cosmic Man) model.
#: Used in medical astrology to identify which body part is affected when
#: a planet in that house is weak, afflicted, or retrograde.
#:
#: NOTE on H6: The primary Kaal Purush association is lower abdomen / kidneys.
#: "Right Leg" appears in some derivative Lal Kitab texts as secondary; it is
#: noted here for completeness but the canonical primary remains abdomen/kidney.
#:
#: Cross-ref: PLANET_DISEASES (planet → ailments), HOUSE_HALF_METADATA (body side)
HOUSE_BODY_PARTS: dict[int, dict[str, str]] = {
    1:  {"primary": "Head, Brain, Forehead",                "secondary": "Mouth, Teeth, Tongue"},
    2:  {"primary": "Face, Right Eye",                      "secondary": "Bones, Flesh, Voice, Throat"},
    3:  {"primary": "Throat, Neck, Right Ear",              "secondary": "Right Hand, Shoulder, Respiratory Tract"},
    4:  {"primary": "Chest, Breast, Heart",                 "secondary": "Lungs, Blood"},
    5:  {"primary": "Upper Abdomen, Stomach, Spine (Back)", "secondary": "Intestines, Pancreas"},
    6:  {"primary": "Lower Abdomen, Kidneys",               "secondary": "Intestines, Genitals (upper/right); some traditions cite Right Leg"},
    7:  {"primary": "Navel, Lower Waist, Bladder",          "secondary": "Liver, Central Abdomen"},
    8:  {"primary": "Genitals (left), Excretory Organs",    "secondary": "Rectum, Liver, Left Leg (upper)"},
    9:  {"primary": "Thighs, Thigh Veins",                  "secondary": "Upper Waist, Rectum"},
    10: {"primary": "Knees, Kneecap",                       "secondary": "Bones and Flesh at the Knee Joint"},
    11: {"primary": "Calves, Shins, Left Ear",              "secondary": "Left Hand, Neck, Ankles"},
    12: {"primary": "Feet, Toes, Soles",                    "secondary": "Left Eye"},
}


# ============================================================================
# SECTION 17: PLANET DISEASES AND AILMENTS
# ============================================================================

#: Diseases and ailments governed by each planet when it is afflicted,
#: debilitated, or acting malefically in the chart.
#: Source: Lal Kitab medical astrology chapters
#:
#: For Mars, the nature of disease depends on whether it is acting benefically
#: (digestive/abdominal) or malefically (accidents, blood, force).
#: Both sets are merged under "Mars" for general use; use
#: PLANET_DISEASES_MARS_CONTEXT for context-sensitive lookups.
#:
#: Cross-ref: HOUSE_BODY_PARTS (anatomical region), PLANET_DEBILITATION (dignity states)
PLANET_DISEASES: dict[str, list[str]] = {
    "Sun": [
        "Blood pressure issues",
        "Diphtheria",
        "Eye disease (right eye)",
        "Indigestion and gastric weakness",
        "Neurological weakness",
        "Paralysis",
        "Foaming of mouth / epileptic tendencies",
    ],
    "Moon": [
        "Heart disease",
        "Constipation",
        "Intestinal and urinary diseases",
        "Headache and migraines",
        "Wind/gas formation",
        "Mental instability, anxiety, mood disorders",
        "Left eye issues",
    ],
    # Merged form — use PLANET_DISEASES_MARS_CONTEXT when Mars dignity is known.
    "Mars": [
        "Liver issues",
        "Abdominal diseases and diarrhea",
        "Bile imbalances",
        "Accidents and sudden injuries (when malefic)",
        "Blood pressure (when malefic)",
        "Paralysis and loss of physical strength (when malefic)",
    ],
    "Mercury": [
        "Brain and neurological system disorders",
        "Dental issues (damage or loss of teeth)",
        "Speech defects, stammering, or tongue disorders",
        "Loss of smell",
    ],
    "Jupiter": [
        "Liver conditions (jaundice)",
        "Obesity-related issues",
        "Respiratory issues — nose and throat",
        "Digestive weakness and flatulence",
    ],
    "Venus": [
        "Kidney and urinary tract conditions",
        "Reproductive health issues",
        "Skin diseases (leprosy, rashes)",
        "Loss of voice and throat issues",
        "Thumb or joint injuries",
    ],
    "Saturn": [
        "Chronic and long-term degenerative diseases",
        "Bone and joint pains (arthritis, rheumatism)",
        "Vision loss and eye problems",
        "Loss of hair (including eyebrows)",
        "Paralysis from cold or nerve degeneration",
    ],
    "Rahu": [
        "Mysterious, hard-to-diagnose, or misdiagnosed conditions",
        "Mental disorders — hysteria, anxiety, phobias",
        "Shaking of head or chin (neurological tremor)",
        "Loss of nails",
        "Poisoning, gas exposure, or chemical sensitivity",
    ],
    "Ketu": [
        "Spinal cord injuries and back problems",
        "Urinary tract infections",
        "Rheumatic diseases",
        "Knee and toe problems",
        "Loss or impairment of hearing",
    ],
}

#: Finer Mars disease context split — use when Mars dignity is explicitly known.
#: Cross-ref: PLANET_DISEASES["Mars"] (merged/general form), PLANET_DEBILITATION
PLANET_DISEASES_MARS_CONTEXT: dict[str, list[str]] = {
    "benefic": [
        "Liver issues",
        "Abdominal diseases",
        "Diarrhea",
        "Bile imbalances",
    ],
    "malefic": [
        "Accidents and sudden injuries",
        "Blood pressure",
        "Paralysis",
        "Loss of physical strength",
    ],
}


# ============================================================================
# SECTION 18: PLANET KARMA RELATIVES (GENERAL FAMILY MAPPING)
# ============================================================================

#: General mapping of planets to the family members they govern in a karmic context.
#: Used to identify which relative is affected by a planet's affliction or rin (debt).
#:
#: NOTE — distinct from PLANET_RELATIVES (Section 13):
#:   PLANET_RELATIVES  → dict[planet][house] → specific relative name (house-dependent)
#:   PLANET_KARMA_RELATIVES → dict[planet] → general family category (house-independent)
#:
#: Cross-ref: PLANET_RELATIVES (house-specific), RIN_RULES (debt triggers),
#:            DISPOSITION_RULES (karma between planets)
PLANET_KARMA_RELATIVES: dict[str, str] = {
    "Sun":     "Father, Self, Paternal Ancestors",
    "Moon":    "Mother, Elderly women in family",
    "Mars":    "Brothers (elder = benefic Mars; younger = malefic Mars); close male friends",
    "Mercury": "Sister, Daughter, Father's Sister (Bua / Phoopha)",
    "Jupiter": "Grandfather (Dada), Teacher (Guru), Priest",
    "Venus":   "Wife, Female partner, Women in general",
    "Saturn":  "Paternal Uncle (Chacha / Tau), Servants, Labourers, elderly people",
    "Rahu":    "Father-in-law (Sasur), Maternal Grandfather (Nana), step-relatives",
    "Ketu":    "Son, Nephew (Bhatija), Son-in-law (Damad), Maternal Uncle (Mama)",
}


# ============================================================================
# SECTION 19: NATURAL ZODIAC — HOUSE SIGNS & SIGN LORDS
# ============================================================================

#: Natural zodiac sign governing each house (Kaal Purush / Natural Horoscope ordering).
#: H1 = Aries, H2 = Taurus, ... H12 = Pisces
#: Source: Standard Vedic / Lal Kitab natural zodiac framework
#: Cross-ref: HOUSE_NATURAL_SIGN_LORDS (sign owner), FIXED_HOUSE_LORDS (Lal Kitab Pakka Ghar — DIFFERENT concept)
HOUSE_NATURAL_SIGNS: dict[int, str] = {
    1:  "Aries",
    2:  "Taurus",
    3:  "Gemini",
    4:  "Cancer",
    5:  "Leo",
    6:  "Virgo",
    7:  "Libra",
    8:  "Scorpio",
    9:  "Sagittarius",
    10: "Capricorn",
    11: "Aquarius",
    12: "Pisces",
}

#: The classical zodiac sign lord for each house (based on natural zodiac sign ownership).
#: ⚠️  IMPORTANT DISTINCTION:
#:   HOUSE_NATURAL_SIGN_LORDS — classical sign rulership (Aries→Mars, Taurus→Venus, etc.)
#:   FIXED_HOUSE_LORDS         — Lal Kitab Pakka Ghar lords (Saturn→H10, Jupiter→H2, etc.)
#:   These are DIFFERENT and BOTH matter. Do not conflate them.
#: Cross-ref: FIXED_HOUSE_LORDS (Pakka Ghar / LK-specific), PLANET_PAKKA_GHAR
HOUSE_NATURAL_SIGN_LORDS: dict[int, list[str]] = {
    1:  ["Mars"],
    2:  ["Venus"],
    3:  ["Mercury"],
    4:  ["Moon"],
    5:  ["Sun"],
    6:  ["Mercury"],
    7:  ["Venus"],
    8:  ["Mars", "Saturn"],   # Classical: Mars; Modern/Lal Kitab also acknowledges Saturn
    9:  ["Jupiter"],
    10: ["Saturn"],
    11: ["Saturn"],
    12: ["Jupiter"],
}


# ============================================================================
# SECTION 20: HOUSE DIGNITY VIEW (DERIVED — always in sync with source data)
# ============================================================================

#: Per-house synthesis of all three dignity dimensions: exaltation, debilitation,
#: Pakka Ghar (LK fixed lord), and natural sign lord.
#:
#: This is the "house-first" view of data that lives planet-first in:
#:   PLANET_EXALTATION, PLANET_DEBILITATION, FIXED_HOUSE_LORDS, HOUSE_NATURAL_SIGN_LORDS
#:
#: ⚠️  DERIVED — do NOT edit directly. It is auto-built from the canonical sources above.
#:     Edit those sources and this view stays correct automatically.
#:
#: Notes on blank exaltation/debilitation:
#:   H5  — No classical exaltation. Results depend on the native's own karmic actions.
#:   H8  — No classical exaltation. "Death is unconquerable" (Lal Kitab 1952).
#:   H11 — No classical exaltation or debilitation in Lal Kitab.
#:
#: Cross-ref: PLANET_EXALTATION, PLANET_DEBILITATION, FIXED_HOUSE_LORDS,
#:            HOUSE_NATURAL_SIGN_LORDS, HOUSE_NATURAL_SIGNS
HOUSE_DIGNITY_VIEW: dict[int, dict[str, list[str]]] = {
    h: {
        "exalted":          [p for p, hs in PLANET_EXALTATION.items()   if h in hs],
        "debilitated":      [p for p, hs in PLANET_DEBILITATION.items() if h in hs],
        "pakka_ghar_lords": FIXED_HOUSE_LORDS.get(h, []),
        "sign_lords":       HOUSE_NATURAL_SIGN_LORDS.get(h, []),
        "sign":             HOUSE_NATURAL_SIGNS[h],
    }
    for h in range(1, 13)
}

#: H5 special note — no planet is classically exalted here in Lal Kitab.
#: This house's results are governed by the native's own deeds (Swayam Rin).
HOUSE_5_LK_NOTE: str = (
    "H5 results depend on the native's own karmic actions (Swayam Rin). "
    "No classical planet is exalted here; Jupiter is Fixed Lord (Pakka Ghar). "
    "Sun is the natural sign lord. Both are benefic when unafflicted."
)

#: H8 special note — no classical exaltation in Lal Kitab.
HOUSE_8_LK_NOTE: str = (
    "H8 represents death, transformation, and the unconquerable. "
    "No planet is exalted here. Mars and Saturn are Fixed Lords. "
    "Moon is debilitated. Saturn-Mars conjunction here forms Artificial Rahu (Exalted)."
)


# ============================================================================
# SECTION 21: MASNUI (ARTIFICIAL PLANET) QUALITATIVE EFFECTS
# ============================================================================

#: Qualitative general effect for each Masnui (Artificial Planet) conjunction.
#: Keys use "Planet1+Planet2" format (sorted alphabetically, Title Case).
#: These describe the CHARACTER of the artificial planet formed — not a house-specific result.
#:
#: For which artificial planet is FORMED, see MASNUI_FORMATION_RULES (frozenset keyed).
#: For the base planet the artificial maps to, see MASNUI_TO_STANDARD.
#:
#: Source: Lal Kitab 1952, Volume II — Masnooi Grah descriptions
#: Cross-ref: MASNUI_FORMATION_RULES, MASNUI_TO_STANDARD
MASNUI_EFFECTS: dict[str, dict[str, str]] = {
    "Sun+Venus": {
        "resulting_planet": "Artificial Jupiter",
        "character":        "Hollow or deceptive brightness; can appear positive but lacks substance",
        "lk_note":          "Like gold on the outside but empty within",
    },
    "Jupiter+Sun": {
        "resulting_planet": "Artificial Moon",
        "character":        "Spiritually positive; calm, wise, and nurturing energy",
        "lk_note":          "Beneficial for spiritual and family matters",
    },
    "Mercury+Sun": {
        "resulting_planet": "Artificial Mars (Auspicious)",
        "character":        "Powerful self-earning energy; sharp and decisive",
        "lk_note":          "Good for career and self-made success",
    },
    "Saturn+Sun": {
        "resulting_planet": "Artificial Mars (Malefic) AND Artificial Rahu (Debilitated)",
        "character":        "Highly destructive; toxic like poison when enemies are active",
        "lk_note":          "One of the most challenging conjunctions in Lal Kitab",
    },
    "Mercury+Venus": {
        "resulting_planet": "Artificial Sun",
        "character":        "Bright, royal, copper-like luminosity; attractive and intelligent",
        "lk_note":          "Good for arts, communication, and social status",
    },
    "Jupiter+Rahu": {
        "resulting_planet": "Artificial Mercury",
        "character":        "Clever and doubtful; sharp intelligence with potential for deceit",
        "lk_note":          "Can give both great wit and unreliability",
    },
    "Jupiter+Venus": {
        "resulting_planet": "Artificial Saturn (Ketu-like)",
        "character":        "Detached, strict, and spiritually inclined; renunciation energy",
        "lk_note":          "Material enjoyment is curtailed; spiritual growth is possible",
    },
    "Mars+Mercury": {
        "resulting_planet": "Artificial Saturn (Rahu-like)",
        "character":        "Revengeful, calculating, and strategically clever",
        "lk_note":          "Can indicate a sharp but potentially unscrupulous mind",
    },
    "Mars+Saturn": {
        "resulting_planet": "Artificial Rahu (Exalted)",
        "character":        "Sudden windfall or sudden catastrophic strike",
        "lk_note":          "House placement determines if this manifests as sudden wealth or sudden loss",
    },
    "Saturn+Venus": {
        "resulting_planet": "Artificial Ketu (Exalted)",
        "character":        "Materially wealthy but personally abstinent; detached prosperity",
        "lk_note":          "Often indicates wealth without personal enjoyment of it",
    },
    "Moon+Saturn": {
        "resulting_planet": "Artificial Ketu (Debilitated)",
        "character":        "Restless wandering, loss of peace, emotional turbulence",
        "lk_note":          "Challenges in mother relationship and mental stability",
    },
    "Rahu+Ketu": {
        "resulting_planet": "Artificial Venus (Unusual Conjunction)",
        "character":        "Dual-faced nature; seeks luxury but is internally conflicted",
        "lk_note":          "Rare conjunction — results vary greatly by house placement",
    },
}


# ============================================================================
# SECTION 22: DUAL RESULTS — BENEFIC / MALEFIC OUTCOMES BY HOUSE
# ============================================================================
#
# Lal Kitab Vol II (pp. 315–632) documents every planet's DUAL outcomes
# (Fal / Kufal) for each of the 12 houses. The same placement can manifest
# positively OR negatively depending on:
#   1. Whether the native's friendly planets are well-placed
#   2. Whether enemy planets are aspecting or polluting the house
#   3. Whether the planet is "sleeping" (dormant) or "awake"
#   4. Karmic actions of the native in the current life
#
# The tables below capture these dual outcomes.
# Jupiter's table is provided in full as the canonical example.
# (Remaining planets' dual results can be added incrementally.)

#: Jupiter's dual results (Benefic vs Malefic) for each house.
#: Source: Lal Kitab 1952, Volume II
#: Cross-ref: DISPOSITION_RULES (causes that flip Jupiter Good→Bad),
#:            PLANET_EXALTATION["Jupiter"] = [4], PLANET_DEBILITATION["Jupiter"] = [10]
DUAL_RESULTS_JUPITER: dict[int, dict[str, str]] = {
    1:  {
        "benefic":  "Like a king; protects the family and earns respect.",
        "malefic":  "Pompous and self-aggrandising; brings decline to the family lineage.",
    },
    2:  {
        "benefic":  "Wealthy, fortunate, and a generous head of household.",
        "malefic":  "Loses wealth through bad decisions; household suffers.",
    },
    3:  {
        "benefic":  "Well-educated, courageous, and a strong communicator.",
        "malefic":  "Ignorant and cowardly; estranged from siblings.",
    },
    4:  {
        "benefic":  "Exalted — a great scholar, wealthy, and blessed with children.",
        "malefic":  "Breaks ancestral property; adversarial to mother.",
    },
    5:  {
        "benefic":  "Bestowed with happiness from the time of birth of a son.",
        "malefic":  "May even have a stillborn child; grief through progeny.",
    },
    6:  {
        "benefic":  "Gets everything even unsolicited; favoured by fortune.",
        "malefic":  "Suffocated by poverty; chronic illness.",
    },
    7:  {
        "benefic":  "A renowned king; prosperous and respected.",
        "malefic":  "A renowned hermit — revered but poor and alone.",
    },
    8:  {
        "benefic":  "Lord of the World; extremely helpful and generous to others.",
        "malefic":  "Self-destructive; destroys his own clan.",
    },
    9:  {
        "benefic":  "A brave hunter of lions; courageous and dharmic.",
        "malefic":  "Cowardly, mean, and miserable.",
    },
    10: {
        "benefic":  "An image of Lord Indra and King Vikramaditya; great worldly status.",
        "malefic":  "A man who is his own worst enemy; career self-sabotage.",
    },
    11: {
        "benefic":  "Gains continuously; income never dries up.",
        "malefic":  "Stagnant income; blocked gains despite effort.",
    },
    12: {
        "benefic":  "Spiritually liberated; peace in the final phase of life.",
        "malefic":  "Excessive expenditure; loss in foreign lands.",
    },
}

#: Template structure for all planets' dual results.
#: When adding remaining planets, follow this exact format.
#: Keys: planet name → {house_number: {"benefic": str, "malefic": str}}
#:
#: Currently populated: Jupiter (see DUAL_RESULTS_JUPITER above).
#: Planet keys to add: Sun, Moon, Mars, Mercury, Venus, Saturn, Rahu, Ketu
DUAL_RESULTS_ALL_PLANETS: dict[str, dict[int, dict[str, str]]] = {
    "Jupiter": DUAL_RESULTS_JUPITER,
    # "Sun":     DUAL_RESULTS_SUN,     # To be added
    # "Moon":    DUAL_RESULTS_MOON,    # To be added
    # "Mars":    DUAL_RESULTS_MARS,    # To be added
    # "Mercury": DUAL_RESULTS_MERCURY, # To be added
    # "Venus":   DUAL_RESULTS_VENUS,   # To be added
    # "Saturn":  DUAL_RESULTS_SATURN,  # To be added
    # "Rahu":    DUAL_RESULTS_RAHU,    # To be added
    # "Ketu":    DUAL_RESULTS_KETU,    # To be added
}


# ============================================================================
# SECTION 23: ASPECT TYPE SEMANTICS & SPECIAL RELATIONAL CONDITIONS
# ============================================================================

#: Qualitative meaning of each named Lal Kitab house aspect type.
#: These are the aspect TYPE names used as keys in HOUSE_ASPECT_DATA.
#: ALL 12 houses cast every aspect type; only the target house differs.
#: Cross-ref: HOUSE_ASPECT_DATA (full source of truth), HOUSE_ASPECT_TARGETS (simplified)
HOUSE_ASPECT_TYPE_DESCRIPTIONS: dict[str, str] = {
    "100 Percent": (
        "Full/direct aspect. The casting house exerts complete influence on the target. "
        "Only H1→H7 and H4→H10 carry a 100% aspect in Lal Kitab."
    ),
    "50 Percent": (
        "Half aspect. Moderate but significant influence. "
        "H3 casts 50% to both H9 and H11; H5 casts 50% to H9."
    ),
    "25 Percent": (
        "Reverse quarter aspect — a weak but often sudden or surprise strike. "
        "Only H2→H6 and H8→H2 carry a 25% aspect. "
        "H8's 25% aspect on H2 is particularly potent as a 'blind strike' from the house of hidden matters."
    ),
    "Outside Help": (
        "The casting house's planet provides external uplift or reinforcement to the target. "
        "A beneficial relationship — the planet acts like a patron supporting the target house."
    ),
    "General Condition": (
        "The casting house sets the ambient background conditions for the target. "
        "Every house casts a General Condition aspect on a specific target, "
        "creating a background influence even without a direct strong aspect."
    ),
    "Confrontation": (
        "Hostile face-off. The casting house's planet directly opposes and attacks the target. "
        "E.g., H1 confronts H8, H6 confronts H1. "
        "A Confrontation aspect from an enemy planet is especially damaging."
    ),
    "Foundation": (
        "The casting house provides the structural foundation for the target house's strength. "
        "E.g., H2 is the foundation of H10; H1 is the foundation of H9. "
        "Weakness in the foundation house weakens the target house's results."
    ),
    "Deception": (
        "The casting house's planet can undermine or mislead the target indirectly. "
        "E.g., H10 deceives H7 (not H2 as sometimes cited); H9 deceives H6 (not H3). "
        "The Deception targets follow a consistent +9 offset pattern in the house wheel."
    ),
}

#: Lal Kitab's named special inter-house relational conditions.
#: These are qualitative structural rules, NOT repeating the numeric data in HOUSE_ASPECT_DATA.
#: Cross-ref: HOUSE_ASPECT_DATA, SUDDEN_STRIKE_HOUSE_PAIRS, JOINT_WALL_PAIRS
SPECIAL_ASPECT_CONDITIONS: dict[str, str] = {
    "Foundation (Buniyad)": (
        "One house forms the structural base of another. "
        "The target house's results depend on the health of its foundation house. "
        "Foundation relationships are encoded in HOUSE_ASPECT_DATA under the 'Foundation' key. "
        "Key example: H2 is the foundation of H10 (H2 Foundation → H10)."
    ),
    "Sudden Strike (Achanak Chot)": (
        "Pairs of natal houses where planets create a sudden, unpredictable impact on each other "
        "when they aspect each other in the annual chart. "
        "Standard pairs: see SUDDEN_STRIKE_HOUSE_PAIRS. "
        "The 25% reverse aspect H8→H2 is a classic single-house Sudden Strike pattern."
    ),
    "Confrontation (Takrav)": (
        "Direct hostile opposition between houses. "
        "H1 confronts H8; H6 confronts H1; each house confronts a specific target "
        "(see 'Confrontation' in HOUSE_ASPECT_DATA for all 12 pairs). "
        "Note: H8 confronts H3 — not H2 as sometimes incorrectly cited."
    ),
    "Joint Wall (Sanjhi Deewar)": (
        "Adjacent houses share a common 'wall' and influence each other like neighbors. "
        "Planets in adjacent houses unavoidably affect one another's results. "
        "All adjacent pairs are listed in JOINT_WALL_PAIRS."
    ),
    "Deception (Dhoka)": (
        "A planet in one house can mislead or undermine a specific target house indirectly. "
        "Correct mapping: H10 deceives H7 (not H2); H9 deceives H6 (not H3). "
        "The full deception map follows a +9 offset: deceived_house = (casting_house + 8) % 12 + 1. "
        "See 'Deception' key in HOUSE_ASPECT_DATA for all 12 pairs."
    ),
    "Blind House (Andha Ghar)": (
        "House 8 is considered 'blind' — it does not cast standard outward aspects. "
        "Its only active aspect is the 25% reverse quarter-strike to House 2. "
        "Planets in H8 are therefore somewhat isolated unless awakened by their activator planet."
    ),
}

#: Adjacent house pairs — the 'Joint Wall' (Sanjhi Deewar) relationship.
#: Each pair shares a border; planets in adjacent houses unavoidably affect each other.
#: Represented as frozensets (order-independent), matching the style of SUDDEN_STRIKE_HOUSE_PAIRS.
#: Cross-ref: SUDDEN_STRIKE_HOUSE_PAIRS (specific natal-chart strike pairs),
#:            SPECIAL_ASPECT_CONDITIONS["Joint Wall (Sanjhi Deewar)"]
JOINT_WALL_PAIRS: list[frozenset[int]] = [
    frozenset({12, 1}),
    frozenset({1,  2}),
    frozenset({2,  3}),
    frozenset({3,  4}),
    frozenset({4,  5}),
    frozenset({5,  6}),
    frozenset({6,  7}),
    frozenset({7,  8}),
    frozenset({8,  9}),
    frozenset({9,  10}),
    frozenset({10, 11}),
    frozenset({11, 12}),
]


# ============================================================================
# SECTION 25: HOROSCOPE CLASSIFICATION TYPES (KUNDALI BHED)
# ============================================================================

#: Lal Kitab's 5 structural chart classification types based on specific
#: planetary configurations in the natal chart.
#: These classifications affect overall chart interpretation and timing predictions.
#:
#: Cross-ref: KENDRA_HOUSES (central pillar houses [1,4,7,10]),
#:            NATURAL_RELATIONSHIPS (for inimical planet detection)
HOROSCOPE_TYPE_RULES: dict[str, dict[str, str]] = {
    "Blind Horoscope (Andha Tewa)": {
        "condition": (
            "House 10 contains 2 or more mutually inimical planets, "
            "AND House 4 is empty."
        ),
        "interpretation": (
            "Career and public reputation are severely obscured. The native acts without "
            "full awareness of consequences. H4 (inner strength/home) offers no protection."
        ),
        "cross_ref": "NATURAL_RELATIONSHIPS (inimical check), KENDRA_HOUSES",
    },
    "Half-Blind Horoscope (Ratbandha Tewa)": {
        "condition": "Sun is in House 4 AND Saturn is in House 7.",
        "interpretation": (
            "Home life and partnerships are in persistent conflict. The native can see "
            "'half' the truth but is blind to the other half. Career progress is erratic."
        ),
        "cross_ref": "PLANET_DEBILITATION (Sun in H4 is debilitated? No — Mars is), "
                     "HOUSE_ASPECT_DATA (H4↔H10 mutual, H7 confronts H2)",
    },
    "Pious Horoscope (Dharmi Tewa)": {
        "condition": (
            "Any of: Jupiter in H11; OR Saturn in H11; OR Rahu/Ketu in H4; "
            "OR Rahu/Ketu conjunct Jupiter (same house)."
        ),
        "interpretation": (
            "The native is disposed toward righteousness, religious observances, and "
            "strong moral values. Spiritual progress is accelerated."
        ),
        "cross_ref": "PLANET_PAKKA_GHAR (Jupiter's primary home is H2, not H11 — "
                     "Jupiter in H11 here is a placement condition, not Pakka Ghar)",
    },
    "Non-Adult Chart (Nabalig Tewa)": {
        "condition": (
            "Kendra houses (1, 4, 7, 10) are ALL empty; OR contain only malefics "
            "(Rahu, Ketu, Saturn); OR contain only Mercury. "
            "Chart is considered structurally immature."
        ),
        "interpretation": (
            "Life results are unstable, delayed, or absent until approximately age 12. "
            "The native appears unable to assert personal authority in early years."
        ),
        "cross_ref": "KENDRA_HOUSES [1,4,7,10], STANDARD_PLANETS",
    },
    "Adult Chart (Balig Tewa)": {
        "condition": (
            "One or more Kendra houses (1, 4, 7, 10) are occupied by benefic "
            "or friendly planets (Sun, Moon, Mars, Jupiter, Venus)."
        ),
        "interpretation": (
            "Chart is fully active from birth. The native has the capacity to act on "
            "life circumstances immediately and results manifest in a timely manner."
        ),
        "cross_ref": "KENDRA_HOUSES [1,4,7,10], NATURAL_RELATIONSHIPS (for benefic check)",
    },
}


# ============================================================================
# SECTION 26: SLEEPING PLANET / HOUSE RULES (SOYA GRAH / SOYA GHAR)
# ============================================================================

#: Conditions that determine whether a planet or house is dormant (sleeping).
#: A sleeping planet neither activates remedies nor delivers results.
#: Cross-ref: HOUSE_ASPECT_TARGETS (what a planet aspects), HOUSE_ACTIVATORS (what wakes H7–H12)
SLEEPING_PLANET_RULES: dict[str, str] = {
    "planet_asleep_condition": (
        "A planet is sleeping if ALL of the houses it significantly aspects "
        "(per HOUSE_ASPECT_TARGETS) are empty of any other planet."
    ),
    "house_asleep_condition": (
        "A house is sleeping if it contains no planet AND no planet is "
        "casting a significant aspect onto it (per HOUSE_ASPECT_TARGETS)."
    ),
    "inner_to_outer_activation": (
        "Inner houses (H1–H6) are awakened by planets posited in their "
        "corresponding outer houses (H7–H12) respectively: "
        "H1↔H7, H2↔H8, H3↔H9, H4↔H10, H5↔H11, H6↔H12."
    ),
    "outer_house_activators": (
        "Outer houses H7–H12 each have a specific planet whose presence "
        "(anywhere in the chart) helps awaken them — see HOUSE_ACTIVATORS."
    ),
}

#: Canonical activator planet for each outer house (H7–H12).
#: The listed planet's presence in the chart can awaken an otherwise sleeping outer house.
#:
#: Note on H8 (Moon): Moon is debilitated in H8, yet it is still considered
#: H8's activator. This is because Moon (H4 Fixed Lord) opposes H8 and its energy,
#: even weakened, is sufficient to 'unlock' H8's latent results.
#:
#: Cross-ref: FIXED_HOUSE_LORDS (H7→Venus, H9→Jupiter, H10→Saturn, H11→Jupiter, H12→Rahu),
#:            SLEEPING_PLANET_RULES, PLANET_DEBILITATION["Moon"] = [8]
HOUSE_ACTIVATORS: dict[int, str] = {
    7:  "Venus",
    8:  "Moon",    # Moon is debilitated in H8 but still awakens it
    9:  "Jupiter",
    10: "Saturn",
    11: "Jupiter",
    12: "Rahu",
}


# ============================================================================
# SECTION 27: SCAPEGOAT KARMIC NOTES (BAKRA GRAH)
# ============================================================================

#: Qualitative karmic rationale for each planet's scapegoat transfer mechanism.
#: Complements the NUMERIC scapegoat data in SCAPEGOATS (Section 4).
#: When a planet suffers attack, it transfers damage to its scapegoat,
#: meaning the RELATIVE or LIFE AREA governed by that scapegoat suffers instead.
#:
#: Key rule: Rahu and Ketu have NO scapegoats — they bear damage directly,
#: which then manifests in their associated articles/relatives.
#:
#: Cross-ref: SCAPEGOATS (numeric proportions), PLANET_KARMA_RELATIVES (who each planet represents)
SCAPEGOAT_NOTES: dict[str, dict[str, str]] = {
    "Sun": {
        "represents":          "Father, Self, Authority",
        "transfers_to":        "Ketu",
        "ketu_represents":     "Son, Maternal uncle",
        "karmic_rationale":    "Attacks on the Sun (paternal/self energy) fall on the Son (Ketu)",
    },
    "Moon": {
        "represents":          "Mother, Emotions, Mind",
        "transfers_to":        "Jupiter (40%), Sun (30%), Mars (30%)",
        "karmic_rationale":    "Mother's suffering distributes across Father, Grandfather, and Brother",
    },
    "Mars": {
        "represents":          "Brother, Courage",
        "transfers_to":        "Ketu",
        "ketu_represents":     "Son, Nephew",
        "karmic_rationale":    "Attacks on the Brother (Mars) fall on the Son/Nephew (Ketu)",
    },
    "Mercury": {
        "represents":          "Sister, Daughter, Intelligence",
        "transfers_to":        "Venus",
        "venus_represents":    "Wife, Wealth",
        "karmic_rationale":    "Attacks on Sister/Daughter (Mercury) fall on Wife/Wealth (Venus)",
    },
    "Jupiter": {
        "represents":          "Guru, Grandfather, Wisdom",
        "transfers_to":        "Ketu",
        "karmic_rationale":    "Attacks on the Guru/Grandfather (Jupiter) fall on Son/Nephew (Ketu)",
    },
    "Venus": {
        "represents":          "Wife, Wealth, Beauty, Comfort",
        "transfers_to":        "Moon",
        "moon_represents":     "Mother",
        "karmic_rationale":    "Attacks on Wife/Wealth (Venus) fall on Mother (Moon)",
    },
    "Saturn": {
        "represents":          "Servants, Uncle, Karma, Longevity",
        "transfers_to":        "Rahu (50%), Ketu (30%), Venus (20%)",
        "karmic_rationale":    (
            "Saturn's suffering distributes across Rahu (foreign/shadow), "
            "Ketu (son/renunciation), and Venus (wife/wealth)"
        ),
    },
    "Rahu": {
        "represents":          "Foreign elements, Illusions, Shadow",
        "transfers_to":        "None — Rahu bears damage directly",
        "karmic_rationale":    "Rahu has no scapegoat; attacks manifest directly in Rahu's domains",
    },
    "Ketu": {
        "represents":          "Son, Mysticism, Liberation",
        "transfers_to":        "None — Ketu bears damage directly",
        "karmic_rationale":    "Ketu has no scapegoat; attacks manifest directly in Ketu's domains",
    },
}


# ============================================================================
# SECTION 28: RIN (KARMA DEBT) REMEDIES
# ============================================================================

#: Remedies for each Lal Kitab Karma Debt (Rin) type.
#: Keys exactly match the rin names used in RIN_RULES (Section 7).
#: The TRIGGER conditions (planets + houses) are in RIN_RULES — this table
#: adds only the prescribed remedy action.
#:
#: ⚠️  Source note: Some remedy texts use slightly different trigger planet sets.
#:    Where a discrepancy exists between sources, the triggers in RIN_RULES
#:    (from the 1952 Lal Kitab grammar analysis) are considered authoritative;
#:    only the remedy text is sourced from the supplementary tradition here.
#:
#: Cross-ref: RIN_RULES (trigger conditions), DISPOSITION_RULES (related karma causation)
RIN_REMEDIES: dict[str, str] = {
    "Ancestral Debt (Pitra Rin)": (
        "Collect money from family members (symbolically) and donate to a temple "
        "or religious place of worship."
    ),
    "Self Debt (Swayam Rin)": (
        "Perform a yagna (fire ritual) or havan using collective family funds. "
        "Do not use personal money alone."
    ),
    "Maternal Debt (Matri Rin)": (
        "Drop a piece of silver (coin or small item) into a flowing river or stream."
    ),
    "Family/Wife/Woman Debt (Stri Rin)": (
        "Serve women or donate to causes that benefit women. "
        "Offer food and clothing to elderly women."
    ),
    "Relative/Brother Debt (Bhai-Bandhu Rin)": (
        "Donate medicines or provide medical assistance to the sick and needy."
    ),
    "Daughter/Sister Debt (Behen/Beti Rin)": (
        "Burn yellow cowrie shells (kauri) to ash and immerse the ash in flowing water."
    ),
    "Oppression/Atrocious Debt (Zulm Rin)": (
        "Feed fish in a river or pond, or feed and serve daily labourers and workers."
    ),
    "Debt of the Unborn (Ajanma Rin)": (
        "Donate a whole, sound coconut (symbolising an unborn soul) into flowing water."
    ),
    "Negative Speech Debt (Manda Bol Rin)": (
        "Feed stray dogs regularly and serve or donate to widows."
    ),
}

#: Additional Rin type from supplementary Lal Kitab traditions (not in core RIN_RULES).
#: Trigger: Saturn or Mars in House 10 or 11.
#: Note: Overlaps conceptually with 'Zulm Rin'; kept separate as a distinct cited tradition.
#: Cross-ref: RIN_RULES (core rin table), DISPOSITION_RULES
GODLESS_DEBT_DHARMI_RIN: dict[str, str] = {
    "name":        "Godless Debt (Dharmi Rin)",
    "trigger":     "Saturn or Mars in House 10 or 11",
    "remedy":      "Serve a temple, gurudwara, masjid, or other religious place regularly.",
    "note":        (
        "This rin type is sourced from derivative Lal Kitab traditions; "
        "it is not represented in core RIN_RULES (Section 7). "
        "Add to RIN_RULES if empirically validated."
    ),
}


# ============================================================================
# SECTION 29: PLANET CLASSIFICATIONS (GENDER / NATURE)
# ============================================================================

#: Lal Kitab classification of planets by gender and elemental nature.
#: Used to determine how planets relate to family members and which domains they rule.
#:
#: Mars is uniquely dual: benefic Mars behaves like honey (nurturing, constructive);
#: malefic Mars behaves like poison (destructive, volatile).
#: Mercury is a Eunuch (Napunsak) — gender-neutral; its behaviour mirrors the strongest
#: planet it associates with (it takes on the nature of its company).
#:
#: Cross-ref: PLANET_KARMA_RELATIVES (karmic family mapping), SCAPEGOAT_NOTES
PLANET_GENDER: dict[str, str] = {
    "Jupiter": "Male",
    "Sun":     "Male",
    "Mars":    "Male",
    "Venus":   "Female",
    "Moon":    "Female",
    "Mercury": "Eunuch (Napunsak) — mirrors the nature of its companions",
    "Saturn":  "Neutral/Malefic",
    "Rahu":    "Evil (shadow — no body, no gender)",
    "Ketu":    "Evil (shadow — no body, no gender)",
}

#: Full nature classification by category group.
#: Cross-ref: PLANET_GENDER, NATURAL_RELATIONSHIPS
PLANET_NATURE_GROUPS: dict[str, list[str]] = {
    "Male":   ["Jupiter", "Sun", "Mars"],
    "Female": ["Venus", "Moon"],
    "Eunuch": ["Mercury"],
    "Evil":   ["Rahu", "Ketu", "Saturn"],  # Rahu and Ketu are the primary evils; Saturn is dark/karmic
}

#: Mars dual nature — context-dependent description.
#: Cross-ref: PLANET_DISEASES_MARS_CONTEXT, MASNUI_FORMATION_RULES (involving Mars combos)
MARS_DUAL_NATURE: dict[str, str] = {
    "benefic": "Like honey — nurturing, energising, constructive; supports brothers and courage",
    "malefic": "Like poison — destructive, volatile, accident-prone; harms the same domains",
}


# ============================================================================
# SECTION 30: PLANET COLOURS
# ============================================================================

#: Colour associations for each planet in Lal Kitab.
#: Used in remedy selection (wearing, donating, or avoiding that colour).
#: Mars has two colours based on its benefic/malefic state.
#:
#: Cross-ref: PLANET_NATURE_GROUPS (planet character), PLANET_KARMA_RELATIVES (relay of colour to relatives)
PLANET_COLOURS: dict[str, str] = {
    "Jupiter": "Yellow",
    "Sun":     "Bright copper (shining orange-red)",
    "Moon":    "Milky white",
    "Venus":   "White (like curd)",
    "Mars":    "Blood red (benefic) / Rusted red (malefic)",
    "Mercury": "Green",
    "Saturn":  "Black",
    "Rahu":    "Blue",
    "Ketu":    "Mixed black and white (like a cat's eye gemstone)",
}

#: Separate Mars colour entries for code paths that distinguish Mars polarity.
#: Cross-ref: PLANET_COLOURS["Mars"] (combined), MARS_DUAL_NATURE
MARS_COLOURS: dict[str, str] = {
    "benefic": "Blood red",
    "malefic": "Rusted red",
}


# ============================================================================
# SECTION 31: PLANET TIMES AND DAYS
# ============================================================================

#: The time of day and day of the week that each planet governs.
#: Used in remedy timing: performing a planet's remedy during its hour/day
#: increases effectiveness.
#:
#: Notes:
#:   - Rahu's day (Thursday evening) overlaps partially with Jupiter's day (Thursday).
#:     This reflects Rahu's deceptive nature — it mimics Jupiter's domain.
#:   - Ketu's time (Dawn, Sunday morning) also overlaps with Sun (Sunday).
#:   - Mercury's time is the same regardless of polarity; only its companion planets
#:     determine its benefic/malefic state.
#:
#: Cross-ref: PLANET_COLOURS (remedy materials), RIN_REMEDIES (when to perform rin remedies)
PLANET_TIMES_DAYS: dict[str, dict[str, str]] = {
    "Jupiter": {
        "time_of_day": "First part of day (early morning)",
        "day_of_week": "Thursday",
    },
    "Sun": {
        "time_of_day": "Second part of day (mid-morning)",
        "day_of_week": "Sunday",
    },
    "Moon": {
        "time_of_day": "Moonlit night",
        "day_of_week": "Monday",
    },
    "Venus": {
        "time_of_day": "Dark night",
        "day_of_week": "Friday",
    },
    "Mars": {
        # Peak noon = benefic Mars; midday (slightly earlier) = malefic Mars.
        "time_of_day": "Noon (peak noon for benefic; midday for malefic)",
        "day_of_week": "Tuesday",
    },
    "Mercury": {
        "time_of_day": "Afternoon (~4 pm)",
        "day_of_week": "Wednesday",
    },
    "Saturn": {
        "time_of_day": "Pitch dark night or heavily overcast day",
        "day_of_week": "Saturday",
    },
    "Rahu": {
        "time_of_day": "Peak evening (sunset and just after)",
        "day_of_week": "Thursday evening",  # Overlaps with Jupiter's day — Rahu mimics Jupiter
    },
    "Ketu": {
        "time_of_day": "Dawn (just before sunrise)",
        "day_of_week": "Sunday morning",    # Overlaps with Sun's day — Ketu acts in Sun's shadow
    },
}


# ============================================================================
# SECTION 32: PLANET PERIODS, LIFESPANS, AND ANIMAL ASSOCIATIONS
# ============================================================================

#: Extended planet period data from Lal Kitab.
#: Contains timing, transit, and animal association information.
#:
#: Field definitions:
#:   days              — Number of days the planet's annual-chart influence actively runs
#:   maturity_age      — Age at which the planet reaches full effectiveness in the native's life
#:                       (matches PLANET_EFFECTIVE_AGES; Mars is split into benefic/malefic sub-ages)
#:   main_transit_yr   — The primary transit year (year of life) when the planet delivers
#:                       its strongest overall results
#:   effective_period  — Duration (years) over which the planet's period is actively felt
#:   activation_speed  — How quickly (in years) the planet reaches its peak effect once activated
#:   animal            — The animal Lal Kitab associates with this planet (used in remedy assessment
#:                       and interpretation of chart effects on animal-related matters)
#:
#: Mars note: Split into benefic/malefic. Their maturity_ages (13 + 15 = 28) sum to
#: PLANET_EFFECTIVE_AGES["Mars"] = 28, confirming consistency.
#:
#: Cross-ref: PLANET_EFFECTIVE_AGES (maturity ages, planet-keyed), CYCLE_35_YEAR_RANGES (35-yr ruler)
PLANET_PERIODS: dict[str, dict] = {
    "Jupiter": {
        "days":             32,
        "maturity_age":     16,
        "main_transit_yr":  75,
        "effective_period": 16,
        "activation_speed": 6,
        "animal":           "Lion",
    },
    "Sun": {
        "days":             22,
        "maturity_age":     22,
        "main_transit_yr":  100,
        "effective_period": 6,
        "activation_speed": 2,
        "animal":           "Chariot (solar vehicle; no specific animal)",
    },
    "Moon": {
        "days":             24,
        "maturity_age":     24,
        "main_transit_yr":  85,
        "effective_period": 10,
        "activation_speed": 1,
        "animal":           "Horse",
    },
    "Venus": {
        "days":             50,
        "maturity_age":     25,
        "main_transit_yr":  85,
        "effective_period": 20,
        "activation_speed": 3,
        "animal":           "Ox",
    },
    "Mars (benefic)": {
        "days":             24,
        "maturity_age":     13,  # Benefic Mars matures at 13; see note above
        "main_transit_yr":  28,
        "effective_period": 3,
        "activation_speed": 2,
        "animal":           "Leopard",
    },
    "Mars (malefic)": {
        "days":             32,
        "maturity_age":     15,  # Malefic Mars matures at 15; 13+15=28 = PLANET_EFFECTIVE_AGES["Mars"]
        "main_transit_yr":  90,
        "effective_period": 4,
        "activation_speed": 4,
        "animal":           "Panther, Deer",
    },
    "Mercury": {
        "days":             68,
        "maturity_age":     34,
        "main_transit_yr":  80,
        "effective_period": 17,
        "activation_speed": 2,
        "animal":           "Ram (male sheep)",
    },
    "Saturn": {
        "days":             72,
        "maturity_age":     36,
        "main_transit_yr":  90,
        "effective_period": 19,
        "activation_speed": 6,
        "animal":           "Fish",
    },
    "Rahu": {
        "days":             40,
        "maturity_age":     42,
        "main_transit_yr":  90,
        "effective_period": 18,
        "activation_speed": 6,
        "animal":           "Elephant",
    },
    "Ketu": {
        "days":             43,
        "maturity_age":     48,
        "main_transit_yr":  80,
        "effective_period": 7,
        "activation_speed": 3,
        "animal":           "Dog, Pig",
    },
}


# ============================================================================
# SECTION 33: HOUSE FATE RAISERS AND FIXED PLANET EFFECTS
# ============================================================================

#: The planet whose presence or strength is most responsible for raising the
#: native's fortune specifically through that house's domain ("Fate raising planet").
#: Drawn from the Zodiac sign / house lord relationships in Lal Kitab Vol II.
#:
#: This is distinct from FIXED_HOUSE_LORDS (Pakka Ghar) and
#: HOUSE_NATURAL_SIGN_LORDS (classical sign rulership).
#: Cross-ref: HOUSE_DIGNITY_VIEW, FIXED_HOUSE_LORDS, HOUSE_NATURAL_SIGN_LORDS
HOUSE_FATE_RAISER: dict[int, list[str]] = {
    1:  ["Sun"],
    2:  ["Moon"],
    3:  ["Mars"],
    4:  ["Moon"],
    5:  ["Jupiter", "Sun"],
    6:  ["Ketu"],
    7:  ["Venus", "Mercury"],
    8:  ["Moon"],
    9:  ["Jupiter"],
    10: ["Saturn"],
    11: ["Jupiter"],
    12: ["Rahu"],
}

#: The planet whose fixed (structural) influence permanently colours the results
#: of that house in the natal chart ("Fixed planet effect" per house).
#: This reflects the Lal Kitab view of permanent karaka-ship by house,
#: which differs in some houses from the classical Pakka Ghar.
#:
#: Notable differences from FIXED_HOUSE_LORDS:
#:   H2: Rahu (not Jupiter) — Rahu governs the speech/wealth domain in H2 from a Karaka view
#:   H6: Rahu (not Ketu)   — Rahu has karaka effect on the enemy/disease domain
#:   H12: Ketu (not Rahu)  — Ketu's karaka effect on losses/liberation/foreign
#:
#: Cross-ref: FIXED_HOUSE_LORDS (Pakka Ghar lords), HOUSE_FATE_RAISER
HOUSE_FIXED_PLANET_EFFECT: dict[int, list[str]] = {
    1:  ["Mars"],
    2:  ["Rahu"],
    3:  ["Mercury"],
    4:  ["Moon"],
    5:  ["Sun"],
    6:  ["Rahu"],
    7:  ["Venus"],
    8:  ["Mars"],
    9:  ["Jupiter"],
    10: ["Saturn"],
    11: ["Jupiter"],
    12: ["Ketu"],
}


# ============================================================================
# SECTION 34: INTERMEDIARY SUB-PERIOD RULERS (ANTARDASHA)
# ============================================================================

#: Each planet's annual period is divided into 3 equal sub-periods of ~4 months each,
#: each ruled by a different intermediary planet.
#: Sub-period rulers determine which life area/relative is activated during
#: that 4-month window within the planet's overall annual period.
#:
#: Usage: If the ruling planet for a given year is Jupiter, then in months 1–4
#: of that year Ketu's domains are activated; in months 5–8 Jupiter's own domains;
#: in months 9–12 the Sun's domains are awakened.
#:
#: Cross-ref: PLANET_PERIODS (overall period data), CYCLE_35_YEAR_RANGES (which planet rules which year),
#:            PLANET_KARMA_RELATIVES (what each intermediary planet represents)
PLANET_INTERMEDIARY_PERIODS: dict[str, dict[str, str]] = {
    "Jupiter": {
        "months_1_4":  "Ketu",
        "months_5_8":  "Jupiter",
        "months_9_12": "Sun",
    },
    "Sun": {
        "months_1_4":  "Sun",
        "months_5_8":  "Moon",
        "months_9_12": "Mars",
    },
    "Moon": {
        "months_1_4":  "Jupiter",
        "months_5_8":  "Sun",
        "months_9_12": "Moon",
    },
    "Venus": {
        "months_1_4":  "Mars",
        "months_5_8":  "Venus",
        "months_9_12": "Mercury",
    },
    "Mars": {
        "months_1_4":  "Mars",
        "months_5_8":  "Saturn",
        "months_9_12": "Venus",
    },
    "Mercury": {
        "months_1_4":  "Moon",
        "months_5_8":  "Mars",
        "months_9_12": "Jupiter",
    },
    "Saturn": {
        "months_1_4":  "Rahu",
        "months_5_8":  "Mercury",
        "months_9_12": "Saturn",
    },
    "Rahu": {
        "months_1_4":  "Mars",
        "months_5_8":  "Ketu",
        "months_9_12": "Rahu",
    },
    "Ketu": {
        "months_1_4":  "Saturn",
        "months_5_8":  "Rahu",
        "months_9_12": "Ketu",
    },
}

# ============================================================================
# SECTION 35: BHAGYODAYA (LUCK AWAKENING) AGES
# ============================================================================

#: Fixed years when the luck of a planet is said to "rise" or awaken.
#: Source: Lal Kitab 1952 p.64
BHAGYODAYA_AGES: dict[str, int] = {
    "Jupiter": 16,
    "Sun":     22,
    "Moon":    24,
    "Venus":   25,
    "Mars":    28,
    "Mercury": 34,
    "Saturn":  36,
    "Rahu":    42,
    "Ketu":    48,
}

# ============================================================================
# SECTION 36: STRUCTURAL CHART CLASSIFICATIONS
# ============================================================================

#: Definitions for Nagrik (Urban) and Nashtik (Atheist) chart structures.
#: - Nagrik: Planets focused on personal sphere (H1-H6).
#: - Nashtik: Planets focused on social/external sphere (H7-H12).
STRUCTURAL_CHART_TYPE_RANGES: dict[str, list[int]] = {
    "Nagrik":  [1, 2, 3, 4, 5, 6],
    "Nashtik": [7, 8, 9, 10, 11, 12]
}
