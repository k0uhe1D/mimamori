"""SQLite repository for persisting analysis results and sleep data."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.analyzer.models import AnalysisResult
    from src.core.sleep_session import SleepSession

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = "data/mimamori.db"

_SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS analysis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    posture TEXT NOT NULL,
    sleep_state TEXT NOT NULL,
    summary TEXT NOT NULL,
    confidence TEXT NOT NULL,
    raw_response TEXT NOT NULL,
    anomalies TEXT NOT NULL DEFAULT '[]',
    actions TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS idx_ar_timestamp ON analysis_results(timestamp DESC);

CREATE TABLE IF NOT EXISTS sleep_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_time TEXT NOT NULL,
    end_time TEXT,
    snapshot_paths TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS idx_ss_start ON sleep_sessions(start_time DESC);

CREATE TABLE IF NOT EXISTS daily_timelapses (
    date_str TEXT PRIMARY KEY,
    gif_path TEXT NOT NULL
);
"""


class Repository:
    """SQLite repository for mimamori persistent data.

    Thread-safe via a threading.Lock. Uses WAL journal mode for
    improved concurrent read performance.
    """

    def __init__(self, db_path: str | None = None) -> None:
        """Initialize repository.

        Args:
            db_path: Path to SQLite database file.
                     Defaults to MIMAMORI_DB_PATH env var or "data/mimamori.db".
        """
        self._db_path = db_path or os.environ.get("MIMAMORI_DB_PATH", _DEFAULT_DB_PATH)
        self._lock = threading.Lock()
        self._conn: sqlite3.Connection | None = None

    def initialize(self) -> None:
        """Create database directory, connect, enable WAL mode, and create tables."""
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA_SQL)
        self._conn.commit()
        logger.info("Repository initialized: %s", self._db_path)

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
            logger.info("Repository closed")

    # ------------------------------------------------------------------
    # Analysis Results
    # ------------------------------------------------------------------

    def save_analysis_result(self, result: AnalysisResult) -> None:
        """Persist an analysis result.

        Args:
            result: The AnalysisResult to save.
        """
        with self._lock:
            assert self._conn is not None
            self._conn.execute(
                "INSERT INTO analysis_results "
                "(timestamp, posture, sleep_state, summary, confidence, "
                "raw_response, anomalies, actions) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    result.timestamp.isoformat(),
                    result.posture,
                    result.sleep_state,
                    result.summary,
                    result.confidence,
                    result.raw_response,
                    json.dumps(result.anomalies),
                    json.dumps(result.actions),
                ),
            )
            self._conn.commit()

    def load_analysis_results(self, limit: int = 100) -> list[AnalysisResult]:
        """Load analysis results from the database.

        Args:
            limit: Maximum number of results to return.

        Returns:
            List of AnalysisResult in chronological order (oldest first).
        """
        from src.analyzer.models import AnalysisResult

        with self._lock:
            assert self._conn is not None
            rows = self._conn.execute(
                "SELECT timestamp, posture, sleep_state, summary, confidence, "
                "raw_response, anomalies, actions "
                "FROM analysis_results ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()

        results: list[AnalysisResult] = []
        for row in reversed(rows):
            results.append(
                AnalysisResult(
                    timestamp=datetime.fromisoformat(row[0]).replace(tzinfo=UTC),
                    posture=row[1],
                    sleep_state=row[2],
                    summary=row[3],
                    confidence=row[4],
                    raw_response=row[5],
                    anomalies=json.loads(row[6]),
                    actions=json.loads(row[7]),
                )
            )
        return results

    def load_analysis_results_by_range(
        self, start_iso: str, end_iso: str, limit: int = 500
    ) -> list[AnalysisResult]:
        """Load analysis results within a time range.

        Args:
            start_iso: Start timestamp (inclusive) in ISO format.
            end_iso: End timestamp (exclusive) in ISO format.
            limit: Maximum number of results to return.

        Returns:
            List of AnalysisResult in chronological order (oldest first).
        """
        from src.analyzer.models import AnalysisResult

        with self._lock:
            assert self._conn is not None
            rows = self._conn.execute(
                "SELECT timestamp, posture, sleep_state, summary, confidence, "
                "raw_response, anomalies, actions "
                "FROM analysis_results "
                "WHERE timestamp >= ? AND timestamp < ? "
                "ORDER BY timestamp ASC LIMIT ?",
                (start_iso, end_iso, limit),
            ).fetchall()

        results: list[AnalysisResult] = []
        for row in rows:
            results.append(
                AnalysisResult(
                    timestamp=datetime.fromisoformat(row[0]).replace(tzinfo=UTC),
                    posture=row[1],
                    sleep_state=row[2],
                    summary=row[3],
                    confidence=row[4],
                    raw_response=row[5],
                    anomalies=json.loads(row[6]),
                    actions=json.loads(row[7]),
                )
            )
        return results

    # ------------------------------------------------------------------
    # Sleep Sessions
    # ------------------------------------------------------------------

    def save_sleep_session(self, session: SleepSession) -> int:
        """Persist a new sleep session.

        Args:
            session: The SleepSession to save.

        Returns:
            The database row id for subsequent updates.
        """
        with self._lock:
            assert self._conn is not None
            cursor = self._conn.execute(
                "INSERT INTO sleep_sessions (start_time, end_time, snapshot_paths) "
                "VALUES (?, ?, ?)",
                (
                    session.start_time.isoformat(),
                    session.end_time.isoformat() if session.end_time else None,
                    json.dumps(session.snapshot_paths),
                ),
            )
            self._conn.commit()
            return cursor.lastrowid or 0

    def update_sleep_session(self, db_id: int, session: SleepSession) -> None:
        """Update an existing sleep session row.

        Args:
            db_id: The database row id.
            session: The SleepSession with updated fields.
        """
        with self._lock:
            assert self._conn is not None
            self._conn.execute(
                "UPDATE sleep_sessions SET end_time = ?, snapshot_paths = ? "
                "WHERE id = ?",
                (
                    session.end_time.isoformat() if session.end_time else None,
                    json.dumps(session.snapshot_paths),
                    db_id,
                ),
            )
            self._conn.commit()

    def load_sleep_sessions_by_date(
        self, date_str: str
    ) -> list[tuple[int, SleepSession]]:
        """Load sleep sessions that overlap with a given date.

        Includes sessions that started before the date ends AND
        ended after the date starts (or are still active).

        Args:
            date_str: ISO date string (e.g. "2025-01-15").

        Returns:
            List of (db_id, SleepSession) in chronological order.
        """
        from src.core.sleep_session import SleepSession

        day_start = f"{date_str}T00:00:00"
        day_end = f"{date_str}T23:59:59"

        with self._lock:
            assert self._conn is not None
            rows = self._conn.execute(
                "SELECT id, start_time, end_time, snapshot_paths "
                "FROM sleep_sessions "
                "WHERE start_time <= ? AND (end_time IS NULL OR end_time >= ?) "
                "ORDER BY start_time ASC",
                (day_end, day_start),
            ).fetchall()

        sessions: list[tuple[int, SleepSession]] = []
        for row in rows:
            end_time = (
                datetime.fromisoformat(row[2]).replace(tzinfo=UTC) if row[2] else None
            )
            sessions.append(
                (
                    row[0],
                    SleepSession(
                        start_time=datetime.fromisoformat(row[1]).replace(tzinfo=UTC),
                        end_time=end_time,
                        snapshot_paths=json.loads(row[3]),
                    ),
                )
            )
        return sessions

    def load_sleep_sessions(self) -> list[tuple[int, SleepSession]]:
        """Load all sleep sessions from the database.

        Returns:
            List of (db_id, SleepSession) in chronological order (oldest first).
        """
        from src.core.sleep_session import SleepSession

        with self._lock:
            assert self._conn is not None
            rows = self._conn.execute(
                "SELECT id, start_time, end_time, snapshot_paths "
                "FROM sleep_sessions ORDER BY start_time ASC",
            ).fetchall()

        sessions: list[tuple[int, SleepSession]] = []
        for row in rows:
            end_time = (
                datetime.fromisoformat(row[2]).replace(tzinfo=UTC) if row[2] else None
            )
            sessions.append(
                (
                    row[0],
                    SleepSession(
                        start_time=datetime.fromisoformat(row[1]).replace(tzinfo=UTC),
                        end_time=end_time,
                        snapshot_paths=json.loads(row[3]),
                    ),
                )
            )
        return sessions

    # ------------------------------------------------------------------
    # Daily Timelapses
    # ------------------------------------------------------------------

    def save_daily_timelapse(self, date_str: str, gif_path: str) -> None:
        """Persist a daily timelapse GIF path.

        Args:
            date_str: ISO date string (e.g. "2025-01-15").
            gif_path: Path to the GIF file.
        """
        with self._lock:
            assert self._conn is not None
            self._conn.execute(
                "INSERT OR REPLACE INTO daily_timelapses (date_str, gif_path) "
                "VALUES (?, ?)",
                (date_str, gif_path),
            )
            self._conn.commit()

    def load_daily_timelapses(self) -> dict[str, str]:
        """Load all daily timelapse records.

        Returns:
            Mapping of date_str to gif_path.
        """
        with self._lock:
            assert self._conn is not None
            rows = self._conn.execute(
                "SELECT date_str, gif_path FROM daily_timelapses",
            ).fetchall()
        return dict(rows)
