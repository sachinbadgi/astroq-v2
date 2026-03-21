"""
Shared test fixtures for the LK Prediction Model v2 test suite.

Provides sample charts, config factories, and helper utilities
used across all test modules.
"""

import os
import json
import tempfile
import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.abspath(os.path.join(_THIS_DIR, os.pardir, os.pardir))
_DATA_DIR = os.path.join(_BACKEND_DIR, "data")
MODEL_DEFAULTS_PATH = os.path.join(_DATA_DIR, "model_defaults.json")


# ---------------------------------------------------------------------------
# Sample Charts
# ---------------------------------------------------------------------------

def _make_planet(house, states=None, aspects=None, strength_total=0.0,
                 sleeping_status="", dharmi_status=""):
    """Helper to build a PlanetInHouse dict."""
    return {
        "house": house,
        "states": states or [],
        "aspects": aspects or [],
        "strength_total": strength_total,
        "sleeping_status": sleeping_status,
        "dharmi_status": dharmi_status,
    }


SAMPLE_NATAL_CHART = {
    "chart_type": "Birth",
    "chart_period": 0,
    "planets_in_houses": {
        "Sun":     _make_planet(1, states=["Exalted"]),
        "Moon":    _make_planet(4, states=["Fixed House Lord"]),
        "Mars":    _make_planet(3, states=["Fixed House Lord"]),
        "Mercury": _make_planet(7),
        "Jupiter": _make_planet(2, states=["Fixed House Lord"]),
        "Venus":   _make_planet(7),
        "Saturn":  _make_planet(10, states=["Fixed House Lord"]),
        "Rahu":    _make_planet(12),
        "Ketu":    _make_planet(6),
    },
    "mangal_badh_counter": 0,
    "mangal_badh_status": "",
    "dharmi_kundli_status": "Not Dharmi Teva",
    "house_status": {
        "1": "Occupied", "2": "Occupied", "3": "Occupied",
        "4": "Occupied", "5": "Sleeping House", "6": "Occupied",
        "7": "Occupied", "8": "Sleeping House", "9": "Sleeping House",
        "10": "Occupied", "11": "Sleeping House", "12": "Occupied",
    },
    "masnui_grahas_formed": [],
    "lal_kitab_debts": [],
    "achanak_chot_triggers": [],
    "dhoka_graha_analysis": [],
    "varshaphal_metadata": {},
}


SAMPLE_ANNUAL_CHART = {
    "chart_type": "Yearly",
    "chart_period": 25,
    "planets_in_houses": {
        "Sun":     _make_planet(10),
        "Moon":    _make_planet(2),
        "Mars":    _make_planet(1),
        "Mercury": _make_planet(10),
        "Jupiter": _make_planet(4, states=["Exalted"]),
        "Venus":   _make_planet(12, states=["Exalted"]),
        "Saturn":  _make_planet(7, states=["Exalted"]),
        "Rahu":    _make_planet(6),
        "Ketu":    _make_planet(12),
    },
    "mangal_badh_counter": 1,
    "mangal_badh_status": "Active",
    "dharmi_kundli_status": "Not Dharmi Teva",
    "house_status": {
        "1": "Occupied", "2": "Occupied", "3": "Sleeping House",
        "4": "Occupied", "5": "Sleeping House", "6": "Occupied",
        "7": "Occupied", "8": "Sleeping House", "9": "Sleeping House",
        "10": "Occupied", "11": "Sleeping House", "12": "Occupied",
    },
    "masnui_grahas_formed": [],
    "lal_kitab_debts": [],
    "achanak_chot_triggers": [],
    "dhoka_graha_analysis": [],
    "varshaphal_metadata": {
        "year_lord": "Saturn",
        "muntha_house": 2,
        "age": 25,
    },
}


# ---------------------------------------------------------------------------
# Config Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def defaults_path():
    """Path to the real model_defaults.json."""
    return MODEL_DEFAULTS_PATH


@pytest.fixture
def tmp_db(tmp_path):
    """Create a temporary SQLite DB path for config tests."""
    return str(tmp_path / "test_config.db")


@pytest.fixture
def tmp_defaults(tmp_path):
    """Create a temporary defaults JSON with known values."""
    data = {
        "strength.natal.pakka_ghar": 2.20,
        "strength.natal.exalted": 5.00,
        "strength.natal.debilitated": -5.00,
        "strength.natal.fixed_house_lord": 1.50,
        "strength.annual_dignity_factor": 0.50,
        "probability.sigmoid.k_base": 0.45,
        "probability.sigmoid.k_min": 0.15,
        "classifier.threshold_absolute": 0.70,
    }
    path = str(tmp_path / "test_defaults.json")
    with open(path, "w") as f:
        json.dump(data, f)
    return path


@pytest.fixture
def sample_natal_chart():
    """Return a copy of the sample natal chart."""
    import copy
    return copy.deepcopy(SAMPLE_NATAL_CHART)


@pytest.fixture
def sample_annual_chart():
    """Return a copy of the sample annual chart."""
    import copy
    return copy.deepcopy(SAMPLE_ANNUAL_CHART)
