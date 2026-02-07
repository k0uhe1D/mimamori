"""Sleep tracker daemon thread for mimamori monitoring system."""

from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import cv2

from src.core.sleep_session import SleepSession

if TYPE_CHECKING:
    from src.core.state import MonitoringState

logger = logging.getLogger(__name__)

_DEFAULT_CHECK_INTERVAL = 10.0
_DEFAULT_SNAPSHOT_INTERVAL = 300.0
_DEFAULT_SNAPSHOT_DIR = "sleep_snapshots"
_SLEEP_STATE_VALUE = "睡眠中"


class SleepTracker:
    """Tracks baby sleep sessions using analysis results from MonitoringState.

    Runs as a daemon thread, periodically checking the latest analysis result
    to detect sleep onset and wake events. During sleep, captures periodic
    snapshots for timelapse generation.

    Detection logic:
    - New result with sleep_state == "睡眠中" → sleeping
    - No new result + active session → still sleeping (frame unchanged)
    - New result with sleep_state != "睡眠中" + active session → woke up
    """

    def __init__(
        self,
        state: MonitoringState,
        check_interval: float = _DEFAULT_CHECK_INTERVAL,
        snapshot_interval: float = _DEFAULT_SNAPSHOT_INTERVAL,
        snapshot_dir: str = _DEFAULT_SNAPSHOT_DIR,
    ) -> None:
        """Initialize sleep tracker.

        Args:
            state: Shared monitoring state to read results and frames from.
            check_interval: Seconds between state checks.
            snapshot_interval: Seconds between snapshot captures during sleep.
            snapshot_dir: Directory to save sleep snapshots.
        """
        self._state = state
        self._check_interval = check_interval
        self._snapshot_interval = snapshot_interval
        self._snapshot_dir = Path(snapshot_dir)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._sessions: list[SleepSession] = []
        self._last_checked_result_ts: datetime | None = None
        self._last_snapshot_time: datetime | None = None

    def start(self) -> None:
        """Start the sleep tracker daemon thread."""
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="sleep-tracker",
            daemon=True,
        )
        self._thread.start()
        logger.info("SleepTracker started")

    def stop(self) -> None:
        """Stop the sleep tracker and wait for thread to finish."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=10.0)
            self._thread = None
        logger.info("SleepTracker stopped")

    @property
    def active_session(self) -> SleepSession | None:
        """Get the currently active sleep session, if any.

        Returns:
            The active SleepSession, or None if baby is not sleeping.
        """
        with self._lock:
            if self._sessions and self._sessions[-1].is_active:
                return self._sessions[-1]
            return None

    def get_sessions(self, limit: int = 0) -> list[SleepSession]:
        """Get sleep session history, most recent first.

        Args:
            limit: Maximum number of sessions to return (0 for all).

        Returns:
            List of SleepSession in reverse chronological order.
        """
        with self._lock:
            items = list(reversed(self._sessions))
            if limit > 0:
                return items[:limit]
            return items

    def _run(self) -> None:
        """Main tracking loop."""
        while not self._stop_event.is_set():
            try:
                self._check_once()
            except Exception:
                logger.exception("Sleep tracker check failed")
            self._stop_event.wait(timeout=self._check_interval)

    def _check_once(self) -> None:
        """Perform a single sleep state check.

        Logic:
        1. Get latest result from state.
        2. If new result exists: check sleep_state to determine sleeping.
        3. If no new result + active session: still sleeping (frame unchanged).
        4. Start/end sessions and capture snapshots accordingly.
        """
        result = self._state.get_latest_result()
        has_new_result = False
        sleeping = False

        if result is not None:
            if (
                self._last_checked_result_ts is None
                or result.timestamp != self._last_checked_result_ts
            ):
                has_new_result = True
                self._last_checked_result_ts = result.timestamp
                sleeping = result.sleep_state == _SLEEP_STATE_VALUE
            else:
                # No new result — if we have an active session, baby is still sleeping
                sleeping = self.active_session is not None

        active = self.active_session

        if sleeping:
            if active is None:
                self._start_session()
            else:
                self._maybe_capture_snapshot()
        elif has_new_result and active is not None:
            self._end_session()

    def _start_session(self) -> None:
        """Start a new sleep session."""
        session = SleepSession(start_time=datetime.now(tz=UTC))
        with self._lock:
            self._sessions.append(session)
        self._last_snapshot_time = None
        logger.info("Sleep session started at %s", session.start_time.isoformat())

    def _end_session(self) -> None:
        """End the current active sleep session."""
        with self._lock:
            if self._sessions and self._sessions[-1].is_active:
                self._sessions[-1].end_time = datetime.now(tz=UTC)
                session = self._sessions[-1]
        logger.info(
            "Sleep session ended: %.0f seconds",
            session.duration_seconds,
        )

    def _maybe_capture_snapshot(self) -> None:
        """Capture a snapshot if enough time has passed since the last one.

        Saves a JPEG file to the snapshot directory for timelapse generation.
        """
        now = datetime.now(tz=UTC)
        if (
            self._last_snapshot_time is not None
            and (now - self._last_snapshot_time).total_seconds()
            < self._snapshot_interval
        ):
            return

        frame = self._state.get_frame()
        if frame is None:
            return

        self._snapshot_dir.mkdir(parents=True, exist_ok=True)
        filename = now.strftime("%Y%m%d_%H%M%S") + ".jpg"
        filepath = str(self._snapshot_dir / filename)
        cv2.imwrite(filepath, frame)
        self._last_snapshot_time = now

        with self._lock:
            if self._sessions and self._sessions[-1].is_active:
                self._sessions[-1].snapshot_paths.append(filepath)

        logger.debug("Sleep snapshot saved: %s", filepath)
