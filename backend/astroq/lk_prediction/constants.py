"""
Lal Kitab Astrological Constants.

Centralized lookup tables for Dignities, Relationships, and Aspects.
"""

PLANET_PAKKA_GHAR = {
    "Sun": [1], 
    "Moon": [4], 
    "Mars": [3, 8], 
    "Mercury": [7], 
    "Jupiter": [2, 5, 9, 11],
    "Venus": [7], 
    "Saturn": [8, 10, 11], 
    "Rahu": [12], 
    "Ketu": [6],
}

SCAPEGOATS_INFO = {
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

# Standard Pakka Ghar (Used for Fixed House Lord state)
FIXED_HOUSE_LORDS = {
    1: ["Sun"], 2: ["Jupiter"], 3: ["Mars"],
    4: ["Moon"], 5: ["Jupiter"], 6: ["Ketu"],
    7: ["Venus"], 8: ["Mars", "Saturn"], 9: ["Jupiter"],
    10: ["Saturn"], 11: ["Jupiter"], 12: ["Rahu"],
}

PLANET_EXALTATION = {
    "Sun": [1], "Moon": [2], "Mars": [10], "Mercury": [6],
    "Jupiter": [4], "Venus": [12], "Saturn": [7],
    "Rahu": [3, 6], "Ketu": [9, 12],
}

PLANET_DEBILITATION = {
    "Sun": [7], "Moon": [8], "Mars": [4], "Mercury": [12],
    "Jupiter": [10], "Venus": [6], "Saturn": [1],
    "Rahu": [9, 12], "Ketu": [3, 6],
}

SUDDEN_STRIKE_HOUSE_SETS = [
    {1, 3}, {2, 4}, {4, 6}, {5, 7}, {7, 9}, {8, 10}, {10, 12}, {1, 11}
]

FRIENDS_DATA = {
    "Sun": ["Jupiter", "Mars", "Moon"],
    "Moon": ["Sun", "Mercury"],
    "Mars": ["Sun", "Moon", "Jupiter"],
    "Mercury": ["Sun", "Venus", "Rahu"],
    "Jupiter": ["Sun", "Mars", "Moon"],
    "Venus": ["Saturn", "Mercury", "Ketu"],
    "Saturn": ["Mercury", "Venus", "Rahu"],
    "Rahu": ["Mercury", "Saturn", "Ketu"],
    "Ketu": ["Venus", "Rahu"],
}

ASPECT_STRENGTH_DATA = {
    "Jupiter": {"Jupiter": 0, "Sun": 2, "Moon": 0.5, "Venus": 3.75, "Mars": 2, "Mercury": 2, "Saturn": 3, "Rahu": 2, "Ketu": 0.83333},
    "Sun":     {"Jupiter": 0.666667, "Sun": 0, "Moon": 0.75, "Venus": 0.75, "Mars": 2, "Mercury": 0.5, "Saturn": -5, "Rahu": -5, "Ketu": 0.5},
    "Moon":    {"Jupiter": 2, "Sun": 2, "Moon": 0, "Venus": 2, "Mars": 1, "Mercury": 2, "Saturn": 0.333333, "Rahu": 0.5, "Ketu": -5},
    "Venus":   {"Jupiter": 0.5, "Sun": 0.75, "Moon": 0.5, "Venus": 0, "Mars": 1.333333, "Mercury": 1, "Saturn": 0.333333, "Rahu": 2, "Ketu": 2},
    "Mars":    {"Jupiter": 2, "Sun": 2, "Moon": 2, "Venus": 0.333333, "Mars": 0, "Mercury": 2, "Saturn": 1.333333, "Rahu": 0, "Ketu": 0.5},
    "Mercury": {"Jupiter": 0.5, "Sun": 2, "Moon": 0.5, "Venus": 1, "Mars": 1, "Mercury": 0, "Saturn": 1.25, "Rahu": 2, "Ketu": 0.25},
    "Saturn":  {"Jupiter": 1.25, "Sun": 0.666667, "Moon": 0.333333, "Venus": 1.333333, "Mars": 0.333333, "Mercury": 0.8, "Saturn": 0, "Rahu": 2, "Ketu": 0.5},
    "Rahu":    {"Jupiter": 0, "Sun": -5, "Moon": 0.5, "Venus": 0.5, "Mars": 1, "Mercury": 2, "Saturn": 2, "Rahu": 0, "Ketu": 1},
    "Ketu":    {"Jupiter": 2, "Sun": 0.5, "Moon": -5, "Venus": 2, "Mars": 0.5, "Mercury": 0.75, "Saturn": 2, "Rahu": 1, "Ketu": 0},
}

HOUSE_ASPECT_DATA = {
    "1":  {"aspects": {"Outside Help": 5, "General Condition": 7, "Confrontation": 8, "Foundation": 9, "Deception": 10, "Joint Wall": 2, "100 Percent": 7}},
    "2":  {"aspects": {"Outside Help": 6, "General Condition": 8, "Confrontation": 9, "Foundation": 10, "Deception": 11, "Joint Wall": 3, "25 Percent": 6}},
    "3":  {"aspects": {"Outside Help": 7, "General Condition": 9, "Confrontation": 10, "Foundation": 11, "Deception": 12, "Joint Wall": 4, "50 Percent": [9, 11]}},
    "4":  {"aspects": {"Outside Help": 8, "General Condition": 10, "Confrontation": 11, "Foundation": 12, "Deception": 1, "Joint Wall": 5, "100 Percent": 10}},
    "5":  {"aspects": {"Outside Help": 9, "General Condition": 11, "Confrontation": 12, "Foundation": 1, "Deception": 2, "Joint Wall": 6, "50 Percent": [9]}},
    "6":  {"aspects": {"Outside Help": 10, "General Condition": 12, "Confrontation": 1, "Foundation": 2, "Deception": 3, "Joint Wall": 7}},
    "7":  {"aspects": {"Outside Help": 11, "General Condition": 1, "Confrontation": 2, "Foundation": 3, "Deception": 4, "Joint Wall": 8}},
    "8":  {"aspects": {"Outside Help": 12, "General Condition": 2, "Confrontation": 3, "Foundation": 4, "Deception": 5, "Joint Wall": 9, "25 Percent": 2}},
    "9":  {"aspects": {"Outside Help": 1, "General Condition": 3, "Confrontation": 4, "Foundation": 5, "Deception": 6, "Joint Wall": 10}},
    "10": {"aspects": {"Outside Help": 2, "General Condition": 4, "Confrontation": 5, "Foundation": 6, "Deception": 7, "Joint Wall": 11}},
    "11": {"aspects": {"Outside Help": 3, "General Condition": 5, "Confrontation": 6, "Foundation": 7, "Deception": 8, "Joint Wall": 12}},
    "12": {"aspects": {"Outside Help": 4, "General Condition": 6, "Confrontation": 7, "Foundation": 8, "Deception": 9, "Joint Wall": 1}},
}

ENEMIES_DATA = {
    "Sun": ["Venus", "Saturn", "Rahu", "Ketu"],
    "Moon": ["Rahu", "Ketu"],
    "Mars": ["Mercury", "Ketu"],
    "Mercury": ["Moon"],
    "Jupiter": ["Venus", "Mercury"],
    "Venus": ["Sun", "Moon", "Rahu"],
    "Saturn": ["Sun", "Moon", "Mars"],
    "Rahu": ["Sun", "Venus", "Mars"],
    "Ketu": ["Moon", "Mars"],
}
