"""Tests for the SQLite repository."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from src.analyzer.models import AnalysisResult
from src.core.sleep_session import SleepSession
from src.db.repository import Repository


@pytest.fixture()
def repo(tmp_path: Path) -> Repository:
    """Create and initialize a repository with a temp DB."""
    db_path = str(tmp_path / "test.db")
    r = Repository(db_path=db_path)
    r.initialize()
    return r


# ------------------------------------------------------------------
# Analysis Results
# ------------------------------------------------------------------


class TestAnalysisResults:
    """Tests for analysis result persistence."""

    def test_save_and_load_roundtrip(self, repo: Repository) -> None:
        """Saved results should be loadable with all fields intact."""
        result = AnalysisResult(
            timestamp=datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC),
            posture="仰向け",
            sleep_state="睡眠中",
            summary="赤ちゃんは安全に眠っています",
            confidence="high",
            raw_response="raw text here",
            anomalies=["布団がずれている"],
            actions=["手を動かしている"],
        )
        repo.save_analysis_result(result)
        loaded = repo.load_analysis_results(limit=10)

        assert len(loaded) == 1
        r = loaded[0]
        assert r.timestamp == result.timestamp
        assert r.posture == result.posture
        assert r.sleep_state == result.sleep_state
        assert r.summary == result.summary
        assert r.confidence == result.confidence
        assert r.raw_response == result.raw_response
        assert r.anomalies == result.anomalies
        assert r.actions == result.actions

    def test_load_returns_chronological_order(self, repo: Repository) -> None:
        """Loaded results should be in chronological order (oldest first)."""
        t1 = datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC)
        t2 = datetime(2025, 1, 15, 11, 0, 0, tzinfo=UTC)
        t3 = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)
        for ts in [t2, t1, t3]:  # Insert out of order
            repo.save_analysis_result(
                AnalysisResult(
                    timestamp=ts,
                    posture="仰向け",
                    sleep_state="覚醒",
                    summary="test",
                    confidence="high",
                    raw_response="raw",
                )
            )
        loaded = repo.load_analysis_results(limit=10)
        assert [r.timestamp for r in loaded] == [t1, t2, t3]

    def test_load_respects_limit(self, repo: Repository) -> None:
        """Only the most recent N results should be returned."""
        base = datetime(2025, 1, 15, tzinfo=UTC)
        for i in range(5):
            repo.save_analysis_result(
                AnalysisResult(
                    timestamp=base + timedelta(hours=i),
                    posture="仰向け",
                    sleep_state="覚醒",
                    summary=f"result {i}",
                    confidence="high",
                    raw_response="raw",
                )
            )
        loaded = repo.load_analysis_results(limit=3)
        assert len(loaded) == 3
        # Should be the 3 most recent, in chronological order
        assert loaded[0].summary == "result 2"
        assert loaded[2].summary == "result 4"

    def test_empty_lists_roundtrip(self, repo: Repository) -> None:
        """Empty anomalies and actions should roundtrip correctly."""
        result = AnalysisResult(
            timestamp=datetime(2025, 1, 15, tzinfo=UTC),
            posture="仰向け",
            sleep_state="覚醒",
            summary="test",
            confidence="high",
            raw_response="raw",
            anomalies=[],
            actions=[],
        )
        repo.save_analysis_result(result)
        loaded = repo.load_analysis_results()
        assert loaded[0].anomalies == []
        assert loaded[0].actions == []


# ------------------------------------------------------------------
# Sleep Sessions
# ------------------------------------------------------------------


class TestSleepSessions:
    """Tests for sleep session persistence."""

    def test_save_and_load_active_session(self, repo: Repository) -> None:
        """An active session (no end_time) should roundtrip correctly."""
        session = SleepSession(
            start_time=datetime(2025, 1, 15, 22, 0, 0, tzinfo=UTC),
        )
        db_id = repo.save_sleep_session(session)
        assert db_id > 0

        pairs = repo.load_sleep_sessions()
        assert len(pairs) == 1
        loaded_id, loaded = pairs[0]
        assert loaded_id == db_id
        assert loaded.start_time == session.start_time
        assert loaded.end_time is None
        assert loaded.snapshot_paths == []

    def test_update_session_end_time(self, repo: Repository) -> None:
        """Updating a session should persist end_time and snapshots."""
        session = SleepSession(
            start_time=datetime(2025, 1, 15, 22, 0, 0, tzinfo=UTC),
        )
        db_id = repo.save_sleep_session(session)

        session.end_time = datetime(2025, 1, 16, 6, 0, 0, tzinfo=UTC)
        session.snapshot_paths = ["/tmp/snap1.jpg", "/tmp/snap2.jpg"]
        repo.update_sleep_session(db_id, session)

        pairs = repo.load_sleep_sessions()
        _, loaded = pairs[0]
        assert loaded.end_time == session.end_time
        assert loaded.snapshot_paths == ["/tmp/snap1.jpg", "/tmp/snap2.jpg"]

    def test_load_sessions_chronological_order(self, repo: Repository) -> None:
        """Sessions should be loaded in chronological order."""
        t1 = datetime(2025, 1, 15, 20, 0, 0, tzinfo=UTC)
        t2 = datetime(2025, 1, 15, 22, 0, 0, tzinfo=UTC)
        # Insert out of order
        repo.save_sleep_session(SleepSession(start_time=t2))
        repo.save_sleep_session(SleepSession(start_time=t1))

        pairs = repo.load_sleep_sessions()
        assert pairs[0][1].start_time == t1
        assert pairs[1][1].start_time == t2


class TestSleepSessionsByDate:
    """Tests for date-filtered sleep session queries."""

    def test_sessions_on_single_date(self, repo: Repository) -> None:
        """Sessions that fall within a date should be returned."""
        session = SleepSession(
            start_time=datetime(2025, 1, 15, 22, 0, 0, tzinfo=UTC),
            end_time=datetime(2025, 1, 16, 2, 0, 0, tzinfo=UTC),
        )
        repo.save_sleep_session(session)
        # Should appear on both Jan 15 and Jan 16
        assert len(repo.load_sleep_sessions_by_date("2025-01-15")) == 1
        assert len(repo.load_sleep_sessions_by_date("2025-01-16")) == 1
        assert len(repo.load_sleep_sessions_by_date("2025-01-17")) == 0

    def test_active_session_appears(self, repo: Repository) -> None:
        """Active sessions (no end_time) should appear on their start date."""
        session = SleepSession(
            start_time=datetime(2025, 1, 15, 23, 0, 0, tzinfo=UTC),
        )
        repo.save_sleep_session(session)
        assert len(repo.load_sleep_sessions_by_date("2025-01-15")) == 1

    def test_no_match(self, repo: Repository) -> None:
        """Sessions outside the date should not be returned."""
        session = SleepSession(
            start_time=datetime(2025, 1, 14, 10, 0, 0, tzinfo=UTC),
            end_time=datetime(2025, 1, 14, 12, 0, 0, tzinfo=UTC),
        )
        repo.save_sleep_session(session)
        assert len(repo.load_sleep_sessions_by_date("2025-01-15")) == 0


class TestAnalysisResultsByRange:
    """Tests for time-range analysis result queries."""

    def test_range_query(self, repo: Repository) -> None:
        """Results within the range should be returned in chronological order."""
        base = datetime(2025, 1, 15, tzinfo=UTC)
        for i in range(5):
            repo.save_analysis_result(
                AnalysisResult(
                    timestamp=base + timedelta(hours=i),
                    posture="仰向け",
                    sleep_state="覚醒",
                    summary=f"result {i}",
                    confidence="high",
                    raw_response="raw",
                )
            )
        results = repo.load_analysis_results_by_range(
            "2025-01-15T01:00:00", "2025-01-15T04:00:00"
        )
        assert len(results) == 3
        assert results[0].summary == "result 1"
        assert results[2].summary == "result 3"

    def test_range_query_empty(self, repo: Repository) -> None:
        """Empty range should return no results."""
        results = repo.load_analysis_results_by_range(
            "2025-01-15T00:00:00", "2025-01-15T23:59:59"
        )
        assert results == []

    def test_range_query_respects_limit(self, repo: Repository) -> None:
        """Limit parameter should cap the number of results."""
        base = datetime(2025, 1, 15, tzinfo=UTC)
        for i in range(10):
            repo.save_analysis_result(
                AnalysisResult(
                    timestamp=base + timedelta(hours=i),
                    posture="仰向け",
                    sleep_state="覚醒",
                    summary=f"result {i}",
                    confidence="high",
                    raw_response="raw",
                )
            )
        results = repo.load_analysis_results_by_range(
            "2025-01-15T00:00:00", "2025-01-16T00:00:00", limit=3
        )
        assert len(results) == 3


# ------------------------------------------------------------------
# Daily Timelapses
# ------------------------------------------------------------------


class TestDailyTimelapses:
    """Tests for daily timelapse persistence."""

    def test_save_and_load(self, repo: Repository) -> None:
        """Saved timelapse paths should be loadable."""
        repo.save_daily_timelapse("2025-01-15", "/data/20250115.gif")
        repo.save_daily_timelapse("2025-01-16", "/data/20250116.gif")

        result = repo.load_daily_timelapses()
        assert result == {
            "2025-01-15": "/data/20250115.gif",
            "2025-01-16": "/data/20250116.gif",
        }

    def test_upsert_overwrites(self, repo: Repository) -> None:
        """Saving the same date again should overwrite the path."""
        repo.save_daily_timelapse("2025-01-15", "/data/old.gif")
        repo.save_daily_timelapse("2025-01-15", "/data/new.gif")

        result = repo.load_daily_timelapses()
        assert result["2025-01-15"] == "/data/new.gif"


# ------------------------------------------------------------------
# Close and Reopen
# ------------------------------------------------------------------


class TestCloseReopen:
    """Tests for data durability across close/reopen cycles."""

    def test_data_persists_after_close_reopen(self, tmp_path: Path) -> None:
        """Data should survive close and reopen."""
        db_path = str(tmp_path / "test.db")

        repo1 = Repository(db_path=db_path)
        repo1.initialize()
        repo1.save_analysis_result(
            AnalysisResult(
                timestamp=datetime(2025, 1, 15, tzinfo=UTC),
                posture="仰向け",
                sleep_state="覚醒",
                summary="test",
                confidence="high",
                raw_response="raw",
            )
        )
        repo1.save_sleep_session(
            SleepSession(start_time=datetime(2025, 1, 15, 22, 0, 0, tzinfo=UTC))
        )
        repo1.save_daily_timelapse("2025-01-15", "/data/test.gif")
        repo1.close()

        repo2 = Repository(db_path=db_path)
        repo2.initialize()
        assert len(repo2.load_analysis_results()) == 1
        assert len(repo2.load_sleep_sessions()) == 1
        assert repo2.load_daily_timelapses() == {"2025-01-15": "/data/test.gif"}
        repo2.close()
