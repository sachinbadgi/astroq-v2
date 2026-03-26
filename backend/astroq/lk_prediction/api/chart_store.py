"""
Persistent store for AstroQ charts using SQLite.
Replaces the in-memory charts_db in server.py.
"""

import json
import sqlite3
from typing import List, Dict, Any, Optional
from pathlib import Path

class ChartStore:
    CURRENT_SCHEMA_VERSION = 2
    APP_VERSION = "2.1.0-NFR"

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
        self._migrate_schema()

    def _init_db(self):
        """Initialize the charts table with base columns."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS charts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                dob TEXT NOT NULL,
                tob TEXT,
                pob TEXT,
                planets_json TEXT NOT NULL,
                full_payload_json TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def _migrate_schema(self):
        """Add new columns to existing tables if missing."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check existing columns
        cursor.execute("PRAGMA table_info(charts)")
        columns = [row[1] for row in cursor.fetchall()]
        
        migrations = [
            ("tob", "TEXT"),
            ("pob", "TEXT"),
            ("chart_type", "TEXT DEFAULT 'USER'"),
            ("schema_version", "INTEGER DEFAULT 1"),
            ("app_version", f"TEXT DEFAULT '{self.APP_VERSION}'"),
            ("expires_at", "DATETIME")
        ]
        
        for col_name, col_def in migrations:
            if col_name not in columns:
                cursor.execute(f"ALTER TABLE charts ADD COLUMN {col_name} {col_def}")
                
        conn.commit()
        conn.close()

    def save_chart(self, chart_payload: Dict[str, Any], chart_type: str = "USER", expires_days: Optional[int] = None) -> int:
        """Save a new chart with metadata and return its ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        expires_at = None
        if expires_days is not None:
            cursor.execute("SELECT datetime('now', ?)", (f"{expires_days} days",))
            expires_at = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO charts (name, dob, tob, pob, planets_json, full_payload_json, chart_type, schema_version, app_version, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            chart_payload["name"],
            chart_payload["dob"],
            chart_payload.get("tob", ""),
            chart_payload.get("pob", ""),
            json.dumps(chart_payload["planets_in_houses"]),
            json.dumps(chart_payload["full_payload"]),
            chart_type,
            self.CURRENT_SCHEMA_VERSION,
            self.APP_VERSION,
            expires_at
        ))
        
        id = cursor.lastrowid
        conn.commit()
        conn.close()
        return id

    def get_chart(self, chart_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a chart by ID and perform lazy migration of JSON data."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM charts WHERE id = ?", (chart_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
            
        # Convert row to dict for easy .get() access
        row_dict = dict(row)
        planets = json.loads(row_dict["planets_json"])
        schema_v = row_dict.get("schema_version", 1)
        
        # Lazy Migration Logic
        if schema_v < 2:
            # Ensure every planet has grammar_tags (introduced in v2)
            for p_data in planets.values():
                if isinstance(p_data, dict) and "grammar_tags" not in p_data:
                    p_data["grammar_tags"] = []
                    
        return {
            "id": row_dict["id"],
            "name": row_dict["name"],
            "dob": row_dict["dob"],
            "tob": row_dict.get("tob"),
            "pob": row_dict.get("pob"),
            "planets_in_houses": planets,
            "full_payload": json.loads(row_dict["full_payload_json"]),
            "chart_type": row_dict.get("chart_type", "USER"),
            "schema_version": schema_v,
            "app_version": row_dict.get("app_version", "unknown")
        }

    def cleanup_expired(self) -> int:
        """Purge expired charts and return the count of deleted rows."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM charts WHERE expires_at IS NOT NULL AND expires_at < datetime('now')")
        count = cursor.rowcount
        conn.commit()
        conn.close()
        return count

    def list_charts(self, include_test: bool = False) -> List[Dict[str, Any]]:
        """List all charts, optionally excluding TEST charts."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT id, name, dob, chart_type FROM charts"
        if not include_test:
            query += " WHERE chart_type = 'USER'"
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {"id": row["id"], "client_name": row["name"], "birth_date": row["dob"], "type": row["chart_type"]}
            for row in rows
        ]

    def delete_chart(self, chart_id: int) -> bool:
        """Delete a chart by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM charts WHERE id = ?", (chart_id,))
        count = cursor.rowcount
        conn.commit()
        conn.close()
        return count > 0
