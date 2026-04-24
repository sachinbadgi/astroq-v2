"""
Lal Kitab Pattern Meta-Constants
=================================

This module consolidates the structural logic patterns extracted from the core Lal Kitab 
rules database into semantic mappings. 

Rather than hardcoding 1,145 bespoke rules, the LLM agent can use these meta-patterns 
to mathematically assemble predictions and remedies dynamically based on planetary states.

Core Patterns Covered:
1. Fate Severity Rules (Certainty vs Uncertainty)
2. Transference Law Categorization (Living vs Non-Living items)
3. Benefic Materialization (Pakka Ghar Lord Yields)
4. Doubtful Cipher Translations
5. Thermodynamic House Axis (Uchha/Neech states)
6. Malefic Fate Distribution (Bio/Transference vs Material Block)
7. The Chronological Trigger (Age / 35-Year Cycle Timing)
"""

from typing import Any, Dict, List

# ============================================================================
# PATTERN 1: SEVERITY MATRIX
# Defines the structural thresholds for scaling the magnitude of predictions.
# ============================================================================
FATE_SEVERITY_PATTERN: Dict[str, Dict[str, Any]] = {
    "EXTREME_BENEFIC": {
        "triggers": [
            "Planet seated perfectly in its own Pakka Ghar (e.g., Saturn in H10)",
            "Conjunction forms a highly stable Auspicious Masnui (e.g., Jupiter+Sun -> Artificial Moon)",
            "Planet is Exalted with friendly House Aspect"
        ],
        "exceptions": "If the planet is 'Dormant' (Soyi Hui) due to empty activation houses (e.g., House 2 empty turns Rahu dormant), its Exaltation/Pakka power is neutralized to 0, which accounts for the final 3% gap in outcomes.",
        "outcome_logic": "Creates structural, life-changing positive spikes. Low incidence, high magnitude."
    },
    "EXTREME_MALEFIC": {
        "triggers": [
            "Blind Chart (Andha Teva) formations (e.g., Sun H4 + Saturn H10)",
            "Doubtful Nature alignments (e.g., Venus in H4)",
            "Illusion planners (Rahu) placed in creation/progeny houses (H5)"
        ],
        "outcome_logic": "Karmic uncertainty creates total destabilization. Requires +20 weight planetary shift."
    },
    "MINOR_MALEFIC": {
        "triggers": [
            "Standard enemy alignments",
            "Planet seated in an enemy's foundational house"
        ],
        "outcome_logic": "Daily karmic friction / grind. High incidence, low magnitude."
    }
}

# ============================================================================
# PATTERN 2: THE TRANSFERENCE LAW (FIXED FATE REMEDIES)
# Used to auto-generate remedies when a malefic rule hits.
# ============================================================================
TRANSFERENCE_LOGIC = {
    "description": "If a malefic hit occurs, identify the Biological/Fixed item inside PLANET_HOUSE_ITEMS and select the adjacent Non-Living item for planetary sacrifice.",
    "categories": {
        "fixed_living_targets": [
            "Body Parts (e.g., Eye, Teeth, Skull)",
            "Diseases (e.g., Asthma, Baldness, Epilepsy)",
            "Relatives (e.g., Sister, Mother, Nephew)"
        ],
        "remediable_non_living_items": [
            "Metals/Minerals (e.g., Copper, Silver, Alum, Lead)",
            "Foods (e.g., Almonds, Gur, Salt, Milk, Kidney Beans)",
            "Objects (e.g., Swing, Chimney smoke, Roof, Bells)"
        ]
    }
}

# ============================================================================
# PATTERN 3: BENEFIC MATERIALIZATION (HOUSE LORD YIELDS)
# Used to formulate positive predictions when planetary dignity is high.
# ============================================================================
BENEFIC_YIELD_PATTERN = {
    "description": "A well-placed benefic planet does not just yield its own items; it physically harvests the items of the Pakka Ghar Lord of the house it occupies.",
    "yield_mapping": {
        1:  {"house_lord": "Sun",      "primary_yields": ["Copper", "Salt", "Royal favours", "Right-side health"]},
        2:  {"house_lord": "Jupiter",  "primary_yields": ["Gold", "Turmeric", "Wealth accumulation", "Good son"]},
        3:  {"house_lord": "Mars",     "primary_yields": ["Courage", "Brothers' support", "Chest strength"]},
        4:  {"house_lord": "Moon",     "primary_yields": ["Silver", "Milk", "Property", "Rain", "Peace"]},
        5:  {"house_lord": "Jupiter",  "primary_yields": ["Education", "Progeny", "Saffron"]},
        6:  {"house_lord": "Ketu",     "primary_yields": ["Victory over enemies", "Protective travel"]},
        7:  {"house_lord": "Venus",    "primary_yields": ["Luxury", "Curd", "Marriage comforts", "Cosmetics"]},
        8:  {"house_lord": "Saturn",   "primary_yields": ["Longevity", "Hidden knowledge", "Occult gains"]},
        9:  {"house_lord": "Jupiter",  "primary_yields": ["Fortune", "Ancestral property", "Religious merits"]},
        10: {"house_lord": "Saturn",   "primary_yields": ["Iron", "Machinery", "Building", "Buffalo", "Status"]},
        11: {"house_lord": "Saturn",   "primary_yields": ["Steel", "Tin", "Constant cash flow"]},
        12: {"house_lord": "Rahu",     "primary_yields": ["Elephants", "Coal", "Expense control", "Bed comforts"]}
    }
}

