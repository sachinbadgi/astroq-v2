
import pytest
import json
from astroq.lk_prediction.pipeline import LKPredictionPipeline
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.data_contracts import ChartData

class TestPayloadEnrichment:

    def _make_pipeline(self, tmp_db, tmp_defaults):
        import sqlite3
        con = sqlite3.connect(tmp_db)
        con.execute('''CREATE TABLE IF NOT EXISTS deterministic_rules (
                        id TEXT PRIMARY KEY, domain TEXT, description TEXT, condition TEXT,
                        verdict TEXT, scale TEXT, scoring_type TEXT, source_page TEXT,
                        success_weight REAL)''')
        con.commit()
        con.close()
        cfg = ModelConfig(db_path=tmp_db, defaults_path=tmp_defaults)
        return LKPredictionPipeline(cfg)

    def test_generate_llm_payload_contains_ground_truth(self, tmp_db, tmp_defaults, sample_natal_chart, sample_annual_chart):
        """
        TDD RED: The payload should contain all Ground Truth markers like cycle rulers and grammar status.
        Currently, these are expected to be MISSING.
        """
        pipeline = self._make_pipeline(tmp_db, tmp_defaults)
        pipeline.load_natal_baseline(sample_natal_chart)
        
        # In the actual pipeline, annual_timeline is a list of ChartData dicts
        # sample_annual_chart (age 25) should trigger cycle ruler logic if processed correctly
        
        # Correct signature: generate_llm_payload(natal_chart, annual_charts)
        # annual_charts is {age: ChartData}
        annual_charts = {25: sample_annual_chart}
        
        payload = pipeline.generate_llm_payload(
            natal_chart=sample_natal_chart,
            annual_charts=annual_charts
        )
        
        # 1. Check Natal Baseline Enrichment
        natal = payload["natal_promise_baseline"]
        # Currently, natal["planets_in_houses"] is just {planet: house}
        # We want it to be {planet: {house: X, kaayam_status: Y, ...}}
        
        planets = natal["planets_in_houses"]
        for planet in ["Sun", "Moon", "Mars"]:
            data = planets.get(planet)
            assert isinstance(data, dict), f"Natal planet {planet} should be a dict, got {type(data)}"
            assert "kaayam_status" in data, f"Missing kaayam_status for {planet} in natal"
            assert "dharmi_status" in data, f"Missing dharmi_status for {planet} in natal"
            assert "sleeping_status" in data, f"Missing sleeping_status for {planet} in natal"
            assert "strength_total" in data, f"Missing strength_total for {planet} in natal"

        # Chart level enrichment
        assert "mangal_badh_status" in natal, "Missing mangal_badh_status in natal"
        assert "dharmi_kundli_status" in natal, "Missing dharmi_kundli_status in natal"
        assert "lal_kitab_debts" in natal, "Missing lal_kitab_debts in natal"

        # 2. Check Annual Timeline Enrichment
        annual = payload["annual_fulfillment_timeline"][0]
        # Currently annual omits cycle rulers
        assert "35_year_cycle_ruler" in annual, "Missing 35_year_cycle_ruler in annual"
        assert "35_year_intermediary_ruler" in annual, "Missing 35_year_intermediary_ruler in annual"
        
        # Planet level in annual
        annual_planets = annual["planets_in_houses"]
        for planet in ["Sun", "Moon"]:
            data = annual_planets.get(planet)
            assert "kaayam_status" in data, f"Missing kaayam_status for {planet} in annual"
            assert "strength_total" in data, f"Missing strength_total for {planet} in annual"

        # 3. Check House Status
        assert "house_status" in annual, "Missing house_status in annual timeline"
