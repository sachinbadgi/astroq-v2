import pytest
import os
import tempfile
from backend.tests.graphify_test.rule_extractor import RuleExtractor

def test_rule_extractor_basic():
    # Create a mock constants file
    content = """
VARSHPHAL_TIMING_TRIGGERS = {
    "marriage": [
        {"desc": "Venus or Mercury in 1,2,10,11,12 AND Saturn in 1 or 10", "annual_ven": [1,2,10,11,12], "annual_sat": [1, 10]},
        {"desc": "Annual Venus and Mercury conjoined", "annual_ven_mer_conjoined": [7]}
    ]
}
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tf:
        tf.write(content)
        temp_path = tf.name

    try:
        extractor = RuleExtractor(temp_path)
        rules = extractor.extract()

        assert len(rules) == 2
        
        # Rule 1
        rule1 = next(r for r in rules if "Saturn in 1 or 10" in r.description)
        assert rule1.domain == "marriage"
        assert len(rule1.constraints) == 2
        
        c_ven = next(c for c in rule1.constraints if c.planet == "Venus")
        assert c_ven.houses == [1, 2, 10, 11, 12]
        
        c_sat = next(c for c in rule1.constraints if c.planet == "Saturn")
        assert c_sat.houses == [1, 10]

        # Rule 2 (conjoined)
        rule2 = next(r for r in rules if "conjoined" in r.description)
        assert any(c.planet == "Venus" and c.houses == [7] for c in rule2.constraints)
        assert any(c.planet == "Mercury" and c.houses == [7] for c in rule2.constraints)

    finally:
        os.remove(temp_path)

def test_rule_extractor_production():
    # Run against the real file to ensure no crashes
    real_path = "backend/astroq/lk_prediction/lk_pattern_constants.py"
    if not os.path.exists(real_path):
        pytest.skip("Production file not found")
        
    extractor = RuleExtractor(real_path)
    rules = extractor.extract()
    assert len(rules) > 0
    
    # Check a specific known rule
    marriage_rules = [r for r in rules if r.domain == "marriage"]
    assert len(marriage_rules) > 0
    
    # Verify we can export to JSON
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        json_path = tf.name
    
    try:
        extractor.export_to_json(json_path)
        assert os.path.exists(json_path)
        assert os.path.getsize(json_path) > 0
    finally:
        os.remove(json_path)