# ============================================================================
# PATTERN 4: THE DOUBTFUL METAPHOR CIPHER
# Decoding literal item names used as metaphors for planetary afflictions.
# ============================================================================
DOUBTFUL_CIPHER_DECODER: Dict[str, Dict[str, str]] = {
    "Roof and Well": {
        "literal_meaning": "Roof (Rahu H5) attacking Well (Moon H4)",
        "prediction": "Doubtful pregnancy / Obstruction to progeny"
    },
    "Crow Line / Kawa Rekha": {
        "literal_meaning": "Saturn item (Crow) mixed with Venus H1",
        "prediction": "Doubtful or destructive character tendencies"
    },
    "Rumour & Deceiving Nature": {
        "literal_meaning": "Jupiter H8 (Rumour) + Ketu H8 (Deceiving)",
        "prediction": "A blind/hidden house generating loss of reputation and doubt"
    },
    "Ghosts and Lisping": {
        "literal_meaning": "Mercury H9 items triggering from Jupiter+Rahu Masnui",
        "prediction": "Loss of pure faith; taking up deceitful or illusionary beliefs"
    }
}

# ============================================================================
# PATTERN 5: THE 180-DEGREE HOUSE AXIS (UCHHA/NEECH SYMMETRY)
# Defines thermodynamic energy circuits and karmic opposites between houses.
# ============================================================================
THERMODYNAMIC_AXIS_PATTERN: Dict[str, Any] = {
    "description": "Houses spaced 7 apart (180 degrees) operate as zero-sum pairs. Exaltation (Uchha) in one implies Debilitation (Neech) in the precise opposite.",
    "axis_dualities": {
        "H1_H7": "Self/Authority (Sun Uchha) vs. Service/Partnership (Saturn Uchha)",
        "H4_H10": "Family/Peace (Jupiter Uchha) vs. Career/Aggression (Mars Uchha)",
        "H6_H12": "Litigation/Intellect (Mercury Uchha) vs. Luxury/Surrender (Venus Uchha)"
    },
    "uchha_rule": "Forces maximum material harvest/boost, but exacts a living sacrifice (biological penalty) against the planet's Fixed Fate items.",
    "neech_rule": "Planets sitting perfectly 180-degrees opposite drain each other (debilitation) unless BOTH are explicitly placed in their Exaltation houses."
}

# ============================================================================
# PATTERN 6: MALEFIC FATE DISTRIBUTION
# Determines whether a Malefic penalty attacks biology (Transference) or wealth.
# ============================================================================
MALEFIC_FATE_DISTRIBUTION: Dict[str, Any] = {
    "description": "When a penalty hits, it is divided into two rigid buckets based on the House and Planet Karaka.",
    "biological_transference_trap": {
        "triggers": [
            "Planet is a Biological Karaka (Sun, Moon, Jupiter, Venus, Mars)",
            "Planet resides in a Foundational/Living House (H1, H3, H4, H5, H7, H8, H9)"
        ],
        "outcome": "Strictly attacks the physical body, health, or a specific relative from the PLANET_HOUSE_ITEMS table."
    },
    "material_block": {
        "triggers": [
            "Planet is a Material/Operational Karaka (Saturn, Mercury, Rahu, Ketu)",
            "Planet resides in an Arth/Karma House (H2, H6, H10, H11, H12)"
        ],
        "outcome": "Bypasses biological relatives; strictly attacks wealth, trade, cashflow, and reputation."
    }
}

