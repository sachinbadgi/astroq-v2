"""
Phase 5: ChartDNA Persistence (AutoResearch 2.0)

Handles SQLite persistence for discovered ChartDNA models.
"""

from __future__ import annotations
import json
import sqlite3
from typing import Optional

from astroq.lk_prediction.data_contracts import ChartDNA


class ChartDNARepository:
    """
    Persistence layer for ChartDNA objects in SQLite.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Create the chart_dna table if it doesn't exist."""
        con = sqlite3.connect(self.db_path)
        try:
            con.execute("""
                CREATE TABLE IF NOT EXISTS chart_dna (
                    figure_id TEXT PRIMARY KEY,
                    back_test_hit_rate REAL,
                    mean_offset_years REAL,
                    iterations_run INTEGER,
                    delay_constants_json TEXT,
                    grammar_overrides_json TEXT,
                    config_overrides_json TEXT,
                    confidence_score REAL,
                    generated_at TEXT
                )
            """)
            con.commit()
        finally:
            con.close()

    def save(self, dna: ChartDNA) -> None:
        """Upsert a ChartDNA object into the database."""
        con = sqlite3.connect(self.db_path)
        try:
            con.execute("""
                INSERT INTO chart_dna (
                    figure_id, back_test_hit_rate, mean_offset_years, iterations_run,
                    delay_constants_json, grammar_overrides_json, config_overrides_json,
                    confidence_score, generated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(figure_id) DO UPDATE SET
                    back_test_hit_rate=excluded.back_test_hit_rate,
                    mean_offset_years=excluded.mean_offset_years,
                    iterations_run=excluded.iterations_run,
                    delay_constants_json=excluded.delay_constants_json,
                    grammar_overrides_json=excluded.grammar_overrides_json,
                    config_overrides_json=excluded.config_overrides_json,
                    confidence_score=excluded.confidence_score,
                    generated_at=excluded.generated_at
            """, (
                dna.figure_id,
                dna.back_test_hit_rate,
                dna.mean_offset_years,
                dna.iterations_run,
                json.dumps(dna.delay_constants),
                json.dumps(dna.grammar_overrides),
                json.dumps(dna.config_overrides),
                dna.confidence_score,
                dna.generated_at
            ))
            con.commit()
        finally:
            con.close()

    def load(self, figure_id: str) -> Optional[ChartDNA]:
        """Load a ChartDNA object by figure_id."""
        con = sqlite3.connect(self.db_path)
        try:
            cur = con.execute("SELECT * FROM chart_dna WHERE figure_id = ?", (figure_id,))
            row = cur.fetchone()
            if not row:
                return None
                
            # Maps row to ChartDNA. columns: figure_id, hit_rate, offset, iterations, delay, grammar, config, confidence, generated_at
            return ChartDNA(
                figure_id=row[0],
                back_test_hit_rate=row[1],
                mean_offset_years=row[2],
                iterations_run=row[3],
                delay_constants=json.loads(row[4]),
                grammar_overrides=json.loads(row[5]),
                config_overrides=json.loads(row[6]),
                confidence_score=row[7],
                generated_at=row[8]
            )
        finally:
            con.close()

    def list_all(self) -> list[ChartDNA]:
        """List all saved ChartDNAs."""
        con = sqlite3.connect(self.db_path)
        try:
            cur = con.execute("SELECT * FROM chart_dna")
            results = []
            for row in cur.fetchall():
                results.append(ChartDNA(
                    figure_id=row[0],
                    back_test_hit_rate=row[1],
                    mean_offset_years=row[2],
                    iterations_run=row[3],
                    delay_constants=json.loads(row[4]),
                    grammar_overrides=json.loads(row[5]),
                    config_overrides=json.loads(row[6]),
                    confidence_score=row[7],
                    generated_at=row[8]
                ))
            return results
        finally:
            con.close()
