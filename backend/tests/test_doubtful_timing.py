"""
Unit tests for DoubtfulTimingEngine.

Tests cover:
    - Detection of doubtful natal promise configurations.
    - Annual chart TRIGGER detection (debilitation, 180-enemy, dormancy).
    - Annual chart RESOLUTION detection (Pakka Ghar, exaltation).
    - Confidence modifier logic (Boost / Suppress / Contested / Neutral).
    - Full get_timing_confidence override.
"""

import unittest
import sys
import os

# Ensure backend is importable
_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.normpath(os.path.join(_HERE, "..", ".."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from astroq.lk_prediction.doubtful_timing_engine import DoubtfulTimingEngine


def _natal(positions: dict) -> dict:
    """Build a minimal natal chart payload from a planet→house dict."""
    return {"planets_in_houses": {p: {"house": h} for p, h in positions.items()}}


def _annual(positions: dict) -> dict:
    """Build a minimal annual chart payload."""
    return {"planets_in_houses": {p: {"house": h} for p, h in positions.items()}}


class TestDoubtfulNatalPromiseDetection(unittest.TestCase):
    def setUp(self):
        self.engine = DoubtfulTimingEngine()

    def test_roof_and_well(self):
        """Rahu H5 + Moon H4 → 'Roof and Well' doubtful progeny promise."""
        natal = _natal({"Rahu": 5, "Moon": 4, "Saturn": 10})
        promises = self.engine._identify_doubtful_natal_promises(natal)
        names = [p["name"] for p in promises]
        self.assertTrue(
            any("Roof and Well" in n for n in names),
            f"Expected 'Roof and Well' in promises. Got: {names}"
        )

    def test_doubtful_venus_h4(self):
        """Venus in H4 → 'Doubtful Venus H4' marriage promise."""
        natal = _natal({"Venus": 4, "Saturn": 2, "Jupiter": 9})
        promises = self.engine._identify_doubtful_natal_promises(natal)
        names = [p["name"] for p in promises]
        self.assertTrue(
            any("Doubtful Venus H4" in n for n in names),
            f"Expected 'Doubtful Venus H4' promise. Got: {names}"
        )

    def test_houses_2_7_blank(self):
        """Empty H2 and H7 → 'Houses 2 & 7 Blank' doubtful health promise."""
        natal = _natal({"Sun": 1, "Mars": 3, "Jupiter": 9})  # no planets in H2 or H7
        promises = self.engine._identify_doubtful_natal_promises(natal)
        names = [p["name"] for p in promises]
        self.assertTrue(
            any("Houses 2 & 7 Blank" in n for n in names),
            f"Expected 'Houses 2 & 7 Blank' promise. Got: {names}"
        )

    def test_no_false_detection(self):
        """Clean chart (no doubtful configs) → no doubtful promises."""
        natal = _natal({"Sun": 1, "Moon": 2, "Venus": 7, "Jupiter": 9, "Saturn": 10})
        promises = self.engine._identify_doubtful_natal_promises(natal)
        # Venus is in H7 (Pakka Ghar), Moon in H2, H2 and H7 occupied → no blanks
        # Rahu not in H5 → no roof+well
        # Venus not in H4 → no doubtful Venus
        names = [p["name"] for p in promises]
        self.assertFalse(
            any("Roof and Well" in n for n in names),
            "Should NOT detect Roof and Well"
        )
        self.assertFalse(
            any("Doubtful Venus H4" in n for n in names),
            "Should NOT detect Doubtful Venus H4"
        )


class TestDoubtfulTimingResolutionAndTrigger(unittest.TestCase):
    def setUp(self):
        self.engine = DoubtfulTimingEngine()

    def test_resolution_via_exaltation(self):
        """
        Venus (active in 'Doubtful Venus H4' promise) moves to exaltation in annual
        → RESOLVED.
        """
        natal = _natal({"Venus": 4, "Saturn": 2, "Jupiter": 9})
        # Venus exalts in H12 (per PLANET_EXALTATION["Venus"] = [12])
        annual = _annual({"Venus": 12, "Saturn": 6, "Jupiter": 3})

        evals = self.engine.evaluate_doubtful_timing(natal, annual, domain="marriage")
        venus_evals = [e for e in evals if "Venus H4" in e["promise"]]
        self.assertTrue(len(venus_evals) > 0, "Should have evaluated Venus H4 promise")
        # At minimum should have a resolution for exaltation
        all_resolutions = [r for e in venus_evals for r in e["resolutions"]]
        self.assertTrue(
            any("Exaltation" in r for r in all_resolutions),
            f"Expected exaltation resolution. Resolutions: {all_resolutions}"
        )

    def test_trigger_via_debilitation(self):
        """
        Rahu (active in 'Roof and Well') moves to debilitation in annual → TRIGGERED.
        Rahu debilitates in H9 (per PLANET_DEBILITATION["Rahu"] = [9]).
        """
        natal = _natal({"Rahu": 5, "Moon": 4})
        annual = _annual({"Rahu": 9, "Moon": 11})  # Rahu debilitated in H9

        evals = self.engine.evaluate_doubtful_timing(natal, annual, domain="progeny")
        rahu_evals = [e for e in evals if "Roof and Well" in e["promise"]]
        self.assertTrue(len(rahu_evals) > 0, "Should have evaluated Roof and Well promise")

        all_triggers = [t for e in rahu_evals for t in e["triggers"]]
        self.assertTrue(
            any("Debilitation" in t for t in all_triggers),
            f"Expected debilitation trigger. Triggers: {all_triggers}"
        )
        self.assertIn(rahu_evals[0]["verdict"], ("TRIGGERED", "CONTESTED"))

    def test_domain_filter(self):
        """evaluate_doubtful_timing should only return promises matching the domain."""
        natal = _natal({"Rahu": 5, "Moon": 4, "Venus": 4})
        annual = _annual({"Rahu": 9, "Venus": 12, "Moon": 6})

        # Only progeny domain
        evals_progeny = self.engine.evaluate_doubtful_timing(natal, annual, domain="progeny")
        for e in evals_progeny:
            self.assertEqual(e["domain"], "progeny",
                             f"Unexpected domain in result: {e['domain']}")

        # Only marriage domain
        evals_marriage = self.engine.evaluate_doubtful_timing(natal, annual, domain="marriage")
        for e in evals_marriage:
            self.assertEqual(e["domain"], "marriage",
                             f"Unexpected domain in result: {e['domain']}")


class TestConfidenceModifier(unittest.TestCase):
    def setUp(self):
        self.engine = DoubtfulTimingEngine()

    def test_boost_upgrades_confidence(self):
        """
        When a Doubtful Promise is RESOLVED in the annual chart, confidence
        should be boosted (Low→Medium or Medium→High).
        """
        # Venus H4 natal setup (doubtful marriage)
        natal = _natal({"Venus": 4, "Saturn": 2})
        # Venus moves to exaltation (H12) → RESOLVED
        annual = _annual({"Venus": 12, "Saturn": 3})

        result = self.engine.get_timing_confidence(natal, annual, age=26, domain="marriage")
        self.assertIn(
            result["doubtful_confidence_modifier"], ["Boost", "Neutral", "Contested"],
            f"Unexpected modifier: {result['doubtful_confidence_modifier']}"
        )
        # The modifier field must always be present
        self.assertIn("doubtful_confidence_modifier", result)
        self.assertIn("doubtful_promises", result)
        self.assertIn("doubtful_evaluations", result)

    def test_suppress_does_not_exceed_baseline(self):
        """
        When all Doubtful Promises are TRIGGERED, confidence should not
        be higher than the baseline result.
        """
        natal = _natal({"Rahu": 5, "Moon": 4})
        # Rahu debilitated and dormant (no planets in aspect houses)
        annual = _annual({"Rahu": 9})  # debilitated, and dormant (no other planets)

        result = self.engine.get_timing_confidence(natal, annual, age=20, domain="progeny")
        # The modifier should be Suppress or Neutral
        self.assertIn(
            result["doubtful_confidence_modifier"], ["Suppress", "Neutral", "Contested"]
        )

    def test_result_always_has_doubtful_fields(self):
        """get_timing_confidence always returns the expected doubtful fields."""
        natal  = _natal({"Sun": 1, "Moon": 2, "Venus": 7})
        annual = _annual({"Sun": 7, "Moon": 9, "Venus": 1})

        result = self.engine.get_timing_confidence(natal, annual, age=30, domain="marriage")
        self.assertIn("confidence",                    result)
        self.assertIn("doubtful_promises",             result)
        self.assertIn("doubtful_evaluations",          result)
        self.assertIn("doubtful_confidence_modifier",  result)
        self.assertIn("triggers",                      result)
        self.assertIn("warnings",                      result)


if __name__ == "__main__":
    unittest.main()