# ============================================================================
# PATTERN 7: THE CHRONOLOGICAL TRIGGER (AGE TIMING)
# Determines WHEN a fate unlocks or expires based on Maturity Ages.
# ============================================================================
MATURITY_AGE_PATTERN: Dict[str, Any] = {
    "maturity_ages": {"Jupiter": 16, "Sun": 22, "Moon": 24, "Venus": 25, "Mars": 28, "Mercury": 34, "Saturn": 36, "Rahu": 42, "Ketu": 48},
    "the_escrow_rule": "An EXTREME_BENEFIC boost (Uchha/Pakka) afflicted by an enemy doesn't die; it is delayed until the ruling planet reaches its exact maturity age.",
    "the_expiration_rule": "A Malefic Penalty typically expires the year the governing planet hits its maturity age.",
    "the_premature_activation_trap": "Forcing a major life event (e.g. marriage, building a house) before the responsible planet's maturity age triggers an instant Major Penalty."
}

# ============================================================================
# LLM PREDICTION AUTO-FORMULATOR INSTRUCTIONS
# ============================================================================
LLM_FORMULATION_GUIDE = """
When generating Lal Kitab predictions, bypass hard-coded rules and use this algorithm:

1. ASSESS SEVERITY & DIGNITY:
   - Is the planet 'Dormant' (due to empty preceding/aspect houses)? -> Power is neutralized to MINOR/MODERATE, regardless of placement.
   - Does this planet sit in its Pakka Ghar? -> Generate EXTREME_BENEFIC prediction.
   - Is it Exalted (Uchha)? -> Trigger massive material Boost, but apply biological Penalty.
   - Is it a Doubtful/Blind setup? -> Generate EXTREME_MALEFIC prediction.
   - Are two planets opposed (180 degrees) and not exalted? -> Apply Debilitated (Neech) penalty.
   - Otherwise -> Generate MINOR/MODERATE daily outcome.

2. GENERATE PREDICTION (FATE & TIMING):
   - If Benefic: The native will harvest [Yield Items] from the BENEFIC_YIELD_PATTERN. Apply MATURITY_AGE_PATTERN to specify that full wealth unlocks after the planet's maturity age.
   - If Malefic: Use MALEFIC_FATE_DISTRIBUTION to route the penalty:
       * If Biological/Foundational: Route to Transference Trap. Predict harm to the [Fixed_Living_Target]. Advise penalty lifts after the planet's maturity age.
       * If Material/Arth: Route to Material Block. Predict loss of wealth/trade. Advise penalty lifts after the planet's maturity age.
   - Did native activate a domain early? (e.g. marriage before 25): Apply the Premature Activation Trap.

3. GENERATE REMEDY (TRANSFERENCE):
   - If Malefic prediction hit a [Fixed_Living_Target], auto-generate remedy by extracting
     the [Remediable_Non_Living_Item] from the exact same PLANET_HOUSE_ITEMS array.
   - If planet is Doubtful -> Immediately add +20 to the planet-shifting priority index.
"""

