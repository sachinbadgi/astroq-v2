"""Tests for the PhysicsEngine -- physics pre-processing layer."""
import pytest
from astroq.lk_prediction.physics_engine import PhysicsEngine
from astroq.lk_prediction.data_contracts import RuleHit


# ─── Test Helpers ────────────────────────────────────────────────────────────

def _make_hit(rule_id="R1", domain="Career", magnitude=0.5,
              scoring_type="boost", planets=None, houses=None):
    return RuleHit(
        rule_id=rule_id, domain=domain,
        description="test rule", verdict="positive",
        magnitude=magnitude, scoring_type=scoring_type,
        # Default: Saturn in H9 — NOT its Pakka Ghar (H10), not exalted/debilitated there
        primary_target_planets=planets or ["Saturn"],
        target_houses=houses or [9],
    )


def _minimal_chart(planets_in_houses=None, house_status=None,
                   masnui=None, debts=None):
    return {
        "chart_type": "Birth",
        "chart_period": 0,
        # Default: Saturn in H9 — NOT a Pakka Ghar / exaltation / debilitation house
        "planets_in_houses": planets_in_houses or {"Saturn": {"house": 9, "states": []}},
        "house_status": house_status or {},
        "masnui_grahas_formed": masnui or [],
        "lal_kitab_debts": debts or [],
    }


def _minimal_enriched(planets=None):
    if planets is None:
        # Saturn in H9: NOT Pakka Ghar (H10), NOT exalted (H7), NOT debilitated (H1)
        planets = {"Saturn": {"house": 9, "sleeping_status": "Awake",
                               "strength_total": 3.0, "states": []}}
    return planets


# ─── Test 1.1: Instantiation ─────────────────────────────────────────────────

def test_physics_engine_instantiates():
    engine = PhysicsEngine()
    assert engine is not None


# ─── Test 1.2: Default mutability is FLEXIBLE ─────────────────────────────────

def test_default_mutability_is_flexible():
    engine = PhysicsEngine()
    hit = _make_hit()
    chart = _minimal_chart()
    enriched = _minimal_enriched()
    result = engine.process(chart, [hit], enriched)
    assert len(result) == 1
    assert getattr(result[0], "mutability", None) == "FLEXIBLE"


# ─── Test 1.3: SLEEPING planet → SLEEPING tag ────────────────────────────────

def test_sleeping_planet_tagged_sleeping():
    engine = PhysicsEngine()
    # Venus: Pakka Ghar=H7, Exaltation=H12, Debilitation=H6
    # Venus in H9 is NONE of those → will NOT be FIXED
    enriched = _minimal_enriched({
        "Venus": {"house": 9, "sleeping_status": "Sleeping",
                  "strength_total": 2.0, "states": []}
    })
    hit = _make_hit(planets=["Venus"], houses=[9])
    chart = _minimal_chart(
        planets_in_houses={"Venus": {"house": 9}},
        house_status={}
    )
    result = engine.process(chart, [hit], enriched)
    assert getattr(result[0], "mutability") == "SLEEPING"


# ─── Test 1.4: Sleeping house → GATED tag ────────────────────────────────────

def test_sleeping_house_gates_planet():
    engine = PhysicsEngine()
    # Mercury: Pakka Ghar=H7, Exaltation=H6, Debilitation=H12
    # Mercury in H9 is NONE of those → will NOT be FIXED
    enriched = _minimal_enriched({
        "Mercury": {"house": 9, "sleeping_status": "Awake",
                    "strength_total": 4.0, "states": []}
    })
    hit = _make_hit(planets=["Mercury"], houses=[9])
    chart = _minimal_chart(
        planets_in_houses={"Mercury": {"house": 9}},
        house_status={"9": "Sleeping House"}
    )
    result = engine.process(chart, [hit], enriched)
    assert getattr(result[0], "mutability") == "GATED"


# ─── Test 1.5: Pakka Ghar → FIXED + magnitude saturated ──────────────────────

