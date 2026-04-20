"""
Module 1: Centralized Config — ModelConfig.

Loads default values from ``model_defaults.json``, supports global and
figure-specific overrides persisted in a SQLite database, and provides
a hierarchical resolution chain::

    figure_override(key, figure) → global_override(key) → json_default(key) → fallback
"""

from __future__ import annotations

import json
import os
import sqlite3
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Hardcoded fallback — used only when a key is not in JSON or DB.
# ---------------------------------------------------------------------------

_HARDCODED_FALLBACK = None


class ModelConfig:
    """
    Centralised configuration for the LK Prediction Model.

    Parameters
    ----------
    db_path : str
        Path to the SQLite database for override storage.
    defaults_path : str
        Path to the ``model_defaults.json`` file.
    """

    def __init__(self, db_path: str, defaults_path: str) -> None:
        self._db_path = db_path
        self._defaults: dict[str, Any] = {}
        self._volatile_overrides: dict[str, Any] = {}

        # Load JSON defaults
        if os.path.isfile(defaults_path):
            with open(defaults_path, "r", encoding="utf-8") as fh:
                self._defaults = json.load(fh)

        # Ensure override tables exist in SQLite
        self._init_db()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(
        self,
        key: str,
        figure: str | None = None,
        fallback: Any = _HARDCODED_FALLBACK,
    ) -> Any:
        """
        Resolve a config value using the hierarchical chain.

        Resolution order:
            0. Volatile override (highest priority, in-memory only)
            1. Figure-specific override (if *figure* is provided)
            2. Global override
            3. JSON default
            4. *fallback* (defaults to ``None``)
        """
        # 0. Volatile override
        if key in self._volatile_overrides:
            return self._volatile_overrides[key]

        # 1. Figure override
        if figure:
            val = self._get_override(key, figure=figure)
            if val is not None:
                return val

        # 2. Global override
        val = self._get_override(key, figure=None)
        if val is not None:
            return val

        # 3. JSON default
        if key in self._defaults:
            return self._defaults[key]

        # 4. Fallback
        return fallback

    def set_volatile_overrides(self, overrides: dict[str, Any]) -> None:
        """Set ad-hoc, non-persistent overrides for research iterations."""
        self._volatile_overrides.update(overrides)

    def clear_volatile_overrides(self) -> None:
        """Clear all volatile overrides."""
        self._volatile_overrides.clear()

    def get_group(self, prefix: str, figure: str | None = None) -> dict[str, Any]:
        """
        Return all keys matching *prefix* as a flat dict with the prefix
        stripped.  For example, ``get_group("strength.natal")`` returns
        ``{"pakka_ghar": 2.20, "exalted": 5.00, …}``.
        """
        full_prefix = prefix + "."
        result: dict[str, Any] = {}

        # Collect from JSON defaults
        for k, v in self._defaults.items():
            if k.startswith(full_prefix):
                short_key = k[len(full_prefix):]
                result[short_key] = v

        # Layer overrides on top (global then figure)
        for k, v in self._list_overrides(figure=None):
            if k.startswith(full_prefix):
                result[k[len(full_prefix):]] = v

        if figure:
            for k, v in self._list_overrides(figure=figure):
                if k.startswith(full_prefix):
                    result[k[len(full_prefix):]] = v

        return result

    def set_override(
        self,
        key: str,
        value: Any,
        figure: str | None = None,
        source: str = "manual",
    ) -> None:
        """Persist an override to the SQLite database."""
        fig = figure or "__global__"
        value_json = json.dumps(value)

        con = self._connect()
        try:
            con.execute(
                """
                INSERT OR REPLACE INTO model_config_overrides
                    (key, figure, value, source)
                VALUES (?, ?, ?, ?)
                """,
                (key, fig, value_json, source),
            )
            con.commit()
        finally:
            con.close()

    def reset_overrides(self, figure: str | None = None) -> None:
        """Remove all overrides for *figure* (or global if ``None``)."""
        fig = figure or "__global__"
        con = self._connect()
        try:
            con.execute(
                "DELETE FROM model_config_overrides WHERE figure = ?",
                (fig,),
            )
            con.commit()
        finally:
            con.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        con = self._connect()
        try:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS model_config_overrides (
                    key    TEXT NOT NULL,
                    figure TEXT NOT NULL DEFAULT '__global__',
                    value  TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT 'manual',
                    PRIMARY KEY (key, figure)
                )
                """
            )
            con.commit()
        finally:
            con.close()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _get_override(self, key: str, figure: str | None) -> Any | None:
        fig = figure or "__global__"
        con = self._connect()
        try:
            row = con.execute(
                "SELECT value FROM model_config_overrides WHERE key = ? AND figure = ?",
                (key, fig),
            ).fetchone()
        finally:
            con.close()

        if row is not None:
            return json.loads(row[0])
        return None

    def _list_overrides(self, figure: str | None):
        fig = figure or "__global__"
        con = self._connect()
        try:
            rows = con.execute(
                "SELECT key, value FROM model_config_overrides WHERE figure = ?",
                (fig,),
            ).fetchall()
        finally:
            con.close()

        return [(k, json.loads(v)) for k, v in rows]