# ============================================================================
# PATTERN 8: VARSHPHAL TIMING TRIGGERS (ANNUAL CHART GEOMETRY)
# Explicit event triggers derived from B.M. Goswami & Lal Diary rules
# ============================================================================
VARSHPHAL_TIMING_TRIGGERS: Dict[str, List[Dict[str, Any]]] = {
    "marriage": [
        {"desc": "Venus or Mercury in 1,2,10,11,12 AND Saturn in 1 or 10", "annual_ven_mer": [1,2,10,11,12], "annual_sat": [1, 10]},
        {"desc": "Natal Venus/Mercury in 7 returns to 7 in Annual", "natal_ven_mer": [7], "annual_ven_mer": [7]},
        {"desc": "Annual Venus and Mercury conjoined AND Saturn in 2,7,12", "annual_ven_mer_conjoined": True, "annual_sat": [2, 7, 12]},
        {"desc": "Annual Saturn in House 1", "annual_sat": [1]},
        {"desc": "Venus/Mercury returns to Natal House, No enemies in 2,7", "ven_mer_return": True, "annual_enemies_in_2_7": False},
        {"desc": "Natal H2, H7 blank, Annual Jupiter/Venus in 2,7", "natal_2_7_blank": True, "annual_jup_ven": [2, 7]},
        {"desc": "Annual Venus or Mercury in 2 or 7", "annual_ven_mer": [2, 7]}
    ],
    "finance": [
        {"desc": "Saturn 3,5 in Natal AND Ketu+Saturn/Rahu 1,3 in Annual", "natal_sat": [3, 5], "annual_ket_sat_rah": [1, 3], "polarity": "benefic"},
        {"desc": "Ketu 11 in Natal AND Saturn 11 in Annual", "natal_ket": [11], "annual_sat": [11], "polarity": "benefic"},
        {"desc": "Jup+Moon in Natal AND Jup+Moon 9 in Annual", "natal_jup_mon": True, "annual_jup_mon": [9], "polarity": "benefic"},
        {"desc": "Saturn 6 in Natal AND Mars 1-8 in Annual", "natal_sat": [6], "annual_mar": [1,2,3,4,5,6,7,8], "polarity": "benefic"},
        {"desc": "Mercury 3 in Natal AND Ketu 11 in Annual", "natal_mer": [3], "annual_ket": [11], "polarity": "malefic"},
        {"desc": "Jup+Moon 10 in Natal AND Jup+Moon 10 in Annual", "natal_jup_mon": [10], "annual_jup_mon": [10], "polarity": "malefic"},
        {"desc": "Moon 10 in Natal AND Saturn 1 in Annual", "natal_mon": [10], "annual_sat": [1], "polarity": "malefic"}
    ],
    "health": [
        {"desc": "Moon and Venus conjunct in Annual", "annual_mon_ven_conjoined": True, "target": "progeny"},
        {"desc": "Jup+Sat 2 in Natal AND Jup+Sat 2 in Annual", "natal_jup_sat": [2], "annual_jup_sat": [2], "target": "self"},
        {"desc": "Sun 5 in Natal AND Sun 5 in Annual (H8 empty)", "natal_sun": [5], "annual_sun": [5], "annual_8_empty": True, "target": "self"},
        {"desc": "Mer+Moon 11 in Natal AND Mer 11 alone in Annual", "natal_mer_mon": [11], "annual_mer_alone": [11], "target": "mother"},
        {"desc": "Sun/Moon conjunct Mer in 1,6,7,8,10 in Annual", "annual_sun_mon_mer_conjoined": [1, 6, 7, 8, 10], "target": "self"}
    ],
    "career_travel": [
        {"desc": "Sun+Sat in Natal AND Sun+Sat 7 in Annual", "natal_sun_sat": True, "annual_sun_sat": [7], "outcome": "jail"},
        {"desc": "Ketu in Natal AND Ketu 1 in Annual", "natal_ket": True, "annual_ket": [1], "outcome": "transfer"},
        {"desc": "Mercury in Natal AND Rahu/Moon/Sun 1 in Annual", "natal_mer": True, "annual_rah_mon_sun": [1], "outcome": "deception"},
        {"desc": "Mercury 2 in Natal AND Mercury 12 in Annual", "natal_mer": [2], "annual_mer": [12], "outcome": "foreign_travel"},
        {"desc": "Mercury 8 in Natal AND Mercury 1 in Annual", "natal_mer": [8], "annual_mer": [1], "outcome": "secrets"}
    ],
    "progeny": [
        {"desc": "Mercury 12 in Natal AND Saturn 2 in Annual", "natal_mer": [12], "annual_sat": [2]},
        {"desc": "Jupiter 5 in Natal AND Venus 9 in Annual", "natal_jup": [5], "annual_ven": [9]},
        {"desc": "Mercury in Natal AND Ketu 1 in Annual", "natal_mer": True, "annual_ket": [1]}
    ]
}

# ============================================================================
# PATTERN 9: AGE GATES & PROHIBITIONS
# ============================================================================
VARSHPHAL_AGE_GATES: Dict[str, List[Dict[str, Any]]] = {
    "marriage": [
        {"planet": "Mercury", "houses": [8, 9, 10, 12], "prohibit_before": 25},
        {"planet": "Saturn", "houses": [6, 7, 8], "prohibit_before": 28},
        {"planet": "Rahu", "houses": [1, 2, 3, 4, 5, 6, 7], "prohibit_between": [21, 25]}
    ],
    "real_estate": [
        {"planet": "Saturn", "houses": [1], "condition": "7_to_10_empty", "prohibit": True},
        {"ages": [36, 39], "outcome": "loss_of_progeny"},
        {"ages": [55], "outcome": "long_term_illness"}
    ]
}

# ============================================================================
# PATTERN 10: SPECIAL DESTRUCTION LOGIC (NISHT GRAH)
# ============================================================================
VARSHPHAL_SPECIAL_LOGIC = {
    "sequential_impact_rule": {
        "description": "If a planet is in H8 in Natal and moves to H7, 8, or 6 in Varshphal, it systematically negates the positive effects of those houses.",
        "natal_house": 8,
        "annual_houses": [6, 7, 8]
    }
}
