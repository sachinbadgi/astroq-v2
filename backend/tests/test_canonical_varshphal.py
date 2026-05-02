import unittest
from astroq.lk_prediction.rashi_phal_evaluator import RashiPhalEvaluator

class TestCanonicalVarshphal(unittest.TestCase):
    def setUp(self):
        self.evaluator = RashiPhalEvaluator()

    def test_munsif_rule_suppression(self):
        """
        Munsif Rule: If House 1 is blank in the Annual Chart, 
        planets in House 7 remain dormant for that year, 
        EVEN IF aspected by other houses (e.g., House 11).
        """
        # Setup: Natal Venus in H4 makes it a "Doubtful" promise
        natal_chart = {
            "planets_in_houses": {
                "Venus": {"house": 4}
            }
        }
        
        # Setup: Annual Chart where House 1 is empty.
        # House 11 has Mercury which aspects House 7 (Foundation aspect).
        # House 7 has Venus.
        annual_chart = {
            "planets_in_houses": {
                "Venus": {"house": 7},
                "Mercury": {"house": 11}
            }
        }
        
        results = self.evaluator.evaluate(natal_chart, annual_chart)
        
        # Identify if Venus triggered any events
        venus_events = [e for e in results if e.get('triggering_planet') == "Venus"]
        
        # ASSERT: Under the Munsif rule, Venus should produce NO results if House 1 is blank.
        # This SHOULD fail currently because Munsif is not implemented.
        self.assertEqual(len(venus_events), 0, f"Munsif Rule Violation: Venus triggered {len(venus_events)} events despite blank House 1.")

    def test_munsif_rule_activation(self):
        """
        Munsif Rule: If House 1 is active, House 7 planets should activate.
        """
        # Setup: Natal Venus in H4 makes it a "Doubtful" promise
        natal_chart = {
            "planets_in_houses": {
                "Venus": {"house": 4}
            }
        }
        
        # Setup: Annual Chart where House 1 is ACTIVE (has Sun) and House 7 has Venus
        annual_chart = {
            "planets_in_houses": {
                "Sun": {"house": 1},
                "Venus": {"house": 7}
            }
        }
        
        results = self.evaluator.evaluate(natal_chart, annual_chart)
        
        # Identify if Venus triggered any events
        venus_events = [e for e in results if e.get('triggering_planet') == "Venus"]
        
        # ASSERT: Venus should now be active
        self.assertGreater(len(venus_events), 0, "Munsif Rule Violation: Venus failed to activate despite active House 1.")

    def test_lamp_principle_force_activation(self):
        """
        Lamp Principle: Arrival in an active annual house (like H1) 
        "lights the lamp" even if otherwise dormant.
        """
        # Setup: Natal Venus in H4 (Doubtful)
        natal_chart = {
            "planets_in_houses": {
                "Venus": {"house": 4}
            }
        }
        
        # Setup: Annual Chart where Venus is in H1, and NO other planets exist.
        # Standard dormancy rules would say Venus is dormant (no aspects, no fwd).
        # Lamp Principle says H1 is force-activated.
        annual_chart = {
            "planets_in_houses": {
                "Venus": {"house": 1}
            }
        }
        
        results = self.evaluator.evaluate(natal_chart, annual_chart)
        
        # Identify if Venus triggered any events
        venus_events = [e for e in results if e.get('triggering_planet') == "Venus"]
        
        # ASSERT: Venus should be active due to H1 force-activation
        self.assertGreater(len(venus_events), 0, "Lamp Principle Violation: Venus in H1 failed to force-activate.")

if __name__ == "__main__":
    unittest.main()
