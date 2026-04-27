import unittest
import sys
import os

# Ensure backend is importable
_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.normpath(os.path.join(_HERE, ".."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from astroq.lk_prediction.dormancy_engine import DormancyEngine

class TestDormancyEngine(unittest.TestCase):
    def setUp(self):
        self.engine = DormancyEngine()

    def test_lamp_absolute_awakening(self):
        """Planets in H1, H7, H9 must be AWAKE regardless of aspects/forward houses."""
        ppos = {"Saturn": 1} # H1 is a Lamp house
        # In a blank chart, Saturn would normally be dormant if no aspects/forward planets
        is_awake = self.engine.is_awake("Saturn", 1, ppos)
        self.assertTrue(is_awake, "Planet in H1 (Lamp) should be absolutely awake.")

    def test_munsif_rule_h7_suppression(self):
        """Munsif Rule: H7 is dormant if H1 is blank, even if it's a Lamp house."""
        ppos = {"Venus": 7} # H1 is empty
        is_awake = self.engine.is_awake("Venus", 7, ppos)
        self.assertFalse(is_awake, "Planet in H7 should be suppressed by blank H1 (Munsif Rule).")

    def test_h2_sustenance_factor_blank(self):
        """Blank H2 should yield a sustenance factor of 0.6 (Leakage)."""
        ppos = {"Sun": 1} # H2 is empty
        factor = self.engine.get_sustenance_factor("Sun", 1, ppos)
        self.assertEqual(factor, 0.6)

    def test_h2_sustenance_factor_friend(self):
        """H2 occupied by a friend should yield 1.2."""
        # For Sun in H1, Jupiter (Friend) in H2
        ppos = {"Sun": 1, "Jupiter": 2}
        factor = self.engine.get_sustenance_factor("Sun", 1, ppos)
        self.assertEqual(factor, 1.2)

    def test_h2_sustenance_factor_enemy(self):
        """H2 occupied by an enemy should yield 0.4."""
        # For Sun in H1, Venus (Enemy) in H2
        ppos = {"Sun": 1, "Venus": 2}
        factor = self.engine.get_sustenance_factor("Sun", 1, ppos)
        self.assertEqual(factor, 0.4)

if __name__ == "__main__":
    unittest.main()
