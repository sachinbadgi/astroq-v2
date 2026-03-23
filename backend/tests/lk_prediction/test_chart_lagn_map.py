import pytest
from astroq.lk_prediction.chart_generator import ChartGenerator

def test_chart_lagn_mapping_sachin():
    """
    TDD for Lagn-based Teva Mapping.
    Profile: Sachin (28-11-1977, 18:30, Sangli)
    Ascendant: Taurus (Sign 2)
    
    Expected Lagn-based Houses (Whole Sign):
    House 1: Asc (Taurus)
    House 2: Moon, Jupiter (Gemini)
    House 3: Mars (Cancer)
    House 4: Saturn (Leo)
    House 5: Rahu (Virgo)
    House 6: Venus (Libra)
    House 7: Sun (Scorpio)
    House 8: Mercury (Sagittarius)
    House 11: Ketu (Pisces)
    """
    gen = ChartGenerator()
    # Sachin's birth data
    dob = "1977-11-28"
    tob = "18:30"
    lat = 16.8524
    lon = 74.5815
    utc = "+05:30"
    
    payload = gen.build_full_chart_payload(
        dob, tob, "Sangli", lat, lon, utc, chart_system="vedic"
    )
    
    # Manually apply grammar for testing (as the API now does)
    from astroq.lk_prediction.grammar_analyser import GrammarAnalyser
    from astroq.lk_prediction.config import ModelConfig
    
    # Use real defaults path from conftest if possible, otherwise hardcode for test
    db_path = "d:/astroq-v2/backend/data/api_config.db"
    defaults_path = "d:/astroq-v2/backend/data/model_defaults.json"
    config = ModelConfig(db_path=db_path, defaults_path=defaults_path)
    analyser = GrammarAnalyser(config)
    
    for key in payload:
        if key.startswith("chart_"):
            chart = payload[key]
            enriched = {p: {"house": d["house"]} for p, d in chart["planets_in_houses"].items()}
            analyser.apply_grammar_rules(chart, enriched)
            for p, ep in enriched.items():
                chart["planets_in_houses"][p].update(ep)

    planets = payload["chart_0"]["planets_in_houses"]
    print(f"\nDEBUG: Sun Data: {planets['Sun']}")
    print(f"DEBUG: Mars Data: {planets['Mars']}")
    
    # Assertions for Lagn-based mapping
    assert planets["Asc"]["house"] == 1
    assert "aspects" not in planets["Asc"] or len(planets["Asc"]["aspects"]) == 0
    
    # Sun in House 7 (Scorpio) aspects House 1 (Taurus)
    # Target in House 1 is "Asc", but Asc should NOT be in the aspects list as it's not a standard planet.
    # However, if there were another planet in H1, it would be there.
    assert "aspects" in planets["Sun"]
    
    # Mars in House 3 aspecting Houses 9 and 11
    # Ketu is in House 11.
    mars_aspects = [a["target"] for a in planets["Mars"].get("aspects", [])]
    assert "Ketu" in mars_aspects
    
    # Check relationship for Mars -> Ketu (Enemies)
    ketu_aspect = next(a for a in planets["Mars"]["aspects"] if a["target"] == "Ketu")
    assert ketu_aspect["relationship"] == "enemy"
