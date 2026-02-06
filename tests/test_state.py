"""Tests for MonitoringState."""

from __future__ import annotations

import numpy as np

from src.analyzer.models import AnalysisResult
from src.core.state import MonitoringState


class TestMonitoringState:
    """Tests for MonitoringState."""

    def test_get_frame_returns_none_initially(self) -> None:
        """get_frame returns None when no frame has been set."""
        state = MonitoringState()
        assert state.get_frame() is None

    def test_update_and_get_frame(self) -> None:
        """get_frame returns a copy of the updated frame."""
        state = MonitoringState()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[0, 0, 0] = 42

        state.update_frame(frame)
        result = state.get_frame()

        assert result is not None
        assert result[0, 0, 0] == 42
        # Must be a copy, not the same object
        assert result is not frame

    def test_get_frame_returns_copy(self) -> None:
        """Modifying the returned frame does not affect stored frame."""
        state = MonitoringState()
        frame = np.ones((100, 100, 3), dtype=np.uint8)
        state.update_frame(frame)

        returned = state.get_frame()
        assert returned is not None
        returned[0, 0, 0] = 255

        stored = state.get_frame()
        assert stored is not None
        assert stored[0, 0, 0] == 1

    def test_get_latest_result_returns_none_initially(self) -> None:
        """get_latest_result returns None before any analysis."""
        state = MonitoringState()
        assert state.get_latest_result() is None

    def test_add_and_get_latest_result(self) -> None:
        """add_result stores and get_latest_result retrieves it."""
        state = MonitoringState()
        result = AnalysisResult.create_now(
            posture="仰向け",
            sleep_state="睡眠中",
            summary="正常",
            confidence="high",
            raw_response="{}",
        )
        state.add_result(result)
        assert state.get_latest_result() == result

    def test_get_history_empty(self) -> None:
        """get_history returns empty list when no results exist."""
        state = MonitoringState()
        assert state.get_history() == []

    def test_get_history_returns_reverse_chronological(self) -> None:
        """get_history returns results in reverse chronological order."""
        state = MonitoringState()
        results = []
        for i in range(3):
            r = AnalysisResult.create_now(
                posture=f"posture-{i}",
                sleep_state="睡眠中",
                summary=f"summary-{i}",
                confidence="high",
                raw_response="{}",
            )
            state.add_result(r)
            results.append(r)

        history = state.get_history()
        assert len(history) == 3
        assert history[0].posture == "posture-2"
        assert history[2].posture == "posture-0"

    def test_get_history_with_limit(self) -> None:
        """get_history respects the limit parameter."""
        state = MonitoringState()
        for i in range(5):
            state.add_result(
                AnalysisResult.create_now(
                    posture=f"posture-{i}",
                    sleep_state="睡眠中",
                    summary="ok",
                    confidence="high",
                    raw_response="{}",
                )
            )

        history = state.get_history(limit=2)
        assert len(history) == 2

    def test_history_respects_maxlen(self) -> None:
        """History deque does not exceed maxlen."""
        state = MonitoringState(history_maxlen=3)
        for i in range(5):
            state.add_result(
                AnalysisResult.create_now(
                    posture=f"posture-{i}",
                    sleep_state="睡眠中",
                    summary="ok",
                    confidence="high",
                    raw_response="{}",
                )
            )

        history = state.get_history()
        assert len(history) == 3
        assert history[0].posture == "posture-4"
