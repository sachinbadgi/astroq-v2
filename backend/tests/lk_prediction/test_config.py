"""
Tests for Module 1: Centralized Config (ModelConfig).

Tests written FIRST (TDD Red phase) — 8 unit tests.
"""

import json
import os
import sqlite3

import pytest


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestModelConfig:
    """ModelConfig: loads defaults, supports overrides, hierarchical resolution."""

    def test_config_loads_defaults_json(self, tmp_defaults, tmp_db):
        """Config loads values from the defaults JSON file."""
        from astroq.lk_prediction.config import ModelConfig

        cfg = ModelConfig(db_path=tmp_db, defaults_path=tmp_defaults)
        assert cfg.get("strength.natal.pakka_ghar") == 2.20
        assert cfg.get("strength.natal.exalted") == 5.00

    def test_config_returns_fallback_on_missing_key(self, tmp_defaults, tmp_db):
        """Missing key returns the hardcoded fallback (None by default)."""
        from astroq.lk_prediction.config import ModelConfig

        cfg = ModelConfig(db_path=tmp_db, defaults_path=tmp_defaults)
        assert cfg.get("nonexistent.key") is None
        assert cfg.get("nonexistent.key", fallback=42) == 42

    def test_config_global_override_beats_default(self, tmp_defaults, tmp_db):
        """A global override takes priority over the JSON default."""
        from astroq.lk_prediction.config import ModelConfig

        cfg = ModelConfig(db_path=tmp_db, defaults_path=tmp_defaults)
        cfg.set_override("strength.natal.pakka_ghar", 3.50)

        assert cfg.get("strength.natal.pakka_ghar") == 3.50  # override
        assert cfg.get("strength.natal.exalted") == 5.00      # still default

    def test_config_figure_override_beats_global(self, tmp_defaults, tmp_db):
        """A figure-specific override takes priority over global overrides."""
        from astroq.lk_prediction.config import ModelConfig

        cfg = ModelConfig(db_path=tmp_db, defaults_path=tmp_defaults)
        cfg.set_override("strength.natal.pakka_ghar", 3.50)                     # global
        cfg.set_override("strength.natal.pakka_ghar", 4.00, figure="sachin")     # figure

        assert cfg.get("strength.natal.pakka_ghar", figure="sachin") == 4.00
        assert cfg.get("strength.natal.pakka_ghar") == 3.50  # global still holds

    def test_config_get_group_returns_all_keys(self, tmp_defaults, tmp_db):
        """get_group returns all keys matching a prefix."""
        from astroq.lk_prediction.config import ModelConfig

        cfg = ModelConfig(db_path=tmp_db, defaults_path=tmp_defaults)
        group = cfg.get_group("strength.natal")

        assert "pakka_ghar" in group
        assert "exalted" in group
        assert "debilitated" in group
        assert "fixed_house_lord" in group
        assert group["pakka_ghar"] == 2.20

    def test_config_set_and_retrieve_override(self, tmp_defaults, tmp_db):
        """set_override stores value and get retrieves it."""
        from astroq.lk_prediction.config import ModelConfig

        cfg = ModelConfig(db_path=tmp_db, defaults_path=tmp_defaults)
        cfg.set_override("custom.new_key", 99.9, source="test")

        assert cfg.get("custom.new_key") == 99.9

    def test_config_reset_overrides_clears_figure(self, tmp_defaults, tmp_db):
        """reset_overrides removes figure-specific overrides."""
        from astroq.lk_prediction.config import ModelConfig

        cfg = ModelConfig(db_path=tmp_db, defaults_path=tmp_defaults)
        cfg.set_override("strength.natal.exalted", 10.0, figure="sachin")
        assert cfg.get("strength.natal.exalted", figure="sachin") == 10.0

        cfg.reset_overrides(figure="sachin")
        # After reset, should fall through to default
        assert cfg.get("strength.natal.exalted", figure="sachin") == 5.00

    def test_config_hierarchical_resolution(self, tmp_defaults, tmp_db):
        """Full resolution chain: figure → global → json → fallback."""
        from astroq.lk_prediction.config import ModelConfig

        cfg = ModelConfig(db_path=tmp_db, defaults_path=tmp_defaults)

        # Level 1: JSON default
        assert cfg.get("probability.sigmoid.k_base") == 0.45

        # Level 2: Global override
        cfg.set_override("probability.sigmoid.k_base", 0.50)
        assert cfg.get("probability.sigmoid.k_base") == 0.50

        # Level 3: Figure override
        cfg.set_override("probability.sigmoid.k_base", 0.60, figure="bill_gates")
        assert cfg.get("probability.sigmoid.k_base", figure="bill_gates") == 0.60
        assert cfg.get("probability.sigmoid.k_base") == 0.50  # global still

        # Level 4: Fallback for unknown key
        assert cfg.get("unknown.key", fallback="default_val") == "default_val"
