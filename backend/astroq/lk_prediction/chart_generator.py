"""
Module 0: Chart Generator

Provides the foundation for the Lal Kitab Prediction Pipeline by:
1. Translating DOB/TOB/POB and geographical coordinates into an astronomical chart using `vedicastro`.
2. Extracting KP or Vedic planet/house mappings.
3. Generating the Natal Chart in `ChartData` format.
4. Generating all 75 Varshaphal (Annual) charts dynamically using Lal Kitab progression rules.

This eliminates the need for external pipeline dependency when generating the raw inputs for prediction.
"""

import math
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dateutil.relativedelta import relativedelta

from astroq.lk_prediction.constants import (
    PLANET_EXALTATION, PLANET_DEBILITATION, FIXED_HOUSE_LORDS
)
import dateutil.parser

try:
    from geopy.geocoders import Nominatim
    from timezonefinder import TimezoneFinder
    import pytz
except ImportError:
    pass  # Allow tests to run even if missing, unless called

try:
    from vedicastro.VedicAstro import VedicHoroscopeData
except ImportError:
    pass

logger = logging.getLogger("astroq.lk_prediction.chart_generator")


class ChartGenerator:
    """
    Generates ChartData dicts suitable for the LKPredictionPipeline.
    """

    CHART_SYSTEMS = ["kp", "vedic"]
    
    # Authentic 120-Year Lal Kitab Varshphal Movement Matrix (1952 Edition)
    # Maps Natal House (key) -> Annual House (value) based on Year of Life.
    YEAR_MATRIX = {   1: {1: 1, 2: 9, 3: 10, 4: 3, 5: 5, 6: 2, 7: 11, 8: 7, 9: 6, 10: 12, 11: 4, 12: 8},
        2: {1: 4, 2: 1, 3: 12, 4: 9, 5: 3, 6: 7, 7: 5, 8: 6, 9: 2, 10: 8, 11: 10, 12: 11},
        3: {1: 9, 2: 4, 3: 1, 4: 2, 5: 8, 6: 3, 7: 10, 8: 5, 9: 7, 10: 11, 11: 12, 12: 6},
        4: {1: 3, 2: 8, 3: 4, 4: 1, 5: 10, 6: 9, 7: 6, 8: 11, 9: 5, 10: 7, 11: 2, 12: 12},
        5: {1: 11, 2: 3, 3: 8, 4: 4, 5: 1, 6: 5, 7: 9, 8: 2, 9: 12, 10: 6, 11: 7, 12: 10},
        6: {1: 5, 2: 12, 3: 3, 4: 8, 5: 4, 6: 11, 7: 2, 8: 9, 9: 1, 10: 10, 11: 6, 12: 7},
        7: {1: 7, 2: 6, 3: 9, 4: 5, 5: 12, 6: 4, 7: 1, 8: 10, 9: 11, 10: 2, 11: 8, 12: 3},
        8: {1: 2, 2: 7, 3: 6, 4: 12, 5: 9, 6: 10, 7: 3, 8: 1, 9: 8, 10: 5, 11: 11, 12: 4},
        9: {1: 12, 2: 2, 3: 7, 4: 6, 5: 11, 6: 1, 7: 8, 8: 4, 9: 10, 10: 3, 11: 5, 12: 9},
        10: {1: 10, 2: 11, 3: 2, 4: 7, 5: 6, 6: 12, 7: 4, 8: 8, 9: 3, 10: 1, 11: 9, 12: 5},
        11: {1: 8, 2: 5, 3: 11, 4: 10, 5: 7, 6: 6, 7: 12, 8: 3, 9: 9, 10: 4, 11: 1, 12: 2},
        12: {1: 6, 2: 10, 3: 5, 4: 11, 5: 2, 6: 8, 7: 7, 8: 12, 9: 4, 10: 9, 11: 3, 12: 1},
        13: {1: 1, 2: 5, 3: 10, 4: 8, 5: 11, 6: 6, 7: 7, 8: 2, 9: 12, 10: 3, 11: 9, 12: 4},
        14: {1: 4, 2: 1, 3: 3, 4: 2, 5: 5, 6: 7, 7: 8, 8: 11, 9: 6, 10: 12, 11: 10, 12: 9},
        15: {1: 9, 2: 4, 3: 1, 4: 6, 5: 8, 6: 5, 7: 2, 8: 7, 9: 11, 10: 10, 11: 12, 12: 3},
        16: {1: 3, 2: 9, 3: 4, 4: 1, 5: 12, 6: 8, 7: 6, 8: 5, 9: 2, 10: 7, 11: 11, 12: 10},
        17: {1: 11, 2: 3, 3: 9, 4: 4, 5: 1, 6: 10, 7: 5, 8: 6, 9: 7, 10: 8, 11: 2, 12: 12},
        18: {1: 5, 2: 11, 3: 6, 4: 9, 5: 4, 6: 1, 7: 12, 8: 8, 9: 10, 10: 2, 11: 3, 12: 7},
        19: {1: 7, 2: 10, 3: 11, 4: 3, 5: 9, 6: 4, 7: 1, 8: 12, 9: 8, 10: 5, 11: 6, 12: 2},
        20: {1: 2, 2: 7, 3: 5, 4: 12, 5: 3, 6: 9, 7: 10, 8: 1, 9: 4, 10: 6, 11: 8, 12: 11},
        21: {1: 12, 2: 2, 3: 8, 4: 5, 5: 10, 6: 3, 7: 9, 8: 4, 9: 1, 10: 11, 11: 7, 12: 6},
        22: {1: 10, 2: 12, 3: 2, 4: 7, 5: 6, 6: 11, 7: 3, 8: 9, 9: 5, 10: 1, 11: 4, 12: 8},
        23: {1: 8, 2: 6, 3: 12, 4: 10, 5: 7, 6: 2, 7: 11, 8: 3, 9: 9, 10: 4, 11: 1, 12: 5},
        24: {1: 6, 2: 8, 3: 7, 4: 11, 5: 2, 6: 12, 7: 4, 8: 10, 9: 3, 10: 9, 11: 5, 12: 1},
        25: {1: 1, 2: 6, 3: 10, 4: 3, 5: 2, 6: 8, 7: 7, 8: 4, 9: 11, 10: 5, 11: 12, 12: 9},
        26: {1: 4, 2: 1, 3: 3, 4: 8, 5: 6, 6: 7, 7: 2, 8: 11, 9: 12, 10: 9, 11: 5, 12: 10},
        27: {1: 9, 2: 4, 3: 1, 4: 5, 5: 10, 6: 11, 7: 12, 8: 7, 9: 6, 10: 8, 11: 2, 12: 3},
        28: {1: 3, 2: 9, 3: 4, 4: 1, 5: 11, 6: 5, 7: 6, 8: 8, 9: 7, 10: 2, 11: 10, 12: 12},
        29: {1: 11, 2: 3, 3: 9, 4: 4, 5: 1, 6: 6, 7: 8, 8: 2, 9: 10, 10: 12, 11: 7, 12: 5},
        30: {1: 5, 2: 11, 3: 8, 4: 9, 5: 4, 6: 1, 7: 3, 8: 12, 9: 2, 10: 10, 11: 6, 12: 7},
        31: {1: 7, 2: 5, 3: 11, 4: 12, 5: 9, 6: 4, 7: 1, 8: 10, 9: 8, 10: 6, 11: 3, 12: 2},
        32: {1: 2, 2: 7, 3: 5, 4: 11, 5: 3, 6: 12, 7: 10, 8: 6, 9: 4, 10: 1, 11: 9, 12: 8},
        33: {1: 12, 2: 2, 3: 6, 4: 10, 5: 8, 6: 3, 7: 9, 8: 1, 9: 5, 10: 7, 11: 4, 12: 11},
        34: {1: 10, 2: 12, 3: 2, 4: 7, 5: 5, 6: 9, 7: 11, 8: 3, 9: 1, 10: 4, 11: 8, 12: 6},
        35: {1: 8, 2: 10, 3: 12, 4: 6, 5: 7, 6: 2, 7: 4, 8: 5, 9: 9, 10: 3, 11: 11, 12: 1},
        36: {1: 6, 2: 8, 3: 7, 4: 2, 5: 12, 6: 10, 7: 5, 8: 9, 9: 3, 10: 11, 11: 1, 12: 4},
        37: {1: 1, 2: 3, 3: 10, 4: 6, 5: 9, 6: 12, 7: 7, 8: 5, 9: 11, 10: 2, 11: 4, 12: 8},
        38: {1: 4, 2: 1, 3: 3, 4: 8, 5: 6, 6: 5, 7: 2, 8: 7, 9: 12, 10: 10, 11: 11, 12: 9},
        39: {1: 9, 2: 4, 3: 1, 4: 12, 5: 8, 6: 2, 7: 10, 8: 11, 9: 6, 10: 3, 11: 5, 12: 7},
        40: {1: 3, 2: 9, 3: 4, 4: 1, 5: 11, 6: 8, 7: 6, 8: 12, 9: 2, 10: 5, 11: 7, 12: 10},
        41: {1: 11, 2: 7, 3: 9, 4: 4, 5: 1, 6: 6, 7: 8, 8: 2, 9: 10, 10: 12, 11: 3, 12: 5},
        42: {1: 5, 2: 11, 3: 8, 4: 9, 5: 12, 6: 1, 7: 3, 8: 4, 9: 7, 10: 6, 11: 10, 12: 2},
        43: {1: 7, 2: 5, 3: 11, 4: 2, 5: 3, 6: 4, 7: 1, 8: 10, 9: 8, 10: 9, 11: 12, 12: 6},
        44: {1: 2, 2: 10, 3: 5, 4: 3, 5: 4, 6: 9, 7: 12, 8: 8, 9: 1, 10: 7, 11: 6, 12: 11},
        45: {1: 12, 2: 2, 3: 6, 4: 5, 5: 10, 6: 7, 7: 9, 8: 1, 9: 3, 10: 11, 11: 8, 12: 4},
        46: {1: 10, 2: 12, 3: 2, 4: 7, 5: 5, 6: 3, 7: 11, 8: 6, 9: 4, 10: 8, 11: 9, 12: 1},
        47: {1: 8, 2: 6, 3: 12, 4: 10, 5: 7, 6: 11, 7: 4, 8: 9, 9: 5, 10: 1, 11: 2, 12: 3},
        48: {1: 6, 2: 8, 3: 7, 4: 11, 5: 2, 6: 10, 7: 5, 8: 3, 9: 9, 10: 4, 11: 1, 12: 12},
        49: {1: 1, 2: 7, 3: 10, 4: 6, 5: 12, 6: 2, 7: 8, 8: 4, 9: 11, 10: 9, 11: 3, 12: 5},
        50: {1: 4, 2: 1, 3: 8, 4: 3, 5: 6, 6: 12, 7: 5, 8: 11, 9: 2, 10: 7, 11: 10, 12: 9},
        51: {1: 9, 2: 4, 3: 1, 4: 2, 5: 8, 6: 3, 7: 12, 8: 6, 9: 7, 10: 10, 11: 5, 12: 11},
        52: {1: 3, 2: 9, 3: 4, 4: 1, 5: 11, 6: 7, 7: 2, 8: 12, 9: 5, 10: 8, 11: 6, 12: 10},
        53: {1: 11, 2: 10, 3: 7, 4: 4, 5: 1, 6: 6, 7: 3, 8: 9, 9: 12, 10: 5, 11: 8, 12: 2},
        54: {1: 5, 2: 11, 3: 3, 4: 9, 5: 4, 6: 1, 7: 6, 8: 2, 9: 10, 10: 12, 11: 7, 12: 8},
        55: {1: 7, 2: 5, 3: 11, 4: 8, 5: 3, 6: 9, 7: 1, 8: 10, 9: 6, 10: 4, 11: 2, 12: 12},
        56: {1: 2, 2: 3, 3: 5, 4: 11, 5: 9, 6: 4, 7: 10, 8: 1, 9: 8, 10: 6, 11: 12, 12: 7},
        57: {1: 12, 2: 2, 3: 6, 4: 5, 5: 10, 6: 8, 7: 9, 8: 7, 9: 4, 10: 11, 11: 1, 12: 3},
        58: {1: 10, 2: 12, 3: 2, 4: 7, 5: 5, 6: 11, 7: 4, 8: 8, 9: 3, 10: 1, 11: 9, 12: 6},
        59: {1: 8, 2: 6, 3: 12, 4: 10, 5: 7, 6: 5, 7: 11, 8: 3, 9: 9, 10: 2, 11: 4, 12: 1},
        60: {1: 6, 2: 8, 3: 9, 4: 12, 5: 2, 6: 10, 7: 7, 8: 5, 9: 1, 10: 3, 11: 11, 12: 4},
        61: {1: 1, 2: 11, 3: 10, 4: 6, 5: 12, 6: 2, 7: 4, 8: 7, 9: 8, 10: 9, 11: 5, 12: 3},
        62: {1: 4, 2: 1, 3: 6, 4: 8, 5: 3, 6: 12, 7: 2, 8: 10, 9: 9, 10: 5, 11: 7, 12: 11},
        63: {1: 9, 2: 4, 3: 1, 4: 2, 5: 8, 6: 6, 7: 12, 8: 11, 9: 7, 10: 3, 11: 10, 12: 5},
        64: {1: 3, 2: 9, 3: 4, 4: 1, 5: 6, 6: 8, 7: 7, 8: 12, 9: 5, 10: 2, 11: 11, 12: 10},
        65: {1: 11, 2: 2, 3: 9, 4: 4, 5: 1, 6: 5, 7: 8, 8: 3, 9: 10, 10: 12, 11: 6, 12: 7},
        66: {1: 5, 2: 10, 3: 3, 4: 9, 5: 2, 6: 1, 7: 6, 8: 8, 9: 11, 10: 7, 11: 12, 12: 4},
        67: {1: 7, 2: 5, 3: 11, 4: 3, 5: 10, 6: 4, 7: 1, 8: 9, 9: 12, 10: 6, 11: 8, 12: 2},
        68: {1: 2, 2: 3, 3: 5, 4: 11, 5: 9, 6: 7, 7: 10, 8: 1, 9: 6, 10: 8, 11: 4, 12: 12},
        69: {1: 12, 2: 8, 3: 7, 4: 5, 5: 11, 6: 3, 7: 9, 8: 4, 9: 1, 10: 10, 11: 2, 12: 6},
        70: {1: 10, 2: 12, 3: 2, 4: 7, 5: 5, 6: 11, 7: 3, 8: 6, 9: 4, 10: 1, 11: 9, 12: 8},
        71: {1: 8, 2: 6, 3: 12, 4: 10, 5: 7, 6: 9, 7: 11, 8: 5, 9: 2, 10: 4, 11: 3, 12: 1},
        72: {1: 6, 2: 7, 3: 8, 4: 12, 5: 4, 6: 10, 7: 5, 8: 2, 9: 3, 10: 11, 11: 1, 12: 9},
        73: {1: 1, 2: 4, 3: 10, 4: 6, 5: 12, 6: 11, 7: 7, 8: 8, 9: 2, 10: 5, 11: 9, 12: 3},
        74: {1: 4, 2: 2, 3: 3, 4: 8, 5: 6, 6: 12, 7: 1, 8: 11, 9: 7, 10: 10, 11: 5, 12: 9},
        75: {1: 9, 2: 10, 3: 1, 4: 3, 5: 8, 6: 6, 7: 2, 8: 7, 9: 5, 10: 4, 11: 12, 12: 11},
        76: {1: 3, 2: 9, 3: 6, 4: 1, 5: 2, 6: 8, 7: 5, 8: 11, 9: 11, 10: 7, 11: 10, 12: 4},
        77: {1: 11, 2: 3, 3: 9, 4: 4, 5: 1, 6: 2, 7: 8, 8: 10, 9: 12, 10: 6, 11: 7, 12: 5},
        78: {1: 5, 2: 11, 3: 4, 4: 9, 5: 7, 6: 1, 7: 6, 8: 2, 9: 10, 10: 12, 11: 3, 12: 8},
        79: {1: 7, 2: 5, 3: 11, 4: 2, 5: 9, 6: 4, 7: 12, 8: 6, 9: 3, 10: 1, 11: 8, 12: 10},
        80: {1: 2, 2: 8, 3: 5, 4: 11, 5: 4, 6: 7, 7: 10, 8: 3, 9: 1, 10: 9, 11: 6, 12: 12},
        81: {1: 12, 2: 1, 3: 7, 4: 5, 5: 11, 6: 10, 7: 9, 8: 4, 9: 8, 10: 3, 11: 2, 12: 6},
        82: {1: 10, 2: 12, 3: 2, 4: 7, 5: 5, 6: 3, 7: 4, 8: 9, 9: 6, 10: 8, 11: 11, 12: 1},
        83: {1: 8, 2: 6, 3: 12, 4: 10, 5: 3, 6: 5, 7: 11, 8: 1, 9: 9, 10: 2, 11: 4, 12: 7},
        84: {1: 6, 2: 7, 3: 8, 4: 12, 5: 10, 6: 9, 7: 3, 8: 5, 9: 4, 10: 11, 11: 1, 12: 2},
        85: {1: 1, 2: 3, 3: 10, 4: 6, 5: 12, 6: 2, 7: 8, 8: 11, 9: 5, 10: 4, 11: 9, 12: 7},
        86: {1: 4, 2: 1, 3: 8, 4: 3, 5: 6, 6: 12, 7: 11, 8: 2, 9: 7, 10: 9, 11: 10, 12: 5},
        87: {1: 9, 2: 4, 3: 1, 4: 7, 5: 3, 6: 8, 7: 12, 8: 5, 9: 2, 10: 6, 11: 11, 12: 10},
        88: {1: 3, 2: 9, 3: 4, 4: 1, 5: 8, 6: 10, 7: 2, 8: 7, 9: 12, 10: 5, 11: 6, 12: 11},
        89: {1: 11, 2: 10, 3: 9, 4: 4, 5: 1, 6: 6, 7: 7, 8: 12, 9: 3, 10: 8, 11: 5, 12: 2},
        90: {1: 5, 2: 11, 3: 6, 4: 9, 5: 4, 6: 1, 7: 3, 8: 8, 9: 10, 10: 2, 11: 7, 12: 12},
        91: {1: 7, 2: 5, 3: 11, 4: 2, 5: 10, 6: 4, 7: 6, 8: 9, 9: 8, 10: 3, 11: 12, 12: 1},
        92: {1: 2, 2: 7, 3: 5, 4: 11, 5: 9, 6: 3, 7: 10, 8: 4, 9: 1, 10: 12, 11: 8, 12: 6},
        93: {1: 12, 2: 8, 3: 7, 4: 5, 5: 2, 6: 11, 7: 9, 8: 1, 9: 6, 10: 10, 11: 3, 12: 4},
        94: {1: 10, 2: 12, 3: 2, 4: 8, 5: 11, 6: 5, 7: 4, 8: 6, 9: 9, 10: 7, 11: 1, 12: 3},
        95: {1: 8, 2: 6, 3: 12, 4: 10, 5: 5, 6: 7, 7: 1, 8: 3, 9: 4, 10: 11, 11: 2, 12: 9},
        96: {1: 6, 2: 2, 3: 3, 4: 12, 5: 7, 6: 9, 7: 5, 8: 10, 9: 11, 10: 1, 11: 4, 12: 9},
        97: {1: 1, 2: 9, 3: 10, 4: 6, 5: 12, 6: 2, 7: 7, 8: 5, 9: 3, 10: 4, 11: 8, 12: 11},
        98: {1: 4, 2: 1, 3: 6, 4: 8, 5: 10, 6: 12, 7: 11, 8: 2, 9: 9, 10: 7, 11: 3, 12: 5},
        99: {1: 9, 2: 4, 3: 1, 4: 2, 5: 6, 6: 8, 7: 12, 8: 11, 9: 5, 10: 3, 11: 10, 12: 7},
        100: {1: 3, 2: 10, 3: 8, 4: 1, 5: 5, 6: 7, 7: 6, 8: 12, 9: 2, 10: 9, 11: 11, 12: 4},
        101: {1: 11, 2: 3, 3: 9, 4: 4, 5: 1, 6: 6, 7: 8, 8: 10, 9: 7, 10: 5, 11: 12, 12: 2},
        102: {1: 5, 2: 11, 3: 3, 4: 9, 5: 4, 6: 1, 7: 2, 8: 6, 9: 8, 10: 12, 11: 7, 12: 10},
        103: {1: 7, 2: 5, 3: 11, 4: 3, 5: 9, 6: 4, 7: 1, 8: 8, 9: 12, 10: 10, 11: 2, 12: 6},
        104: {1: 2, 2: 7, 3: 5, 4: 11, 5: 3, 6: 9, 7: 10, 8: 1, 9: 6, 10: 8, 11: 4, 12: 12},
        105: {1: 12, 2: 2, 3: 4, 4: 5, 5: 11, 6: 3, 7: 9, 8: 7, 9: 10, 10: 6, 11: 1, 12: 8},
        106: {1: 10, 2: 12, 3: 2, 4: 7, 5: 8, 6: 5, 7: 3, 8: 9, 9: 4, 10: 11, 11: 6, 12: 1},
        107: {1: 8, 2: 6, 3: 12, 4: 10, 5: 7, 6: 11, 7: 4, 8: 3, 9: 1, 10: 2, 11: 5, 12: 9},
        108: {1: 6, 2: 8, 3: 7, 4: 12, 5: 2, 6: 10, 7: 5, 8: 4, 9: 11, 10: 1, 11: 9, 12: 3},
        109: {1: 1, 2: 9, 3: 10, 4: 6, 5: 12, 6: 2, 7: 7, 8: 11, 9: 5, 10: 3, 11: 4, 12: 8},
        110: {1: 4, 2: 1, 3: 6, 4: 8, 5: 10, 6: 12, 7: 3, 8: 5, 9: 7, 10: 2, 11: 11, 12: 9},
        111: {1: 9, 2: 4, 3: 1, 4: 2, 5: 5, 6: 8, 7: 12, 8: 10, 9: 6, 10: 7, 11: 3, 12: 11},
        112: {1: 3, 2: 10, 3: 8, 4: 9, 5: 11, 6: 7, 7: 4, 8: 1, 9: 2, 10: 12, 11: 6, 12: 5},
        113: {1: 11, 2: 3, 3: 9, 4: 4, 5: 1, 6: 6, 7: 2, 8: 7, 9: 10, 10: 5, 11: 8, 12: 12},
        114: {1: 5, 2: 11, 3: 3, 4: 1, 5: 4, 6: 10, 7: 6, 8: 8, 9: 12, 10: 9, 11: 7, 12: 2},
        115: {1: 7, 2: 5, 3: 11, 4: 3, 5: 9, 6: 4, 7: 1, 8: 12, 9: 8, 10: 10, 11: 2, 12: 6},
        116: {1: 2, 2: 7, 3: 5, 4: 11, 5: 3, 6: 9, 7: 10, 8: 6, 9: 4, 10: 8, 11: 12, 12: 1},
        117: {1: 12, 2: 2, 3: 4, 4: 5, 5: 6, 6: 1, 7: 8, 8: 9, 9: 3, 10: 11, 11: 10, 12: 7},
        118: {1: 10, 2: 12, 3: 2, 4: 7, 5: 8, 6: 11, 7: 9, 8: 3, 9: 1, 10: 6, 11: 5, 12: 4},
        119: {1: 8, 2: 6, 3: 12, 4: 10, 5: 7, 6: 5, 7: 11, 8: 2, 9: 9, 10: 4, 11: 1, 12: 3},
        120: {1: 6, 2: 8, 3: 7, 4: 12, 5: 2, 6: 3, 7: 5, 8: 4, 9: 11, 10: 1, 11: 9, 12: 10}
    }

    def _parse_date_time(self, dob_str: str, tob_str: str) -> dict:
        try:
            # We remove dayfirst=True because dob_str usually comes as YYYY-MM-DD from HTML input.
            parsed_date = dateutil.parser.parse(dob_str)
            parsed_time = dateutil.parser.parse(tob_str)
        except Exception as exc:
            raise ValueError(f"Could not understand the date/time format. Use YYYY-MM-DD and HH:MM. Error: {exc}")

        return {
            "year": parsed_date.year,
            "month": parsed_date.month,
            "day": parsed_date.day,
            "hour": parsed_time.hour,
            "minute": parsed_time.minute,
            "second": parsed_time.second
        }

    def geocode_place(self, place_name: str) -> List[Dict[str, Any]]:
        """Look up lat/lon and UTC offset from a place name string."""
        if not place_name or not place_name.strip():
            return []
            
        geolocator = Nominatim(user_agent="lk_predictor_geocoder", timeout=10)
        tf = TimezoneFinder()

        try:
            results = geolocator.geocode(place_name, exactly_one=False, limit=1)
        except Exception as e:
            logger.warning("Geocoding failed for '%s': %s", place_name, e)
            return []

        if not results:
            return []
            
        loc = results[0]
        tz_name = tf.timezone_at(lat=loc.latitude, lng=loc.longitude)
        if tz_name:
            tz = pytz.timezone(tz_name)
            utc_offset = datetime.now(tz).strftime("%z")
            utc_offset = f"{utc_offset[:3]}:{utc_offset[3:]}"
        else:
            utc_offset = "+00:00"
            tz_name = "UTC"

        return [{
            "display_name": loc.address,
            "latitude": round(loc.latitude, 6),
            "longitude": round(loc.longitude, 6),
            "utc_offset": utc_offset,
            "timezone": tz_name,
        }]

    def generate_chart(self, dob_str: str, tob_str: str, place_name: str, 
                       latitude: float, longitude: float, utc_string: str, 
                       chart_system: str = "kp") -> dict:
        """
        Generate astronomical chart and convert to 'ChartData' Base Contract format.
        """
        if chart_system not in self.CHART_SYSTEMS:
            raise ValueError(f"Unknown chart system '{chart_system}'. Choose from: {self.CHART_SYSTEMS}")

        dt = self._parse_date_time(dob_str, tob_str)
        ayanamsa = "Lahiri" if chart_system == "vedic" else "Krishnamurti"
        house_system = "Whole Sign" if chart_system == "vedic" else "Placidus"

        calculator = VedicHoroscopeData(
            year=dt["year"], month=dt["month"], day=dt["day"],
            hour=dt["hour"], minute=dt["minute"], second=dt["second"],
            utc=utc_string, latitude=latitude, longitude=longitude,
            ayanamsa=ayanamsa, house_system=house_system,
        )

        chart = calculator.generate_chart()
        va_planets_raw = calculator.get_planets_data_from_chart(chart)
        
        # Standard LK planets mapping
        standard_planets = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu", "Asc"]
        planets_in_houses = {}
        
        for p_obj in va_planets_raw:
            planet_name = getattr(p_obj, "Object", "N/A")
            if planet_name in standard_planets:
                # Use the library-computed HouseNr directly
                house = getattr(p_obj, "HouseNr", 1)
                
                # Special constraint: Ascendant MUST be in House 1 for visual grid
                if planet_name == "Asc":
                    house = 1

                planets_in_houses[planet_name] = {
                    "house": house,
                    "house_natal": house,
                }

        birth_datetime_str = f"{dt['year']:04d}-{dt['month']:02d}-{dt['day']:02d}T{dt['hour']:02d}:{dt['minute']:02d}:{dt['second']:02d}"

        # Build ChartData dict contract
        return {
            "chart_type": "Birth",
            "chart_period": 0,
            "birth_time": birth_datetime_str,
            "planets_in_houses": planets_in_houses
        }

    def generate_annual_charts(self, natal_chart: dict, max_years: int = 75) -> Dict[str, dict]:
        """
        Iterate over max_years and construct Varshaphal charts from the natal chart
        according to the 120-year mapping matrix.
        """
        annual_charts = {}
        birth_datetime_str = natal_chart.get("birth_time", "")
        
        try:
            birth_datetime = datetime.fromisoformat(birth_datetime_str.replace('Z', '+00:00')) if birth_datetime_str else None
        except ValueError:
            birth_datetime = None

        for age in range(1, max_years + 1):
            # In the 120-year matrix, the key matches the Age (e.g. Age 45 uses index 45)
            # as validated against the 'Moon Returns to H2 at Age 45' and 'Mercury in H1' reality check.
            year_key = age
            mapping = self.YEAR_MATRIX.get(year_key, {})
            
            annual = natal_chart.copy()
            annual["chart_type"] = "Yearly"
            annual["chart_period"] = age
            
            # Deep copy planets to apply new house placements without clobbering Natal
            annual_planets = {}
            for p, p_data in natal_chart.get("planets_in_houses", {}).items():
                p_copy = p_data.copy()
                
                # Rule: Ascendant ALWAYS stays in House 1 in Lal Kitab Varshphal
                if p == "Asc":
                    p_copy["house"] = 1
                else:
                    natal_h = p_copy.get("house_natal", p_copy.get("house", 0))
                    # Map Natal House -> Annual House using the 120-year matrix
                    if natal_h in mapping:
                        p_copy["house"] = int(mapping[natal_h])
                    
                    # Update States for Annual Chart (Exalted, Debilitated, Fixed House Lord)
                    p_copy["states"] = self._detect_planet_states(p, p_copy["house"])

                annual_planets[p] = p_copy
                
            annual["planets_in_houses"] = annual_planets
            
            if birth_datetime:
                # Precise birthday tracking using relativedelta
                period_start = birth_datetime + relativedelta(years=age)
                period_end = birth_datetime + relativedelta(years=age + 1)
                
                annual["period_start"] = period_start.date().isoformat()
                annual["period_end"] = (period_end - timedelta(days=1)).date().isoformat()
                annual["birth_time"] = period_start.isoformat()
            
            annual_charts[f"chart_{age}"] = annual
            
        return annual_charts

    def _detect_planet_states(self, planet: str, house: int) -> List[str]:
        """
        Detects Lal Kitab planetary states (Exalted, Debilitated, Fixed House Lord) 
        based on the current house placement.
        """
        states = []
        # Exaltation
        if planet in PLANET_EXALTATION and house in PLANET_EXALTATION[planet]:
            states.append("Exalted")
        
        # Debilitation
        if planet in PLANET_DEBILITATION and house in PLANET_DEBILITATION[planet]:
            states.append("Debilitated")
            
        # Fixed House Lord (Pakka Ghar)
        if house in FIXED_HOUSE_LORDS and planet in FIXED_HOUSE_LORDS[house]:
            states.append("Fixed House Lord")
            
        return states

    def build_full_chart_payload(self, dob_str: str, tob_str: str, place_name: str,
                                 latitude: float = 0.0, longitude: float = 0.0,
                                 utc_string: str = "+05:30", chart_system: str = "kp",
                                 annual_basis: str = "vedic") -> Dict[str, dict]:
        """
        Wraps geocoding iff lat/lon are not provided, generates Natal, and all 75 Annual charts.
        
        Dual-basis Logic:
        If annual_basis='vedic', we use the Vedic-Whole-Sign chart as the seed for all Varshphal mappings,
        ensuring parity with legacy reference systems, while keeping the primary Natal chart in the user's
        chosen system (e.g., KP).
        """
        if latitude is None or longitude is None or (latitude == 0.0 and longitude == 0.0):
            locations = self.geocode_place(place_name)
            if not locations:
                raise ValueError(f"Could not geocode {place_name} and lat/lon were not provided.")
            loc = locations[0]
            latitude = loc["latitude"]
            longitude = loc["longitude"]
            utc_string = loc["utc_offset"]
            
        natal_chart = self.generate_chart(dob_str, tob_str, place_name, latitude, longitude, utc_string, chart_system)
        
        # Determine the seed for annual charts
        if annual_basis == "vedic" and chart_system != "vedic":
            # Generate a hidden Vedic chart to use as the seed for annual mapping
            seed_chart = self.generate_chart(dob_str, tob_str, place_name, latitude, longitude, utc_string, "vedic")
        else:
            seed_chart = natal_chart
            
        annual_charts = self.generate_annual_charts(seed_chart)
        
        payload = {"chart_0": natal_chart}
        # In the payload, we might want to store which system was used for annuals
        payload["metadata"] = {
            "chart_system": chart_system,
            "annual_basis": annual_basis
        }
        payload.update(annual_charts)
        
        return payload
