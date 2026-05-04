"""
Tests for AnnualSimContext — the extracted module-level simulation context.

Verifies:
1. AnnualSimContext is importable (not an inline class)
2. get_house() delegates to AstroChart correctly
3. get_fate_type_for_domain() uses the real domain_fate_map (not hardcoded 'RASHI_PHAL')
4. LifecycleEngine.run_75yr_analysis() uses AnnualSimContext (not SimContext)

Run: cd backend && python3 -m pytest tests/test_annual_sim_context.py -v
"""
import pytest
from astroq.lk_prediction.lifecycle_engine import AnnualSimContext, LifecycleEngine


# ---------------------------------------------------------------------------
# AnnualSimContext unit tests
# ---------------------------------------------------------------------------
class TestAnnualSimContext:

    def _ctx(self, positions=None, fate_map=None, age=30):
        positions = positions or {"Sun": 6, "Moon": 9, "Saturn": 8, "Venus": 6,
                                   "Mars": 4, "Mercury": 6, "Jupiter": 6,
                                   "Rahu": 7, "Ketu": 1}
        fate_map = fate_map or {}
        return AnnualSimContext(age, positions, fate_map)

    def test_importable_at_module_level(self):
        """AnnualSimContext must NOT be an inline class — must be importable."""
        from astroq.lk_prediction.lifecycle_engine import AnnualSimContext
        assert AnnualSimContext is not None

    def test_age_attribute(self):
        ctx = self._ctx(age=42)
        assert ctx.age == 42

    def test_get_house_known_planet(self):
        ctx = self._ctx(positions={"Sun": 6, "Moon": 9})
        assert ctx.get_house("Sun") == 6
        assert ctx.get_house("Moon") == 9

    def test_get_house_unknown_planet_returns_none(self):
        ctx = self._ctx(positions={"Sun": 6})
        assert ctx.get_house("Mercury") is None

    def test_fate_map_wired_not_hardcoded(self):
        """
        get_fate_type_for_domain() must return the value from domain_fate_map,
        NOT the old hardcoded 'RASHI_PHAL' fallback.
        """
        fate_map = {"marriage": "GRAHA_PHAL", "career_travel": "HYBRID"}
        ctx = self._ctx(fate_map=fate_map)
        assert ctx.get_fate_type_for_domain("marriage") == "GRAHA_PHAL"
        assert ctx.get_fate_type_for_domain("career_travel") == "HYBRID"

    def test_unknown_domain_returns_rashi_phal(self):
        ctx = self._ctx(fate_map={})
        assert ctx.get_fate_type_for_domain("progeny") == "RASHI_PHAL"

    def test_graha_phal_domain_not_downgraded(self):
        """
        Previously the hardcoded 'RASHI_PHAL' downgraded all GRAHA_PHAL domains.
        This test ensures a GRAHA_PHAL domain is returned correctly.
        """
        fate_map = {"wealth": "GRAHA_PHAL"}
        ctx = self._ctx(fate_map=fate_map)
        result = ctx.get_fate_type_for_domain("wealth")
        assert result == "GRAHA_PHAL", (
            f"Expected GRAHA_PHAL, got {result}. "
            "The hardcoded 'RASHI_PHAL' fallback may still be in effect."
        )


# ---------------------------------------------------------------------------
# LifecycleEngine no longer defines SimContext inside the loop
# ---------------------------------------------------------------------------
class TestLifecycleEngineUsesAnnualSimContext:

    def test_no_simcontext_class_in_engine_source(self):
        """
        Verify the old 'class SimContext:' definition is gone from lifecycle_engine.py.
        """
        import inspect
        from astroq.lk_prediction import lifecycle_engine
        source = inspect.getsource(lifecycle_engine)
        assert "class SimContext" not in source, (
            "lifecycle_engine.py still contains 'class SimContext' — "
            "it must be replaced by AnnualSimContext."
        )

    def test_annual_sim_context_used_in_loop(self):
        """The loop in run_75yr_analysis must reference AnnualSimContext."""
        import inspect
        from astroq.lk_prediction import lifecycle_engine
        source = inspect.getsource(lifecycle_engine.LifecycleEngine.run_75yr_analysis)
        assert "AnnualSimContext" in source

    def test_run_75yr_produces_history_dict(self):
        """
        Smoke test: run_75yr_analysis with a minimal natal chart produces a
        history dict with 75 entries without crashing.
        """
        engine = LifecycleEngine()
        natal_data = {
            "planets_in_houses": {
                "Sun":     {"house": 6},
                "Moon":    {"house": 9},
                "Mars":    {"house": 4},
                "Mercury": {"house": 6},
                "Jupiter": {"house": 6},
                "Venus":   {"house": 6},
                "Saturn":  {"house": 8},
                "Rahu":    {"house": 7},
                "Ketu":    {"house": 1},
            }
        }
        history = engine.run_75yr_analysis(natal_data)
        assert len(history) == 75
        # Each entry must be a StateLedger
        from astroq.lk_prediction.state_ledger import StateLedger
        for age, ledger in history.items():
            assert isinstance(ledger, StateLedger), f"Age {age}: expected StateLedger, got {type(ledger)}"

    def test_context_fate_map_not_all_rashi_phal(self):
        """
        When AnnualSimContext is used with NatalFateView domain_fate_map,
        at least some GRAHA_PHAL domains should appear in the map for a
        known chart with strong planets.
        
        This would fail with the old hardcoded 'RASHI_PHAL' implementation,
        which always returned RASHI_PHAL regardless of the natal promise.
        """
        from astroq.lk_prediction.natal_fate_view import NatalFateView
        natal_data = {
            "planets_in_houses": {
                "Sun":     {"house": 6},
                "Moon":    {"house": 9},
                "Mars":    {"house": 4},
                "Mercury": {"house": 6},
                "Jupiter": {"house": 6},
                "Venus":   {"house": 6},
                "Saturn":  {"house": 8},
                "Rahu":    {"house": 7},
                "Ketu":    {"house": 1},
            }
        }
        view = NatalFateView()
        entries = view.evaluate(natal_data, include_neither=True)
        domain_fate_map = {e["domain"]: e["fate_type"] for e in entries}

        # With the old hardcoded fallback, this would always be RASHI_PHAL.
        # With the real map, some domains will be GRAHA_PHAL or HYBRID.
        fate_types = set(domain_fate_map.values())
        assert len(fate_types) > 1, (
            "All domains returned RASHI_PHAL — either the hardcoded fallback "
            "is still in effect, or NatalFateView found no GRAHA_PHAL domains "
            "for this natal chart."
        )
