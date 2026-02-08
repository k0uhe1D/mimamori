"""Sleep tracker daemon thread for mimamori monitoring system."""

from __future__ import annotations

import logging
import threading
from datetime import UTC, date, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import cv2

from src.core.sleep_session import SleepSession

if TYPE_CHECKING:
    from src.core.state import MonitoringState
    from src.db.repository import Repository

logger = logging.getLogger(__name__)

_DEFAULT_CHECK_INTERVAL = 10.0
_DEFAULT_SNAPSHOT_INTERVAL = 300.0
_DEFAULT_SNAPSHOT_DIR = "sleep_snapshots"
_SLEEP_STATE_VALUE = "睡眠中"
_TIMELAPSE_MAX_WIDTH = 480
_TIMELAPSE_FRAME_DURATION_MS = 500


def generate_timelapse_gif(
    snapshot_paths: list[str],
    output_path: str,
    max_width: int = _TIMELAPSE_MAX_WIDTH,
) -> str | None:
    """Generate a timelapse GIF from snapshot JPEG files.

    Args:
        snapshot_paths: Ordered list of JPEG file paths.
        output_path: Path to write the output GIF.
        max_width: Maximum width for resizing frames.

    Returns:
        The output_path on success, or None if fewer than 2 valid images.
    """
    from PIL import Image

    frames: list[Image.Image] = []
    for path in snapshot_paths:
        try:
            img = Image.open(path)
        except (FileNotFoundError, OSError):
            logger.debug("Skipping missing/corrupt snapshot: %s", path)
            continue
        w, h = img.size
        frame: Image.Image = img
        if w > max_width:
            ratio = max_width / w
            frame = img.resize((max_width, int(h * ratio)))
        frames.append(frame.convert("RGB"))

    if len(frames) < 2:
        return None

    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=_TIMELAPSE_FRAME_DURATION_MS,
        loop=0,
    )
    logger.info("Timelapse GIF created: %s (%d frames)", output_path, len(frames))
    return output_path


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
        repository: Repository | None = None,
    ) -> None:
        """Initialize sleep tracker.

        Args:
            state: Shared monitoring state to read results and frames from.
            check_interval: Seconds between state checks.
            snapshot_interval: Seconds between snapshot captures during sleep.
            snapshot_dir: Directory to save sleep snapshots.
            repository: Optional SQLite repository for persistence.
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
        self._current_date: date | None = None
        self._daily_timelapses: dict[str, str] = {}
        self._repository = repository
        self._session_db_ids: dict[int, int] = {}  # id(session) → DB row id

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
        0. Check for date rollover → build daily timelapse for previous day.
        1. Get latest result from state.
        2. If new result exists: check sleep_state to determine sleeping.
        3. If no new result + active session: still sleeping (frame unchanged).
        4. Start/end sessions and capture snapshots accordingly.
        """
        today = date.today()
        if self._current_date is not None and today != self._current_date:
            self._build_daily_timelapse(self._current_date)
        self._current_date = today

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
        if self._repository is not None:
            db_id = self._repository.save_sleep_session(session)
            self._session_db_ids[id(session)] = db_id
        self._last_snapshot_time = None
        logger.info("Sleep session started at %s", session.start_time.isoformat())

    def _end_session(self) -> None:
        """End the current active sleep session."""
        with self._lock:
            if self._sessions and self._sessions[-1].is_active:
                self._sessions[-1].end_time = datetime.now(tz=UTC)
                session = self._sessions[-1]
        if self._repository is not None:
            db_id = self._session_db_ids.get(id(session))
            if db_id is not None:
                self._repository.update_sleep_session(db_id, session)
        logger.info(
            "Sleep session ended: %.0f seconds",
            session.duration_seconds,
        )

    def _build_daily_timelapse(self, target_date: date) -> None:
        """Build a daily timelapse GIF from all sessions on the target date.

        Collects snapshots from all sessions whose start_time falls on
        target_date (local time) and generates a single GIF in a background
        thread.

        Args:
            target_date: The local date to build the timelapse for.
        """
        all_snapshots: list[str] = []
        with self._lock:
            for session in self._sessions:
                if session.start_time.astimezone().date() == target_date:
                    all_snapshots.extend(session.snapshot_paths)

        if not all_snapshots:
            return

        date_str = target_date.isoformat()
        gif_name = target_date.strftime("%Y%m%d") + "_daily_timelapse.gif"
        output_path = str(self._snapshot_dir / gif_name)

        def _generate() -> None:
            try:
                result = generate_timelapse_gif(all_snapshots, output_path)
                if result is not None:
                    with self._lock:
                        self._daily_timelapses[date_str] = result
                    if self._repository is not None:
                        self._repository.save_daily_timelapse(date_str, result)
                    logger.info("Daily timelapse built for %s", date_str)
            except Exception:
                logger.exception("Failed to build daily timelapse for %s", date_str)

        t = threading.Thread(target=_generate, name="daily-timelapse", daemon=True)
        t.start()

    def get_daily_timelapse(self, target_date: date) -> str | None:
        """Get the path to the daily timelapse GIF for a given date.

        Args:
            target_date: The date to look up.

        Returns:
            Path to the GIF file, or None if not available.
        """
        with self._lock:
            return self._daily_timelapses.get(target_date.isoformat())

    def restore_from_repository(self) -> None:
        """Restore sleep sessions and daily timelapses from the repository.

        Loads persisted data into in-memory structures.
        No-op if no repository is configured.
        """
        if self._repository is None:
            return
        pairs = self._repository.load_sleep_sessions()
        with self._lock:
            for db_id, session in pairs:
                self._sessions.append(session)
                self._session_db_ids[id(session)] = db_id
        timelapses = self._repository.load_daily_timelapses()
        with self._lock:
            self._daily_timelapses.update(timelapses)

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
                session = self._sessions[-1]
            else:
                session = None

        if session is not None and self._repository is not None:
            db_id = self._session_db_ids.get(id(session))
            if db_id is not None:
                self._repository.update_sleep_session(db_id, session)

        logger.debug("Sleep snapshot saved: %s", filepath)
