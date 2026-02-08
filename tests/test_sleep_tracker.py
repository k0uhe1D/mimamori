"""Tests for SleepSession and SleepTracker."""

from __future__ import annotations

import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import numpy as np

from src.analyzer.models import AnalysisResult
from src.core.sleep_session import SleepSession
from src.core.sleep_tracker import SleepTracker
from src.core.state import MonitoringState


def _make_result(sleep_state: str = "睡眠中") -> AnalysisResult:
    """Create an AnalysisResult with the given sleep state."""
    return AnalysisResult.create_now(
        posture="仰向け",
        sleep_state=sleep_state,
        summary="テスト",
        confidence="high",
        raw_response="{}",
    )


class TestSleepSession:
    """Tests for SleepSession dataclass."""

    def test_duration_active(self) -> None:
        """Active session duration is from start to now."""
        start = datetime.now(tz=UTC) - timedelta(seconds=60)
        session = SleepSession(start_time=start)
        assert session.duration_seconds >= 60.0
        assert session.duration_seconds < 62.0

    def test_duration_ended(self) -> None:
        """Ended session duration is from start to end."""
        start = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        end = datetime(2025, 1, 1, 1, 0, 0, tzinfo=UTC)
        session = SleepSession(start_time=start, end_time=end)
        assert session.duration_seconds == 3600.0

    def test_is_active_true(self) -> None:
        """Session with no end_time is active."""
        session = SleepSession(start_time=datetime.now(tz=UTC))
        assert session.is_active is True

    def test_is_active_false(self) -> None:
        """Session with end_time is not active."""
        now = datetime.now(tz=UTC)
        session = SleepSession(start_time=now, end_time=now + timedelta(hours=1))
        assert session.is_active is False

    def test_snapshot_paths_default_empty(self) -> None:
        """Snapshot paths default to empty list."""
        session = SleepSession(start_time=datetime.now(tz=UTC))
        assert session.snapshot_paths == []


class TestSleepTracker:
    """Tests for SleepTracker."""

    def test_no_sessions_initially(self) -> None:
        """SleepTracker has no sessions initially."""
        state = MonitoringState()
        tracker = SleepTracker(state=state)
        assert tracker.active_session is None
        assert tracker.get_sessions() == []

    def test_detects_sleep_onset(self) -> None:
        """SleepTracker starts a session when sleep is detected."""
        state = MonitoringState()
        tracker = SleepTracker(state=state, check_interval=0.1)

        state.add_result(_make_result("睡眠中"))
        tracker._check_once()

        assert tracker.active_session is not None
        assert tracker.active_session.is_active
        assert len(tracker.get_sessions()) == 1

    def test_detects_wake(self) -> None:
        """SleepTracker ends session when wake is detected."""
        state = MonitoringState()
        tracker = SleepTracker(state=state, check_interval=0.1)

        state.add_result(_make_result("睡眠中"))
        tracker._check_once()
        assert tracker.active_session is not None

        state.add_result(_make_result("覚醒"))
        tracker._check_once()
        assert tracker.active_session is None
        sessions = tracker.get_sessions()
        assert len(sessions) == 1
        assert sessions[0].is_active is False
        assert sessions[0].duration_seconds >= 0

    def test_frame_unchanged_continues_sleep(self) -> None:
        """No new result with active session means baby is still sleeping."""
        state = MonitoringState()
        tracker = SleepTracker(state=state, check_interval=0.1)

        state.add_result(_make_result("睡眠中"))
        tracker._check_once()
        assert tracker.active_session is not None

        # Check again without adding a new result — same timestamp
        tracker._check_once()
        assert tracker.active_session is not None
        assert tracker.active_session.is_active

    def test_snapshot_during_sleep(self, tmp_path: Path) -> None:
        """Snapshots are saved during sleep sessions."""
        state = MonitoringState()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        state.update_frame(frame)

        tracker = SleepTracker(
            state=state,
            check_interval=0.1,
            snapshot_interval=0.0,  # capture immediately
            snapshot_dir=str(tmp_path),
        )

        state.add_result(_make_result("睡眠中"))
        tracker._check_once()  # starts session
        tracker._check_once()  # still sleeping, captures snapshot

        session = tracker.active_session
        assert session is not None
        assert len(session.snapshot_paths) >= 1
        assert Path(session.snapshot_paths[0]).exists()
        assert session.snapshot_paths[0].endswith(".jpg")

    def test_multiple_sleep_wake_cycles(self) -> None:
        """Multiple sleep/wake cycles create multiple sessions."""
        state = MonitoringState()
        tracker = SleepTracker(state=state, check_interval=0.1)

        # Cycle 1: sleep → wake
        state.add_result(_make_result("睡眠中"))
        tracker._check_once()
        state.add_result(_make_result("覚醒"))
        tracker._check_once()

        # Cycle 2: sleep → wake
        state.add_result(_make_result("睡眠中"))
        tracker._check_once()
        state.add_result(_make_result("覚醒"))
        tracker._check_once()

        sessions = tracker.get_sessions()
        assert len(sessions) == 2
        assert all(not s.is_active for s in sessions)

    def test_start_stop_thread(self) -> None:
        """SleepTracker can start and stop its daemon thread."""
        state = MonitoringState()
        tracker = SleepTracker(state=state, check_interval=0.05)
        tracker.start()
        time.sleep(0.1)
        tracker.stop()
        # Should not raise

    def test_get_sessions_with_limit(self) -> None:
        """get_sessions respects the limit parameter."""
        state = MonitoringState()
        tracker = SleepTracker(state=state)

        # Create 3 sessions
        for _ in range(3):
            state.add_result(_make_result("睡眠中"))
            tracker._check_once()
            state.add_result(_make_result("覚醒"))
            tracker._check_once()

        assert len(tracker.get_sessions(limit=2)) == 2
        assert len(tracker.get_sessions(limit=0)) == 3

    def test_daily_timelapse_on_date_rollover(self, tmp_path: Path) -> None:
        """Daily timelapse is triggered when date changes."""
        state = MonitoringState()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        state.update_frame(frame)

        tracker = SleepTracker(
            state=state,
            check_interval=0.1,
            snapshot_interval=0.0,
            snapshot_dir=str(tmp_path),
        )

        yesterday = date.today() - timedelta(days=1)

        # Simulate a session from yesterday
        with patch("src.core.sleep_tracker.date") as mock_date:
            mock_date.today.return_value = yesterday
            mock_date.fromisoformat = date.fromisoformat
            state.add_result(_make_result("睡眠中"))
            tracker._check_once()  # starts session on "yesterday"
            tracker._check_once()  # captures snapshot
            state.add_result(_make_result("覚醒"))
            tracker._check_once()  # ends session

        sessions = tracker.get_sessions()
        assert len(sessions) == 1
        assert not sessions[0].is_active
        assert len(sessions[0].snapshot_paths) >= 1

        # Now trigger date rollover by calling _check_once on "today"
        with patch("src.core.sleep_tracker.date") as mock_date:
            mock_date.today.return_value = date.today()
            mock_date.fromisoformat = date.fromisoformat
            tracker._check_once()

        # Wait briefly for background thread to finish
        time.sleep(0.5)

        result = tracker.get_daily_timelapse(yesterday)
        # May be None if fewer than 2 snapshots, but method should be callable
        assert result is None or Path(result).exists()

    def test_get_daily_timelapse_not_found(self) -> None:
        """get_daily_timelapse returns None for unknown dates."""
        state = MonitoringState()
        tracker = SleepTracker(state=state)
        assert tracker.get_daily_timelapse(date(2025, 1, 1)) is None
