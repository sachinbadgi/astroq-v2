import unittest
from astroq.lk_prediction.astrological_context import UnifiedAstrologicalContext
from astroq.lk_prediction.data_contracts import ChartData, EnrichedChart

def _make_enriched(chart: ChartData) -> EnrichedChart:
    return EnrichedChart(source=chart)

class TestAstrologicalContext(unittest.TestCase):
    def setUp(self):
        self.natal_chart: ChartData = {
            "chart_type": "Birth",
            "planets_in_houses": {
                "Jupiter": {"house": 1},
                "Sun": {"house": 1},
                "Saturn": {"house": 10}
            },
            "house_status": {"1": "Occupied", "10": "Occupied"}
        }
        self.annual_chart: ChartData = {
            "chart_type": "Yearly",
            "chart_period": 30,
            "planets_in_houses": {
                "Jupiter": {"house": 4},
                "Masnui Venus": {"house": 2}
            },
            "house_status": {"4": "Occupied", "2": "Occupied"}
        }

    def test_planet_resolution(self):
        context = UnifiedAstrologicalContext(_make_enriched(self.annual_chart), self.natal_chart)
        self.assertEqual(context.resolve_base_planet("Masnui Venus"), "Venus")
        self.assertEqual(context.resolve_base_planet("Jupiter"), "Jupiter")

    def test_house_lookups(self):
        context = UnifiedAstrologicalContext(_make_enriched(self.annual_chart), self.natal_chart)
        self.assertEqual(context.get_house("Jupiter"), 4)
        self.assertEqual(context.get_house("Masnui Venus"), 2)
        self.assertEqual(context.get_natal_house("Jupiter"), 1)
        self.assertEqual(context.get_natal_house("Masnui Venus"), None) # Venus not in natal

    def test_dignity_multipliers(self):
        context = UnifiedAstrologicalContext(_make_enriched(self.annual_chart), self.natal_chart)
        mult = context.get_dignity_multiplier("Jupiter")
        self.assertIsInstance(mult, float)
        self.assertTrue(0.5 <= mult <= 1.5)

    def test_cycle_ruler(self):
        context = UnifiedAstrologicalContext(_make_enriched(self.annual_chart), self.natal_chart)
        mult = context.get_cycle_ruler_multiplier(["Jupiter"])
        self.assertIsInstance(mult, float)

if __name__ == "__main__":
    unittest.main()
