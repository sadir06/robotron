"""SQLite-backed event store for QC pipeline logging.

Non-invasive — call log_event() from the pipeline, query later.
DB file lives at data/qc_events.db (auto-created).
"""

import sqlite3
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from data.models import QCEvent, QCSessionStats

_DB_PATH = Path(__file__).parent / "qc_events.db"
_local = threading.local()


def _conn() -> sqlite3.Connection:
    """Thread-local SQLite connection."""
    if not hasattr(_local, "conn"):
        _local.conn = sqlite3.connect(str(_DB_PATH))
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
    return _local.conn


def init_db():
    """Create tables if they don't exist."""
    c = _conn()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS qc_events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT NOT NULL,
            timestamp   TEXT NOT NULL,
            item_id     INTEGER NOT NULL,
            label       TEXT NOT NULL,
            raw_vlm_response TEXT,
            vlm_latency_ms   REAL,
            vlm_model        TEXT,
            action           TEXT,
            trajectory_file  TEXT,
            motor_positions_start TEXT,
            motor_positions_end   TEXT,
            stability_frames INTEGER DEFAULT 1,
            outcome          TEXT DEFAULT 'unverified',
            frame_b64        TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_session ON qc_events(session_id);
        CREATE INDEX IF NOT EXISTS idx_label   ON qc_events(label);
        CREATE INDEX IF NOT EXISTS idx_ts      ON qc_events(timestamp);
    """)
    c.commit()


# ── Session management ──

_session_id: str = ""
_session_start: datetime = datetime.utcnow()


def start_session() -> str:
    """Begin a new logging session. Returns session_id."""
    global _session_id, _session_start
    _session_id = uuid.uuid4().hex[:12]
    _session_start = datetime.utcnow()
    init_db()
    return _session_id


def current_session() -> str:
    if not _session_id:
        return start_session()
    return _session_id


# ── Write ──

def log_event(event: QCEvent):
    """Insert a QC event into the database."""
    c = _conn()
    c.execute(
        """INSERT INTO qc_events
           (session_id, timestamp, item_id, label, raw_vlm_response,
            vlm_latency_ms, vlm_model, action, trajectory_file,
            motor_positions_start, motor_positions_end,
            stability_frames, outcome, frame_b64)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            current_session(),
            event.timestamp.isoformat(),
            event.item_id,
            event.label,
            event.raw_vlm_response,
            event.vlm_latency_ms,
            event.vlm_model,
            event.action,
            event.trajectory_file,
            str(event.motor_positions_start) if event.motor_positions_start else None,
            str(event.motor_positions_end) if event.motor_positions_end else None,
            event.stability_frames,
            event.outcome,
            event.frame_b64,
        ),
    )
    c.commit()


# ── Read ──

def get_events(
    session_id: Optional[str] = None,
    label: Optional[str] = None,
    limit: int = 100,
) -> list[dict]:
    """Query events with optional filters."""
    c = _conn()
    query = "SELECT * FROM qc_events WHERE 1=1"
    params: list = []

    if session_id:
        query += " AND session_id = ?"
        params.append(session_id)
    if label:
        query += " AND label = ?"
        params.append(label)

    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    rows = c.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def get_session_stats(session_id: Optional[str] = None) -> QCSessionStats:
    """Aggregate stats for a session (defaults to current)."""
    sid = session_id or current_session()
    c = _conn()

    row = c.execute(
        """SELECT
             COUNT(*)                                    AS total,
             SUM(CASE WHEN label='GOOD'    THEN 1 ELSE 0 END) AS good,
             SUM(CASE WHEN label='FAULTY'  THEN 1 ELSE 0 END) AS faulty,
             SUM(CASE WHEN label='NOTHING' THEN 1 ELSE 0 END) AS nothing_count,
             AVG(vlm_latency_ms)                               AS avg_lat,
             MIN(timestamp)                                    AS first_ts
           FROM qc_events WHERE session_id = ?""",
        (sid,),
    ).fetchone()

    total_classified = (row["good"] or 0) + (row["faulty"] or 0)

    return QCSessionStats(
        session_id=sid,
        started_at=datetime.fromisoformat(row["first_ts"]) if row["first_ts"] else _session_start,
        total_items=row["total"] or 0,
        good_count=row["good"] or 0,
        faulty_count=row["faulty"] or 0,
        nothing_count=row["nothing_count"] or 0,
        avg_vlm_latency_ms=round(row["avg_lat"] or 0, 1),
        fault_rate=round((row["faulty"] or 0) / total_classified, 4) if total_classified else 0.0,
    )


def get_training_export(session_id: Optional[str] = None, label: Optional[str] = None) -> list[dict]:
    """Export events in a format suitable for LeRobot policy training.

    Returns list of dicts with fields matching LeRobot dataset conventions:
    image (b64), action label, motor positions, outcome.
    """
    events = get_events(session_id=session_id, label=label, limit=10000)
    export = []
    for e in events:
        if e["label"] == "NOTHING":
            continue
        export.append({
            "timestamp": e["timestamp"],
            "image_b64": e["frame_b64"],
            "classification": e["label"],
            "action": e["action"],
            "trajectory_file": e["trajectory_file"],
            "motor_start": e["motor_positions_start"],
            "motor_end": e["motor_positions_end"],
            "outcome": e["outcome"],
            "vlm_response": e["raw_vlm_response"],
            "vlm_latency_ms": e["vlm_latency_ms"],
        })
    return export