def test_pakka_ghar_is_fixed():
    """Sun in H1 (its Pakka Ghar) must become FIXED with magnitude 0.9."""
    engine = PhysicsEngine()
    enriched = _minimal_enriched({
        "Sun": {"house": 1, "sleeping_status": "Awake", "strength_total": 6.0,
                "states": ["Fixed House Lord"]}
    })
    hit = _make_hit(planets=["Sun"], houses=[1], magnitude=0.4)
    chart = _minimal_chart(
        planets_in_houses={"Sun": {"house": 1, "states": ["Fixed House Lord"]}}
    )
    result = engine.process(chart, [hit], enriched)
    assert getattr(result[0], "mutability") == "FIXED"
    assert result[0].magnitude == pytest.approx(0.9)


# ─── Test 1.6: Masnui conjunction → SYNTHETIC tag + virtual_planet ───────────

def test_masnui_conjunction_tagged_synthetic():
    """Rule hitting Sun where Sun+Venus formed Artificial Jupiter → SYNTHETIC."""
    engine = PhysicsEngine()
    enriched = _minimal_enriched({
        "Sun":   {"house": 2, "sleeping_status": "Awake",
                  "strength_total": 3.0, "states": []},
        "Venus": {"house": 2, "sleeping_status": "Awake",
                  "strength_total": 3.0, "states": []},
    })
    hit = _make_hit(planets=["Sun"], houses=[2])
    chart = _minimal_chart(
        planets_in_houses={"Sun": {"house": 2}, "Venus": {"house": 2}},
        masnui=[{
            "masnui_graha_name": "Artificial Jupiter",
            "house": 2,
            "components": ["Sun", "Venus"],
            "magnitude": 1.25,
        }],
    )
    result = engine.process(chart, [hit], enriched)
    assert getattr(result[0], "mutability") == "SYNTHETIC"
    vp = getattr(result[0], "virtual_planet")
    assert vp is not None
    assert vp["name"] == "Artificial Jupiter"
    assert vp["type"] == "MASNUI"


# ─── Test 1.7: Rin debt → SYSTEMIC_LEAK + remedy sentinel ────────────────────

def test_rin_debt_tagged_systemic_leak():
    """Rule hitting H6 where Daughter Debt is active → SYSTEMIC_LEAK.
    Using H6/Moon — Moon's Pakka Ghar is H4, so H6 is NOT FIXED.
    """
    engine = PhysicsEngine()
    enriched = _minimal_enriched({
        "Moon": {"house": 6, "sleeping_status": "Awake",
                 "strength_total": 3.0, "states": []}
    })
    hit = _make_hit(planets=["Moon"], houses=[6])
    chart = _minimal_chart(
        planets_in_houses={"Moon": {"house": 6}},
        debts=[{
            "debt_name": "Daughter/Sister Debt (Behen/Beti Rin)",
            "active": True,
            "trigger_planets": ["Moon"],
            "trigger_houses": [6],
        }],
    )
    result = engine.process(chart, [hit], enriched)
    assert getattr(result[0], "mutability") == "SYSTEMIC_LEAK"
    ss = getattr(result[0], "structural_status")
    assert ss is not None
    assert ss["is_rina"] is True
    remedy_hints = getattr(result[0], "remedy_hints", [])
    assert "[COLLECTIVE_ACTIVATION_REQUIRED]" in remedy_hints


# ─── Test 1.8: Priority order ─────────────────────────────────────────────────

def test_fixed_takes_priority_over_sleeping():
    """Planet in Pakka Ghar AND sleeping → FIXED wins."""
    engine = PhysicsEngine()
    enriched = _minimal_enriched({
        "Moon": {"house": 4, "sleeping_status": "Sleeping",
                 "strength_total": 2.0, "states": ["Fixed House Lord"]}
    })
    hit = _make_hit(planets=["Moon"], houses=[4])
    chart = _minimal_chart(
        planets_in_houses={"Moon": {"house": 4, "states": ["Fixed House Lord"]}}
    )
    result = engine.process(chart, [hit], enriched)
    assert getattr(result[0], "mutability") == "FIXED"
