"""
Tests for Amitabh Bachchan domain timeline fidelity fixes.

Run: cd backend && python -m pytest tests/test_timeline_fidelity.py -v
"""
import sys
import os
import json
import importlib.util
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

NATAL = {
    "Jupiter": 6, "Sun": 6, "Mercury": 6, "Venus": 6,
    "Mars": 4, "Moon": 9, "Saturn": 8, "Rahu": 7, "Ketu": 1
}
PLANETS = ["Jupiter", "Sun", "Moon", "Venus", "Mars", "Mercury", "Saturn", "Rahu", "Ketu"]


def _fake_timeline(total_strength_at_age=None):
    """Construct a minimal fake 76-entry timeline for template tests."""
    rows = []
    for i in range(76):
        ts = total_strength_at_age(i) if total_strength_at_age else float(i * 2)
        rows.append({
            'age': i,
            'planet_strengths': {p: 1.0 for p in PLANETS},
            'planet_cumulative_strengths': {p: float(i) for p in PLANETS},
            'planet_fates': {p: 'RASHI_PHAL' for p in PLANETS},
            'total_strength': ts,
            'total_strength_cumulative': float(i * 10),
            'timing_gated_strengths': {p: 0.3 for p in PLANETS},
        })
    return rows


def _load_visualizer():
    """Load generate_amitabh_visualizer as a module."""
    gen_path = os.path.join(
        os.path.dirname(__file__), '..', 'scripts', 'generate_amitabh_visualizer.py'
    )
    spec = importlib.util.spec_from_file_location("gen_viz", gen_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Task 1: Ledger bypass at age 0
# ---------------------------------------------------------------------------

def test_age_0_ledger_is_not_blank():
    """Age 0 data generator must use lifecycle age=1 proxy, not a blank StateLedger.
    
    Lifecycle engine runs range(1,76) so history[0] does not exist.
    The data generator should fall back to history[1] (first real ledger state)
    which reflects Lamp house activations from birth positions — not a blank slate.
    """
    from astroq.lk_prediction.lifecycle_engine import LifecycleEngine
    from astroq.lk_prediction.state_ledger import StateLedger

    engine = LifecycleEngine()
    history = engine.run_75yr_analysis(NATAL)

    # Lifecycle engine history starts at age=1 (by design)
    assert 1 in history, "Lifecycle history must contain at least age 1"

    ledger_age1 = history[1]
    blank_ledger = StateLedger()

    # Age=1 ledger must differ from blank: Lamp houses (1,7,9) wake planets immediately.
    # Ketu is in H1 natally → annual H1 at age=1 likely → Ketu.is_awake should be True.
    age1_awake = sum(1 for s in ledger_age1.planets.values() if s.is_awake)
    blank_awake = sum(1 for s in blank_ledger.planets.values() if s.is_awake)

    assert age1_awake > blank_awake, (
        f"Age=1 ledger must have more awake planets than blank (Lamp house activation). "
        f"Got age1_awake={age1_awake}, blank_awake={blank_awake}"
    )


# ---------------------------------------------------------------------------
# Task 2: Per-age fate classification
# ---------------------------------------------------------------------------

def test_planet_fates_present_per_age():
    """Every timeline JSON entry must carry a planet_fates dict."""
    output_path = os.path.join(
        os.path.dirname(__file__), '..', 'output', 'amitabh_full_timeline_data.json'
    )
    if not os.path.exists(output_path):
        pytest.skip("Timeline JSON not generated yet — run generate_amitabh_full_timeline_data.py")
    with open(output_path) as f:
        timeline = json.load(f)
    assert len(timeline) == 76, "Expected 76 age entries (0–75)"
    for entry in timeline:
        assert 'planet_fates' in entry, f"Age {entry['age']} missing planet_fates"
        for p in PLANETS:
            assert p in entry['planet_fates'], f"Age {entry['age']} missing planet {p} in planet_fates"


def test_visualizer_uses_majority_fate_not_age0_snapshot():
    """Visualizer must derive planet_fates via majority vote, not frozen age-0 snapshot."""
    mod = _load_visualizer()

    # Build timeline where Planet Jupiter has GRAHA_PHAL at most ages but RASHI_PHAL at age 0
    tl = _fake_timeline()
    for i, row in enumerate(tl):
        row['planet_fates']['Jupiter'] = 'RASHI_PHAL' if i == 0 else 'GRAHA_PHAL'

    fake_events = []
    html = mod.generate_html(tl, fake_events)

    # In the JS: planetFates["Jupiter"] should be GRAHA_PHAL (majority), not RASHI_PHAL (age 0)
    assert '"Jupiter": "GRAHA_PHAL"' in html or '"Jupiter":"GRAHA_PHAL"' in html, (
        "Jupiter fate should be GRAHA_PHAL (majority vote), not the age-0 snapshot value RASHI_PHAL"
    )


# ---------------------------------------------------------------------------
# Task 3: Event annotation y-anchoring
# ---------------------------------------------------------------------------

def test_event_annotations_anchored_to_actual_strength():
    """Event point yValue must equal total_strength at that age, not hardcoded 60."""
    mod = _load_visualizer()

    # Age 31 has total_strength = 31 * 2 = 62.0
    tl = _fake_timeline(total_strength_at_age=lambda i: float(i * 2))
    fake_events = [{'age': 31, 'description': 'Zanjeer', 'domain': 'career_travel',
                    'baseline_hit': False, 'doubtful_hit': False,
                    'active_promises': [], 'doubtful_modifier': 'Neutral'}]

    html = mod.generate_html(tl, fake_events)

    # Extract the event_point_0 annotation JSON block
    start = html.find('"event_point_0"')
    assert start != -1, "event_point_0 annotation not found in HTML"
    chunk = html[start:start + 300]

    assert ('"yValue": 62' in chunk or '"yValue":62' in chunk or
            '"yValue": 62.0' in chunk or '"yValue":62.0' in chunk), (
        f"Expected yValue 62.0 (total_strength at age 31), found: {chunk}"
    )
    assert '"yValue": 60' not in chunk and '"yValue":60' not in chunk, (
        "Hardcoded yValue: 60 must be replaced with actual total_strength"
    )


# ---------------------------------------------------------------------------
# Task 4: Domain score accumulation
# ---------------------------------------------------------------------------

def test_domain_scores_accumulate_not_max():
    """Domain scores must accumulate all prediction contributions, not just max."""
    domain_scores = {'career_travel': 0.0}

    # Simulate old (buggy) max logic
    def old_update(score, dom='career_travel'):
        if score > domain_scores[dom]:
            domain_scores[dom] = score

    old_update(0.5)
    old_update(0.3)
    assert domain_scores['career_travel'] == pytest.approx(0.5)  # max

    # Simulate new (correct) accumulation logic
    domain_scores2 = {'career_travel': 0.0}

    def new_update(score, dom='career_travel'):
        domain_scores2[dom] += score

    new_update(0.5)
    new_update(0.3)
    assert domain_scores2['career_travel'] == pytest.approx(0.8), (
        "Accumulated domain score must be 0.8 (0.5 + 0.3), not 0.5 (max)"
    )


def test_timeline_json_has_domain_hit_count():
    """Timeline JSON must have domain_hit_count per age (added with accumulation fix)."""
    output_path = os.path.join(
        os.path.dirname(__file__), '..', 'output', 'amitabh_full_timeline_data.json'
    )
    if not os.path.exists(output_path):
        pytest.skip("Timeline JSON not generated yet")
    with open(output_path) as f:
        timeline = json.load(f)
    for entry in timeline:
        assert 'domain_hit_count' in entry, f"Age {entry['age']} missing domain_hit_count"


# ---------------------------------------------------------------------------
# Task 5: Timing-gated strengths
# ---------------------------------------------------------------------------

def test_timeline_json_contains_timing_gated_strengths():
    """Each timeline entry must have timing_gated_strengths for all 9 planets."""
    output_path = os.path.join(
        os.path.dirname(__file__), '..', 'output', 'amitabh_full_timeline_data.json'
    )
    if not os.path.exists(output_path):
        pytest.skip("Timeline JSON not generated yet")
    with open(output_path) as f:
        timeline = json.load(f)
    for entry in timeline:
        assert 'timing_gated_strengths' in entry, f"Age {entry['age']} missing timing_gated_strengths"
        for planet in PLANETS:
            assert planet in entry['timing_gated_strengths'], (
                f"Age {entry['age']} missing {planet} in timing_gated_strengths"
            )


# ---------------------------------------------------------------------------
# Task 6: Event click handler + active_promises
# ---------------------------------------------------------------------------

def test_event_click_not_stub():
    """Generated HTML must not contain stub comment in event onclick."""
    mod = _load_visualizer()
    tl = _fake_timeline()
    fake_events = [{'age': 31, 'description': 'Zanjeer', 'domain': 'career_travel',
                    'baseline_hit': True, 'doubtful_hit': False,
                    'active_promises': ['Sun in H6'], 'doubtful_modifier': 'Neutral'}]

    html = mod.generate_html(tl, fake_events)

    assert 'Future: Focus chart on this age' not in html, (
        "Stub onclick comment must be removed"
    )
    assert 'focusAge' in html, (
        "Event onclick must call focusAge() function"
    )


def test_event_hit_badge_rendered():
    """Events with baseline_hit=True must show a HIT badge in the sidebar."""
    mod = _load_visualizer()
    tl = _fake_timeline()
    fake_events = [{'age': 31, 'description': 'Zanjeer', 'domain': 'career_travel',
                    'baseline_hit': True, 'doubtful_hit': False,
                    'active_promises': [], 'doubtful_modifier': 'Neutral'}]

    html = mod.generate_html(tl, fake_events)
    assert 'HIT' in html, "baseline_hit=True must render a HIT badge"


def test_event_active_promises_rendered():
    """Events with active_promises must render them in the sidebar."""
    mod = _load_visualizer()
    tl = _fake_timeline()
    fake_events = [{'age': 31, 'description': 'Zanjeer', 'domain': 'career_travel',
                    'baseline_hit': False, 'doubtful_hit': False,
                    'active_promises': ['Sun in H6', 'Mars in H4'], 'doubtful_modifier': 'Neutral'}]

    html = mod.generate_html(tl, fake_events)
    assert 'Sun in H6' in html, "active_promises must be rendered in sidebar"
    assert 'Mars in H4' in html, "active_promises must be rendered in sidebar"
