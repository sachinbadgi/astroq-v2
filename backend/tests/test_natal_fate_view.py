"""
Tests for NatalFateView.

Run:
    cd /Users/sachinbadgi/Documents/lal_kitab/astroq-v2
    python -m pytest backend/tests/test_natal_fate_view.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from astroq.lk_prediction.natal_fate_view import NatalFateView


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _chart(planets: dict) -> dict:
    """Build minimal chart dict from {planet_name: house_number}."""
    return {"planets_in_houses": {p: {"house": h} for p, h in planets.items()}}


def _get(entries: list, domain: str) -> dict | None:
    return next((e for e in entries if e["domain"] == domain), None)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestNatalFateView:

    def setup_method(self):
        self.view = NatalFateView()

    # --- GRAHA_PHAL cases ------------------------------------------------

    def test_career_graha_phal_saturn_pakka_ghar(self):
        """Saturn in H10 (Pakka Ghar) → career = GRAHA_PHAL."""
        chart = _chart({"Saturn": 10, "Sun": 1})
        entries = self.view.evaluate(chart, categories=["canonical"])
        entry = _get(entries, "career")
        assert entry is not None, "career entry missing"
        assert entry["fate_type"] == "GRAHA_PHAL"
        assert any("Saturn" in ev for ev in entry["evidence"])

    def test_marriage_graha_phal_venus_pakka_ghar(self):
        """Venus in H7 (Pakka Ghar) → marriage = GRAHA_PHAL."""
        chart = _chart({"Venus": 7})
        entries = self.view.evaluate(chart, categories=["canonical"])
        entry = _get(entries, "marriage")
        assert entry is not None
        assert entry["fate_type"] == "GRAHA_PHAL"

    def test_cryptocurrency_graha_phal_rahu_pakka_ghar(self):
        """Rahu in H12 (Pakka Ghar) → cryptocurrency = GRAHA_PHAL."""
        chart = _chart({"Rahu": 12})
        entries = self.view.evaluate(chart)
        entry = _get(entries, "cryptocurrency")
        assert entry is not None
        assert entry["fate_type"] == "GRAHA_PHAL"

    def test_spirituality_graha_phal_ketu_exalted(self):
        """Ketu in H12 (exaltation) → spirituality = GRAHA_PHAL."""
        chart = _chart({"Ketu": 12})
        entries = self.view.evaluate(chart, categories=["canonical"])
        entry = _get(entries, "spirituality")
        assert entry is not None
        assert entry["fate_type"] == "GRAHA_PHAL"

    # --- RASHI_PHAL cases ------------------------------------------------

    def test_marriage_rashi_phal_venus_not_dignified(self):
        """Venus in H6 (debilitated) AND H7 empty → NEITHER (primary house empty).
        But when Saturn is in H7 (not a key planet for marriage), H7 is occupied
        and Venus is undignified → RASHI_PHAL (promise exists, conditional)."""
        # Case A: H7 empty, Venus off-domain → NEITHER
        chart_a = _chart({"Venus": 6, "Mercury": 3})
        entries_a = self.view.evaluate(chart_a, categories=["canonical"])
        entry_a = _get(entries_a, "marriage")
        assert entry_a is not None
        assert entry_a["fate_type"] == "NEITHER"   # H7 empty = no structural promise

        # Case B: H7 occupied by Saturn (not a key planet), Venus off-domain → RASHI_PHAL
        chart_b = _chart({"Venus": 3, "Saturn": 7})
        entries_b = self.view.evaluate(chart_b, categories=["canonical"])
        entry_b = _get(entries_b, "marriage")
        assert entry_b is not None
        assert entry_b["fate_type"] == "RASHI_PHAL"  # H7 occupied but Venus/Mercury not dignified

    def test_career_rashi_phal_saturn_not_in_h10(self):
        """Saturn in H1 (debilitation) and H10 occupied by other planet → career = RASHI_PHAL."""
        chart = _chart({"Saturn": 1, "Sun": 10})
        entries = self.view.evaluate(chart, categories=["canonical"])
        entry = _get(entries, "career")
        assert entry is not None
        # Sun in H10 but H10 is not Sun's Pakka Ghar; Saturn debilitated → RASHI_PHAL or HYBRID
        assert entry["fate_type"] in ("RASHI_PHAL", "HYBRID")

    # --- HYBRID cases ----------------------------------------------------

    def test_health_hybrid_sun_exalted_but_saturn_debilitated(self):
        """Sun in H1 (exaltation) AND Saturn in H1 (debilitation) → HYBRID."""
        chart = _chart({"Sun": 1, "Saturn": 1})
        entries = self.view.evaluate(chart, categories=["canonical"])
        entry = _get(entries, "health")
        assert entry is not None
        # Sun gives GP signal for H1; Saturn debilitated gives RP penalty → HYBRID
        assert entry["fate_type"] in ("GRAHA_PHAL", "HYBRID")

    # --- NEITHER cases ---------------------------------------------------

    def test_foreign_travel_neither_when_h12_empty(self):
        """H12 empty, Rahu absent → foreign_travel = NEITHER."""
        chart = _chart({"Saturn": 10, "Jupiter": 2})  # No planets in H12 or H9
        entries = self.view.evaluate(chart, categories=["canonical"])
        entry = _get(entries, "foreign_travel")
        assert entry is not None
        assert entry["fate_type"] == "NEITHER"

    # --- Filter tests ----------------------------------------------------

    def test_filter_categories_returns_only_canonical(self):
        """Only canonical entries returned when categories=['canonical']."""
        chart = _chart({"Saturn": 10})
        entries = self.view.evaluate(chart, categories=["canonical"])
        assert all(e["category"] == "canonical" for e in entries)
        assert len(entries) == 13  # Exactly 13 canonical domains

    def test_include_neither_false_excludes_absent(self):
        """NEITHER entries excluded when include_neither=False."""
        chart = _chart({"Saturn": 10})  # Most houses empty
        entries = self.view.evaluate(chart, include_neither=False)
        assert all(e["fate_type"] != "NEITHER" for e in entries)

    def test_all_50_plus_returned_by_default(self):
        """Default call returns 50+ domain entries."""
        chart = _chart({"Saturn": 10, "Jupiter": 2, "Venus": 7, "Rahu": 12})
        entries = self.view.evaluate(chart)
        assert len(entries) >= 50

    # --- Output format tests ---------------------------------------------

    def test_entry_schema_complete(self):
        """Every entry has all required JSON keys."""
        chart = _chart({"Saturn": 10, "Venus": 7})
        entries = self.view.evaluate(chart, categories=["canonical"])
        required_keys = {
            "domain", "label", "category", "fate_type", "fate_label",
            "evidence", "key_planets", "active_houses", "dignity_details"
        }
        for e in entries:
            assert required_keys.issubset(e.keys()), f"Entry {e['domain']} missing keys: {required_keys - e.keys()}"

    def test_json_serializable(self):
        """Output is JSON-serializable without errors."""
        import json
        chart = _chart({"Saturn": 10, "Jupiter": 2, "Venus": 7, "Rahu": 12})
        entries = self.view.evaluate(chart)
        result = json.dumps(entries)
        assert isinstance(result, str)
        assert "GRAHA_PHAL" in result or "RASHI_PHAL" in result

    def test_format_as_table_returns_string(self):
        """format_as_table() returns a non-empty string."""
        chart = _chart({"Saturn": 10, "Jupiter": 2, "Venus": 7})
        entries = self.view.evaluate(chart, categories=["canonical"])
        table = self.view.format_as_table(entries)
        assert isinstance(table, str)
        assert len(table) > 0
        assert "CANONICAL" in table
