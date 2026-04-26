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

# ============================================================================
# PATTERN 11: EVENT DOMAIN CATALOGUE
# Maps every life domain/event (canonical + modern) to houses, planets, and
# the logic for classifying it as GRAHA_PHAL (fixed fate) vs RASHI_PHAL
# (conditional fate) purely from natal chart planetary dignity.
#
# Fate classification algorithm (used by NatalFateView):
#   1. Check if any key_planet sits in primary_houses or supporting_houses.
#   2. If yes AND planet is in Pakka Ghar or Exaltation house → GRAHA_PHAL
#   3. If yes AND planet is NOT dignified → RASHI_PHAL
#   4. If yes AND BOTH dignity AND debilitation signals present → HYBRID
#   5. If primary_houses all empty AND no key_planet anywhere → NEITHER
#
# Fields:
#   domain          : machine key (unique)
#   label           : human-readable label
#   category        : grouping for filtering
#   primary_houses  : houses whose occupancy signals domain is structurally active
#   supporting_houses: secondary houses (lower weight)
#   key_planets     : planets whose dignity determines GP vs RP
#   gp_condition    : plain-english description of GRAHA_PHAL condition
#   rp_condition    : plain-english description of RASHI_PHAL condition
# ============================================================================
EVENT_DOMAIN_CATALOGUE: List[Dict] = [

    # ── CANONICAL DOMAINS (13) ──────────────────────────────────────────────
    {
        "domain": "career",
        "label": "Career & Profession",
        "category": "canonical",
        "primary_houses": [10],
        "supporting_houses": [6, 2],
        "key_planets": ["Sun", "Mars", "Jupiter", "Saturn"],
        "gp_condition": "Saturn in Pakka Ghar H10, or Sun/Mars exalted in H10",
        "rp_condition": "Planets in H10 but not dignified; career conditional on annual chart",
    },
    {
        "domain": "wealth",
        "label": "Wealth & Assets",
        "category": "canonical",
        "primary_houses": [2],
        "supporting_houses": [11, 9],
        "key_planets": ["Jupiter", "Venus", "Mercury"],
        "gp_condition": "Jupiter in Pakka Ghar H2 (or H5/H9/H11), or Mercury in H7",
        "rp_condition": "Wealth planets present but not dignified; prosperity conditional",
    },
    {
        "domain": "marriage",
        "label": "Marriage & Partnerships",
        "category": "canonical",
        "primary_houses": [7],
        "supporting_houses": [2],
        "key_planets": ["Venus", "Mercury"],
        "gp_condition": "Venus in Pakka Ghar H7, or Mercury in Pakka Ghar H7",
        "rp_condition": "Venus/Mercury in chart but not in H7 dignity; marriage conditional",
    },
    {
        "domain": "progeny",
        "label": "Progeny (Children)",
        "category": "canonical",
        "primary_houses": [5],
        "supporting_houses": [],
        "key_planets": ["Jupiter", "Ketu"],
        "gp_condition": "Jupiter in H5 (Pakka Ghar) or exalted in H4",
        "rp_condition": "H5 occupied but Jupiter/Ketu not dignified; children conditional",
    },
    {
        "domain": "education",
        "label": "Education & Wisdom",
        "category": "canonical",
        "primary_houses": [5],
        "supporting_houses": [9],
        "key_planets": ["Jupiter", "Mercury"],
        "gp_condition": "Jupiter in H5 or H9; Mercury in Pakka Ghar H7 or exalted H6",
        "rp_condition": "Education planets present but not dignified; learning conditional",
    },
    {
        "domain": "property",
        "label": "Property & Land",
        "category": "canonical",
        "primary_houses": [4],
        "supporting_houses": [8],
        "key_planets": ["Moon", "Saturn", "Mars"],
        "gp_condition": "Moon in Pakka Ghar H4, or Saturn/Mars in H8 (Pakka Ghar)",
        "rp_condition": "Property planets present but not dignified; ownership conditional",
    },
    {
        "domain": "foreign_travel",
        "label": "Foreign Travel / Rest",
        "category": "canonical",
        "primary_houses": [12],
        "supporting_houses": [9],
        "key_planets": ["Rahu", "Ketu"],
        "gp_condition": "Rahu in Pakka Ghar H12; strong foreign destiny fixed at birth",
        "rp_condition": "H12 occupied but Rahu not dignified; foreign travel conditional",
    },
    {
        "domain": "litigation",
        "label": "Litigation & Enemies",
        "category": "canonical",
        "primary_houses": [6],
        "supporting_houses": [12],
        "key_planets": ["Mercury", "Ketu", "Saturn"],
        "gp_condition": "Mercury exalted in H6 (its exaltation house); enemy victory fixed",
        "rp_condition": "Litigation planets present but not dignified; outcome conditional",
    },
    {
        "domain": "courage",
        "label": "Courage & Siblings",
        "category": "canonical",
        "primary_houses": [3],
        "supporting_houses": [1],
        "key_planets": ["Mars"],
        "gp_condition": "Mars in Pakka Ghar H3; fixed courage and sibling strength",
        "rp_condition": "H3 occupied but Mars not dignified; courage conditional",
    },
    {
        "domain": "health",
        "label": "Health & Vitality",
        "category": "canonical",
        "primary_houses": [1],
        "supporting_houses": [6, 8],
        "key_planets": ["Sun", "Mars", "Saturn"],
        "gp_condition": "Sun in Pakka Ghar H1 (exaltation); strong constitutional health fixed",
        "rp_condition": "Health planets present but not dignified; vitality conditional",
    },
    {
        "domain": "spirituality",
        "label": "Spirituality & Liberation",
        "category": "canonical",
        "primary_houses": [12],
        "supporting_houses": [9],
        "key_planets": ["Ketu", "Jupiter"],
        "gp_condition": "Ketu in H12 (exaltation); spiritual liberation fixed at birth",
        "rp_condition": "H12 occupied but Ketu/Jupiter not dignified; moksha conditional",
    },
    {
        "domain": "family",
        "label": "Family & Home Life",
        "category": "canonical",
        "primary_houses": [4],
        "supporting_houses": [2],
        "key_planets": ["Moon", "Jupiter"],
        "gp_condition": "Moon in Pakka Ghar H4; stable family life fixed",
        "rp_condition": "H4 occupied but Moon not dignified; family harmony conditional",
    },
    {
        "domain": "real_estate",
        "label": "Real Estate & Property Purchase",
        "category": "canonical",
        "primary_houses": [4],
        "supporting_houses": [8, 11],
        "key_planets": ["Moon", "Saturn", "Mars"],
        "gp_condition": "Moon in H4 (Pakka Ghar) or Saturn in H8; property acquisition fixed",
        "rp_condition": "Property planets present, not dignified; purchase outcome conditional",
    },

    # ── CAREER & TECH (6) ───────────────────────────────────────────────────
    {
        "domain": "startups_entrepreneurship",
        "label": "Startups & Entrepreneurship",
        "category": "career_tech",
        "primary_houses": [10],
        "supporting_houses": [1],
        "key_planets": ["Sun", "Mercury"],
        "gp_condition": "Sun in H1 (Pakka Ghar/Exaltation); entrepreneurial authority fixed",
        "rp_condition": "H10 occupied but Sun/Mercury not dignified; startup success conditional",
    },
    {
        "domain": "software_coding",
        "label": "Software Coding & Logic",
        "category": "career_tech",
        "primary_houses": [3],
        "supporting_houses": [10],
        "key_planets": ["Mercury", "Rahu"],
        "gp_condition": "Mercury exalted in H6 or in Pakka Ghar H7; logic ability fixed",
        "rp_condition": "H3 occupied but Mercury not dignified; coding skill conditional",
    },
    {
        "domain": "ai_big_data",
        "label": "Artificial Intelligence & Big Data",
        "category": "career_tech",
        "primary_houses": [12],
        "supporting_houses": [10],
        "key_planets": ["Rahu", "Mercury"],
        "gp_condition": "Rahu in Pakka Ghar H12; AI/unseen intelligence domain fixed",
        "rp_condition": "H12 occupied but Rahu not dignified; AI domain conditional",
    },
    {
        "domain": "public_reputation",
        "label": "Public Reputation & Social Media",
        "category": "career_tech",
        "primary_houses": [10],
        "supporting_houses": [7],
        "key_planets": ["Sun", "Venus"],
        "gp_condition": "Sun in Pakka Ghar H1 or exaltation; fame/authority fixed",
        "rp_condition": "H10 occupied but Sun/Venus not dignified; reputation conditional",
    },
    {
        "domain": "corporate_politics",
        "label": "Corporate Politics & Litigation",
        "category": "career_tech",
        "primary_houses": [6],
        "supporting_houses": [12],
        "key_planets": ["Saturn", "Mercury"],
        "gp_condition": "Mercury exalted H6 or Saturn in H10 (Pakka Ghar); political power fixed",
        "rp_condition": "H6 occupied but planets not dignified; corporate outcomes conditional",
    },
    {
        "domain": "consulting_coaching",
        "label": "Consulting & Coaching",
        "category": "career_tech",
        "primary_houses": [9],
        "supporting_houses": [2],
        "key_planets": ["Jupiter"],
        "gp_condition": "Jupiter in H9 (Pucca Ghar); guru/wisdom role fixed at birth",
        "rp_condition": "H9 occupied but Jupiter not dignified; teaching success conditional",
    },

    # ── FINANCE & INVESTMENTS (5) ───────────────────────────────────────────
    {
        "domain": "cryptocurrency",
        "label": "Cryptocurrency & Digital Assets",
        "category": "finance",
        "primary_houses": [2],
        "supporting_houses": [12],
        "key_planets": ["Rahu", "Jupiter"],
        "gp_condition": "Rahu in Pakka Ghar H12; shadow/digital wealth domain fixed",
        "rp_condition": "H2/H12 occupied but Rahu/Jupiter not dignified; crypto gains conditional",
    },
    {
        "domain": "stock_market_trading",
        "label": "Stock Market & Trading",
        "category": "finance",
        "primary_houses": [5],
        "supporting_houses": [2],
        "key_planets": ["Mercury", "Rahu"],
        "gp_condition": "Mercury in Pakka Ghar H7; calculation and trading acumen fixed",
        "rp_condition": "H5 occupied but Mercury/Rahu not dignified; market gains conditional",
    },
    {
        "domain": "gold_bonds",
        "label": "Gold & Bonds (SGBs)",
        "category": "finance",
        "primary_houses": [2],
        "supporting_houses": [9],
        "key_planets": ["Jupiter", "Sun"],
        "gp_condition": "Jupiter in H2 (Pakka Ghar); gold/fixed wealth accumulation fixed",
        "rp_condition": "H2 occupied but Jupiter/Sun not dignified; gold gains conditional",
    },
    {
        "domain": "inheritance",
        "label": "Inheritance & Hidden Wealth",
        "category": "finance",
        "primary_houses": [8],
        "supporting_houses": [2],
        "key_planets": ["Saturn", "Mars"],
        "gp_condition": "Saturn in H8 (Pakka Ghar); hidden/ancestral wealth access fixed",
        "rp_condition": "H8 occupied but Saturn/Mars not dignified; inheritance conditional",
    },
    {
        "domain": "ecommerce_retail",
        "label": "E-commerce & Retail Business",
        "category": "finance",
        "primary_houses": [7],
        "supporting_houses": [11],
        "key_planets": ["Venus", "Mercury"],
        "gp_condition": "Venus in Pakka Ghar H7; business/trade partnerships fixed",
        "rp_condition": "H7 occupied but Venus/Mercury not dignified; business conditional",
    },

    # ── HOME, LIFESTYLE & SUSTAINABILITY (5) ────────────────────────────────
    {
        "domain": "solar_energy",
        "label": "Solar Energy (Rooftop/Agrivoltaics)",
        "category": "home_lifestyle",
        "primary_houses": [1],
        "supporting_houses": [4],
        "key_planets": ["Sun"],
        "gp_condition": "Sun in Pakka Ghar H1 or exaltation H1; solar power destiny fixed",
        "rp_condition": "H1 occupied but Sun not dignified; solar ventures conditional",
    },
    {
        "domain": "sustainable_farming",
        "label": "Sustainable Farming & Hydroponics",
        "category": "home_lifestyle",
        "primary_houses": [4],
        "supporting_houses": [8],
        "key_planets": ["Moon", "Sun"],
        "gp_condition": "Moon in Pakka Ghar H4; farming/earth domain fixed at birth",
        "rp_condition": "H4 occupied but Moon/Sun not dignified; farming success conditional",
    },
    {
        "domain": "smart_homes",
        "label": "Smart Homes & Gadgets",
        "category": "home_lifestyle",
        "primary_houses": [4],
        "supporting_houses": [3],
        "key_planets": ["Rahu", "Moon"],
        "gp_condition": "Rahu in Pakka Ghar H12 or Moon in H4; tech-home destiny fixed",
        "rp_condition": "H4 occupied but Rahu/Moon not dignified; smart-home outcomes conditional",
    },
    {
        "domain": "automobiles_travel",
        "label": "Automobiles & Travel",
        "category": "home_lifestyle",
        "primary_houses": [4],
        "supporting_houses": [12],
        "key_planets": ["Venus", "Moon"],
        "gp_condition": "Venus in Pakka Ghar H7 or Moon in H4; vehicle/travel promise fixed",
        "rp_condition": "H4 occupied but Venus/Moon not dignified; vehicle outcomes conditional",
    },
    {
        "domain": "spirituality_wellness",
        "label": "Spirituality & Mental Wellness",
        "category": "home_lifestyle",
        "primary_houses": [12],
        "supporting_houses": [4],
        "key_planets": ["Ketu", "Moon"],
        "gp_condition": "Ketu in H12 (exaltation); liberation and peace fixed at birth",
        "rp_condition": "H12 occupied but Ketu/Moon not dignified; inner peace conditional",
    },

    # ── HEALTH & WELLNESS (5) ────────────────────────────────────────────────
    {
        "domain": "anxiety_digital_fatigue",
        "label": "Anxiety & Digital Fatigue",
        "category": "health_wellness",
        "primary_houses": [1],
        "supporting_houses": [12],
        "key_planets": ["Moon", "Rahu"],
        "gp_condition": "Sun in H1 strongly; mental constitution fixed and resilient",
        "rp_condition": "Moon/Rahu in H1 or H12 not dignified; anxiety levels conditional",
    },
    {
        "domain": "gym_biohacking",
        "label": "Gym, Vitality & Biohacking",
        "category": "health_wellness",
        "primary_houses": [1],
        "supporting_houses": [3],
        "key_planets": ["Mars", "Sun"],
        "gp_condition": "Mars in Pakka Ghar H3 or Sun in H1; physical strength fixed",
        "rp_condition": "H1 occupied but Mars/Sun not dignified; physical vitality conditional",
    },
    {
        "domain": "chronic_lifestyle_diseases",
        "label": "Chronic Lifestyle Diseases",
        "category": "health_wellness",
        "primary_houses": [6],
        "supporting_houses": [8],
        "key_planets": ["Saturn", "Venus"],
        "gp_condition": "Saturn in Pakka Ghar H10; structural health issues long-term fixed",
        "rp_condition": "H6 occupied but Saturn/Venus not dignified; chronic risk conditional",
    },
    {
        "domain": "professional_networking",
        "label": "Professional Networking",
        "category": "health_wellness",
        "primary_houses": [11],
        "supporting_houses": [7],
        "key_planets": ["Mercury", "Saturn"],
        "gp_condition": "Mercury in Pakka Ghar H7; networking and communication fixed",
        "rp_condition": "H11 occupied but Mercury/Saturn not dignified; network growth conditional",
    },
    {
        "domain": "education_online_learning",
        "label": "Education & Online Learning",
        "category": "health_wellness",
        "primary_houses": [5],
        "supporting_houses": [2],
        "key_planets": ["Jupiter", "Mercury"],
        "gp_condition": "Jupiter in H5 or H2 (Pakka Ghar); learning destiny fixed",
        "rp_condition": "H5 occupied but Jupiter/Mercury not dignified; learning conditional",
    },

    # ── TECHNOLOGY & DIGITAL INFRA (6) ──────────────────────────────────────
    {
        "domain": "logic_coding",
        "label": "Logic Design & Recursive Coding",
        "category": "tech_infra",
        "primary_houses": [3],
        "supporting_houses": [10],
        "key_planets": ["Mercury"],
        "gp_condition": "Mercury exalted H6 or Pakka Ghar H7; analytical coding fixed",
        "rp_condition": "H3 occupied but Mercury not dignified; coding mastery conditional",
    },
    {
        "domain": "local_llm_hosting",
        "label": "Local LLM Hosting & Private Nodes",
        "category": "tech_infra",
        "primary_houses": [12],
        "supporting_houses": [4],
        "key_planets": ["Rahu", "Moon"],
        "gp_condition": "Rahu in Pakka Ghar H12; hidden/private computation fixed",
        "rp_condition": "H12 occupied but Rahu not dignified; private AI hosting conditional",
    },
    {
        "domain": "cloud_computing",
        "label": "Cloud Computing & Vast Data Sets",
        "category": "tech_infra",
        "primary_houses": [12],
        "supporting_houses": [3],
        "key_planets": ["Rahu", "Mercury"],
        "gp_condition": "Rahu in Pakka Ghar H12 and Mercury dignified; cloud scale fixed",
        "rp_condition": "H12 occupied but planets not dignified; cloud success conditional",
    },
    {
        "domain": "hardware_servers",
        "label": "Hardware Troubleshooting & Servers",
        "category": "tech_infra",
        "primary_houses": [6],
        "supporting_houses": [8],
        "key_planets": ["Saturn", "Mars"],
        "gp_condition": "Saturn in Pakka Ghar H10 or H8; hardware/metal work fixed",
        "rp_condition": "H6 occupied but Saturn/Mars not dignified; server work conditional",
    },
    {
        "domain": "cybersecurity",
        "label": "Cybersecurity & Ethical Hacking",
        "category": "tech_infra",
        "primary_houses": [6],
        "supporting_houses": [12],
        "key_planets": ["Rahu", "Mercury"],
        "gp_condition": "Mercury exalted H6 and Rahu in H12; security/detection fixed",
        "rp_condition": "H6 occupied but Rahu/Mercury not dignified; security work conditional",
    },
    {
        "domain": "app_launch_branding",
        "label": "App Launch & Digital Branding",
        "category": "tech_infra",
        "primary_houses": [10],
        "supporting_houses": [7],
        "key_planets": ["Sun", "Venus"],
        "gp_condition": "Sun in Pakka Ghar H1; public authority/brand visibility fixed",
        "rp_condition": "H10 occupied but Sun/Venus not dignified; app success conditional",
    },

    # ── MODERN FINANCE (6) ───────────────────────────────────────────────────
    {
        "domain": "sovereign_gold_bonds",
        "label": "Sovereign Gold Bonds (SGBs)",
        "category": "modern_finance",
        "primary_houses": [2],
        "supporting_houses": [11],
        "key_planets": ["Sun", "Jupiter"],
        "gp_condition": "Jupiter in Pakka Ghar H2; government-backed gold wealth fixed",
        "rp_condition": "H2 occupied but Sun/Jupiter not dignified; SGB gains conditional",
    },
    {
        "domain": "mutual_funds_sip",
        "label": "Mutual Funds & Long-term SIPs",
        "category": "modern_finance",
        "primary_houses": [2],
        "supporting_houses": [5],
        "key_planets": ["Jupiter"],
        "gp_condition": "Jupiter in Pakka Ghar H2/H5/H9/H11; long-term wealth fixed",
        "rp_condition": "H2 occupied but Jupiter not dignified; fund growth conditional",
    },
    {
        "domain": "digital_tokens",
        "label": "Cryptocurrency & Digital Tokens",
        "category": "modern_finance",
        "primary_houses": [12],
        "supporting_houses": [8],
        "key_planets": ["Rahu", "Ketu"],
        "gp_condition": "Rahu in Pakka Ghar H12 and Ketu in H6; shadow wealth fixed",
        "rp_condition": "H12 occupied but Rahu/Ketu not dignified; token gains conditional",
    },
    {
        "domain": "venture_capital",
        "label": "Venture Capital & Angel Investing",
        "category": "modern_finance",
        "primary_houses": [5],
        "supporting_houses": [11],
        "key_planets": ["Rahu", "Sun"],
        "gp_condition": "Sun in Pakka Ghar H1; authority to back others fixed",
        "rp_condition": "H5 occupied but Rahu/Sun not dignified; VC success conditional",
    },
    {
        "domain": "premature_asset_redemption",
        "label": "Premature Asset Redemption (Risk)",
        "category": "modern_finance",
        "primary_houses": [8],
        "supporting_houses": [12],
        "key_planets": ["Saturn", "Moon"],
        "gp_condition": "Saturn in H8 (Pakka Ghar); long-duration asset holding fixed",
        "rp_condition": "H8 occupied but Saturn not dignified; early redemption risk conditional",
    },
    {
        "domain": "corporate_audits",
        "label": "Corporate Audits & Tax Planning",
        "category": "modern_finance",
        "primary_houses": [6],
        "supporting_houses": [2],
        "key_planets": ["Mercury", "Saturn"],
        "gp_condition": "Mercury exalted H6; systematic audit/accounting ability fixed",
        "rp_condition": "H6 occupied but Mercury/Saturn not dignified; audit outcomes conditional",
    },

    # ── SUSTAINABLE INNOVATION (5) ───────────────────────────────────────────
    {
        "domain": "rooftop_solar_agrivoltaics",
        "label": "Rooftop Solar & Agrivoltaics",
        "category": "sustainable",
        "primary_houses": [1],
        "supporting_houses": [10],
        "key_planets": ["Sun"],
        "gp_condition": "Sun in Pakka Ghar H1 (exaltation); solar enterprise fixed",
        "rp_condition": "H1 occupied but Sun not dignified; solar ROI conditional",
    },
    {
        "domain": "hydroponics_farming",
        "label": "Hydroponics & Precision Farming",
        "category": "sustainable",
        "primary_houses": [4],
        "supporting_houses": [6],
        "key_planets": ["Moon", "Ketu"],
        "gp_condition": "Moon in Pakka Ghar H4; water/crop farming fixed at birth",
        "rp_condition": "H4 occupied but Moon/Ketu not dignified; hydro-farming conditional",
    },
    {
        "domain": "cordyceps_mushroom",
        "label": "Cordyceps & Mushroom Cultivation",
        "category": "sustainable",
        "primary_houses": [8],
        "supporting_houses": [12],
        "key_planets": ["Rahu", "Moon"],
        "gp_condition": "Rahu in Pakka Ghar H12; hidden/underground growth enterprises fixed",
        "rp_condition": "H8 occupied but Rahu/Moon not dignified; specialty farming conditional",
    },
    {
        "domain": "electric_vehicles",
        "label": "Electric Vehicles (EVs) & Charging",
        "category": "sustainable",
        "primary_houses": [4],
        "supporting_houses": [3],
        "key_planets": ["Venus", "Rahu"],
        "gp_condition": "Venus in Pakka Ghar H7 or H2; luxury vehicle acquisition fixed",
        "rp_condition": "H4 occupied but Venus/Rahu not dignified; EV ownership conditional",
    },
    {
        "domain": "government_subsidies",
        "label": "Government Subsidies & Schemes",
        "category": "sustainable",
        "primary_houses": [11],
        "supporting_houses": [9],
        "key_planets": ["Jupiter", "Sun"],
        "gp_condition": "Jupiter in H11 (Pucca Ghar) and Sun dignified; state support fixed",
        "rp_condition": "H11 occupied but Jupiter/Sun not dignified; subsidy access conditional",
    },

    # ── SOCIAL & PSYCHOLOGICAL (5) ────────────────────────────────────────────
    {
        "domain": "social_media_influencing",
        "label": "Social Media Influencing",
        "category": "social_psych",
        "primary_houses": [10],
        "supporting_houses": [11],
        "key_planets": ["Sun", "Venus"],
        "gp_condition": "Sun in Pakka Ghar H1; fame/authority projected outward fixed",
        "rp_condition": "H10 occupied but Sun/Venus not dignified; influence conditional",
    },
    {
        "domain": "anxiety_info_overload",
        "label": "Anxiety & Information Overload",
        "category": "social_psych",
        "primary_houses": [12],
        "supporting_houses": [1],
        "key_planets": ["Moon", "Rahu"],
        "gp_condition": "Moon in Pakka Ghar H4; inner mind stable and grounded (resilience fixed)",
        "rp_condition": "Moon/Rahu not dignified; anxiety and overload risk conditional",
    },
    {
        "domain": "professional_networking_linkedin",
        "label": "Professional Networking (LinkedIn/Online)",
        "category": "social_psych",
        "primary_houses": [7],
        "supporting_houses": [11],
        "key_planets": ["Mercury", "Saturn"],
        "gp_condition": "Mercury in Pakka Ghar H7; networked communication destiny fixed",
        "rp_condition": "H7 occupied but Mercury/Saturn not dignified; network quality conditional",
    },
    {
        "domain": "remote_work",
        "label": "Remote Work / Work From Home",
        "category": "social_psych",
        "primary_houses": [4],
        "supporting_houses": [10],
        "key_planets": ["Moon", "Saturn"],
        "gp_condition": "Moon in H4 (Pakka Ghar); home as workspace fixed",
        "rp_condition": "H4 occupied but Moon/Saturn not dignified; WFH productivity conditional",
    },
    {
        "domain": "legal_agreements",
        "label": "Legal Agreements & Smart Contracts",
        "category": "social_psych",
        "primary_houses": [7],
        "supporting_houses": [6],
        "key_planets": ["Mercury", "Venus"],
        "gp_condition": "Mercury in Pakka Ghar H7; contract and partnership logic fixed",
        "rp_condition": "H7 occupied but Mercury/Venus not dignified; legal outcomes conditional",
    },
]
