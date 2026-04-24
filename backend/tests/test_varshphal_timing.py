import unittest
from astroq.lk_prediction.varshphal_timing_engine import VarshphalTimingEngine

class TestVarshphalTimingEngine(unittest.TestCase):
    def setUp(self):
        self.engine = VarshphalTimingEngine()
        
        self.natal_chart = {
            "planets_in_houses": {
                "Venus": {"house": 7},
                "Saturn": {"house": 6},
                "Mercury": {"house": 2},
                "Sun": {"house": 5},
                "Moon": {"house": 5}
            }
        }
        
        self.annual_chart = {
            "planets_in_houses": {
                "Venus": {"house": 7},
                "Saturn": {"house": 10},
                "Mercury": {"house": 12},
                "Jupiter": {"house": 9},
                "Moon": {"house": 9}
            }
        }

    def test_age_gates(self):
        # Saturn in H6 -> Prohibit marriage before 28
        is_prohibited, reason = self.engine.check_age_gates(self.natal_chart, 25, "marriage")
        self.assertTrue(is_prohibited)
        self.assertIn("before age 28", reason)
        
        is_prohibited, reason = self.engine.check_age_gates(self.natal_chart, 29, "marriage")
        self.assertFalse(is_prohibited)

    def test_varshphal_triggers_marriage(self):
        # Natal Venus in 7, Annual Venus in 7 should trigger marriage rule
        triggers = self.engine.evaluate_varshphal_triggers(self.natal_chart, self.annual_chart, "marriage")
        # Triggers: 
        # - Venus/Mer returns to Natal House, No enemies in 2,7 (Annual enemies are Sun/Moon/Rahu. Here Moon is 9. None in 2,7)
        # - Natal Ven/Mer in 7 returns to 7
        # - Ven or Mer in 1,2,10,11,12 AND Sat in 1 or 10. (Annual Sat is 10, Mer is 12).
        # - Annual Venus or Mer in 2 or 7 (Ven is 7)
        self.assertGreaterEqual(len(triggers), 1)
        
    def test_varshphal_triggers_finance(self):
        natal = {
            "planets_in_houses": {
                "Saturn": {"house": 6}
            }
        }
        annual = {
            "planets_in_houses": {
                "Mars": {"house": 4}
            }
        }
        triggers = self.engine.evaluate_varshphal_triggers(natal, annual, "finance")
        self.assertEqual(len(triggers), 1)
        self.assertIn("Saturn 6 in Natal AND Mars 1-8 in Annual", triggers[0]["desc"])

    def test_special_destruction(self):
        natal = {"planets_in_houses": {"Jupiter": {"house": 8}}}
        annual = {"planets_in_houses": {"Jupiter": {"house": 7}}}
        warnings = self.engine.evaluate_special_destruction(natal, annual)
        self.assertEqual(len(warnings), 1)
        self.assertIn("Jupiter moved from Natal H8 to Annual H7", warnings[0])

if __name__ == "__main__":
    unittest.main()
