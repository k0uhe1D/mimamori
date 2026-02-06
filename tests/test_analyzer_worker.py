"""Tests for AnalyzerWorker."""

from __future__ import annotations

import time

import numpy as np

from src.analyzer.models import AnalysisResult
from src.config.runtime_config import RuntimeConfig
from src.config.settings import Settings
from src.core.analyzer_worker import AnalyzerWorker
from src.core.state import MonitoringState


def _fake_analyze(_settings: Settings, _base64_image: str) -> AnalysisResult:
    """Fake analyzer function for testing."""
    return AnalysisResult.create_now(
        posture="仰向け",
        sleep_state="睡眠中",
        summary="テスト結果",
        confidence="high",
        raw_response="{}",
    )


def _error_analyze(_settings: Settings, _base64_image: str) -> AnalysisResult:
    """Fake analyzer that raises an exception."""
    msg = "LLM API error"
    raise RuntimeError(msg)


class TestAnalyzerWorker:
    """Tests for AnalyzerWorker."""

    def test_analyzes_frame_and_stores_result(self) -> None:
        """AnalyzerWorker analyzes available frame and stores result."""
        state = MonitoringState()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        state.update_frame(frame)

        settings = Settings(openai_api_key="test-key")
        runtime_config = RuntimeConfig(analysis_interval_seconds=1)

        worker = AnalyzerWorker(
            state=state,
            settings=settings,
            runtime_config=runtime_config,
            analyze_fn=_fake_analyze,
        )
        worker.start()
        time.sleep(0.5)
        worker.stop()

        result = state.get_latest_result()
        assert result is not None
        assert result.posture == "仰向け"

    def test_skips_when_no_frame(self) -> None:
        """AnalyzerWorker skips analysis when no frame is available."""
        state = MonitoringState()
        settings = Settings(openai_api_key="test-key")
        runtime_config = RuntimeConfig(analysis_interval_seconds=1)

        worker = AnalyzerWorker(
            state=state,
            settings=settings,
            runtime_config=runtime_config,
            analyze_fn=_fake_analyze,
        )
        worker.start()
        time.sleep(0.5)
        worker.stop()

        assert state.get_latest_result() is None

    def test_continues_after_error(self) -> None:
        """AnalyzerWorker continues running after analysis error."""
        state = MonitoringState()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        state.update_frame(frame)

        settings = Settings(openai_api_key="test-key")
        runtime_config = RuntimeConfig(analysis_interval_seconds=1)

        worker = AnalyzerWorker(
            state=state,
            settings=settings,
            runtime_config=runtime_config,
            analyze_fn=_error_analyze,
        )
        worker.start()
        time.sleep(0.5)
        # Worker should still be running despite errors
        assert worker._thread is not None
        assert worker._thread.is_alive()
        worker.stop()

    def test_stop_is_idempotent(self) -> None:
        """Calling stop() multiple times does not raise."""
        state = MonitoringState()
        settings = Settings(openai_api_key="test-key")
        runtime_config = RuntimeConfig(analysis_interval_seconds=1)

        worker = AnalyzerWorker(
            state=state,
            settings=settings,
            runtime_config=runtime_config,
            analyze_fn=_fake_analyze,
        )
        worker.start()
        worker.stop()
        worker.stop()  # Should not raise

    def test_pause_skips_analysis(self) -> None:
        """AnalyzerWorker does not analyze when paused."""
        state = MonitoringState()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        state.update_frame(frame)

        settings = Settings(openai_api_key="test-key")
        runtime_config = RuntimeConfig(analysis_interval_seconds=1)

        worker = AnalyzerWorker(
            state=state,
            settings=settings,
            runtime_config=runtime_config,
            analyze_fn=_fake_analyze,
        )
        worker.pause()
        worker.start()
        time.sleep(0.5)
        worker.stop()

        assert state.get_latest_result() is None
        assert worker.paused

    def test_resume_after_pause(self) -> None:
        """AnalyzerWorker resumes analysis after being paused."""
        state = MonitoringState()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        state.update_frame(frame)

        settings = Settings(openai_api_key="test-key")
        runtime_config = RuntimeConfig(analysis_interval_seconds=1)

        worker = AnalyzerWorker(
            state=state,
            settings=settings,
            runtime_config=runtime_config,
            analyze_fn=_fake_analyze,
        )
        worker.pause()
        worker.start()
        time.sleep(0.3)
        assert state.get_latest_result() is None
        worker.resume()
        assert not worker.paused
        time.sleep(1.5)
        worker.stop()

        assert state.get_latest_result() is not None

    def test_skips_unchanged_frame(self) -> None:
        """AnalyzerWorker skips analysis when frame is unchanged."""
        call_count = 0

        def counting_analyze(_settings: Settings, _base64_image: str) -> AnalysisResult:
            nonlocal call_count
            call_count += 1
            return _fake_analyze(_settings, _base64_image)

        state = MonitoringState()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        state.update_frame(frame)

        settings = Settings(openai_api_key="test-key")
        runtime_config = RuntimeConfig(analysis_interval_seconds=1)

        worker = AnalyzerWorker(
            state=state,
            settings=settings,
            runtime_config=runtime_config,
            analyze_fn=counting_analyze,
        )
        worker.start()
        time.sleep(2.5)
        worker.stop()

        # First call analyzes, subsequent ones skip (same frame)
        assert call_count == 1
