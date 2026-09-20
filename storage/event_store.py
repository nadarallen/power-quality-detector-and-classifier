"""
Embedded Power Quality Event Store & Persistence Layer
------------------------------------------------------
Lightweight SQLite-backed event repository storing:
- High-level event metadata (event_id, timestamps, duration, class, confidence, affected phases)
- Per-phase electrical metrics (RMS, THD, peak, crest factor, harmonic ratios)
- Optional raw waveform snapshot capture for post-mortem analysis
- Query interfaces by time range, disturbance class, and affected phase
"""

import sqlite3
import json
import os
from typing import List, Optional, Dict, Any

from dsp.event_engine import PQEvent, PhaseMeasurement


class EventStore:
    """Persistent SQLite event repository for 3-phase power quality events."""

    def __init__(self, db_path: str = "data/pq_events.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initializes database tables if they do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pq_events (
                    event_id TEXT PRIMARY KEY,
                    start_time_utc REAL NOT NULL,
                    end_time_utc REAL NOT NULL,
                    duration_ms REAL NOT NULL,
                    event_class TEXT NOT NULL,
                    overall_confidence REAL NOT NULL,
                    affected_phases TEXT NOT NULL,
                    phase_metrics_json TEXT NOT NULL,
                    device_id TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_time ON pq_events (start_time_utc);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_class ON pq_events (event_class);")
            conn.commit()

    def save_event(self, event: PQEvent) -> bool:
        """Persists a PQEvent object to the database."""
        # Serialize phase metrics
        metrics_dict = {}
        for phase, m in event.phase_metrics.items():
            metrics_dict[phase] = {
                "rms_voltage": m.rms_voltage,
                "min_rms": m.min_rms,
                "max_rms": m.max_rms,
                "thd_2_11": m.thd_2_11,
                "fundamental_frequency": m.fundamental_frequency,
                "peak_voltage": m.peak_voltage,
                "crest_factor": m.crest_factor,
                "harmonics": m.harmonics,
                "classification": m.classification,
                "confidence": m.confidence
            }

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO pq_events (
                    event_id, start_time_utc, end_time_utc, duration_ms,
                    event_class, overall_confidence, affected_phases,
                    phase_metrics_json, device_id, source_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                event.event_id,
                event.start_time_utc,
                event.end_time_utc,
                event.duration_ms,
                event.event_class,
                event.overall_confidence,
                json.dumps(event.affected_phases),
                json.dumps(metrics_dict),
                event.device_id,
                event.source_type
            ))
            conn.commit()
            return True

    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Fetches a single event by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pq_events WHERE event_id = ?;", (event_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_dict(row)

    def query_events(
        self,
        event_class: Optional[str] = None,
        phase: Optional[str] = None,
        start_time_after: Optional[float] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Queries recorded events with optional filtering."""
        query = "SELECT * FROM pq_events WHERE 1=1"
        params = []

        if event_class:
            query += " AND event_class = ?"
            params.append(event_class)
        if phase:
            query += " AND affected_phases LIKE ?"
            params.append(f'%"{phase}"%')
        if start_time_after:
            query += " AND start_time_utc >= ?"
            params.append(start_time_after)

        query += " ORDER BY start_time_utc DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            return [self._row_to_dict(r) for r in rows]

    def get_event_stats(self) -> Dict[str, Any]:
        """Calculates aggregate event statistics by disturbance class and phase."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT event_class, COUNT(*) as count, AVG(duration_ms) as avg_duration_ms
                FROM pq_events
                GROUP BY event_class;
            """)
            rows = cursor.fetchall()
            by_class = {
                row["event_class"]: {
                    "count": row["count"],
                    "avg_duration_ms": round(row["avg_duration_ms"], 2)
                } for row in rows
            }
            cursor.execute("SELECT COUNT(*) as total FROM pq_events;")
            total = cursor.fetchone()["total"]

            # Calculate phase counts
            cursor.execute("SELECT affected_phases FROM pq_events;")
            phase_rows = cursor.fetchall()
            by_phase: Dict[str, int] = {}
            for prow in phase_rows:
                phases = json.loads(prow["affected_phases"])
                for p in phases:
                    by_phase[p] = by_phase.get(p, 0) + 1

            return {"total_events": total, "by_class": by_class, "by_phase": by_phase}

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        d["affected_phases"] = json.loads(d["affected_phases"])
        d["phase_metrics"] = json.loads(d["phase_metrics_json"])
        del d["phase_metrics_json"]
        return d
