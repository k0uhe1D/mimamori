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


def _fake_analyze_awake(_settings: Settings, _base64_image: str) -> AnalysisResult:
    """Fake analyzer function that returns awake state."""
    return AnalysisResult.create_now(
        posture="仰向け",
        sleep_state="覚醒",
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

    def test_forces_analysis_after_max_skip(self) -> None:
        """AnalyzerWorker forces analysis after max_skip_seconds elapsed."""
        call_count = 0

        def counting_analyze(_settings: Settings, _base64_image: str) -> AnalysisResult:
            nonlocal call_count
            call_count += 1
            return _fake_analyze_awake(_settings, _base64_image)

        state = MonitoringState()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        state.update_frame(frame)

        settings = Settings(openai_api_key="test-key")
        runtime_config = RuntimeConfig(
            analysis_interval_seconds=1,
            max_skip_seconds=2,
        )

        worker = AnalyzerWorker(
            state=state,
            settings=settings,
            runtime_config=runtime_config,
            analyze_fn=counting_analyze,
        )
        worker.start()
        # Wait enough for initial analysis + forced re-analysis after 2s
        time.sleep(3.5)
        worker.stop()

        # First call at T=0, then forced re-analysis after 2s
        assert call_count >= 2

    def test_no_forced_analysis_when_disabled(self) -> None:
        """AnalyzerWorker does not force analysis when max_skip_seconds=0."""
        call_count = 0

        def counting_analyze(_settings: Settings, _base64_image: str) -> AnalysisResult:
            nonlocal call_count
            call_count += 1
            return _fake_analyze(_settings, _base64_image)

        state = MonitoringState()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        state.update_frame(frame)

        settings = Settings(openai_api_key="test-key")
        runtime_config = RuntimeConfig(
            analysis_interval_seconds=1,
            max_skip_seconds=0,
        )

        worker = AnalyzerWorker(
            state=state,
            settings=settings,
            runtime_config=runtime_config,
            analyze_fn=counting_analyze,
        )
        worker.start()
        time.sleep(2.5)
        worker.stop()

        # Only the initial analysis, no forced re-analysis
        assert call_count == 1

    def test_max_skip_seconds_config(self) -> None:
        """RuntimeConfig max_skip_seconds getter/setter works correctly."""
        config = RuntimeConfig(max_skip_seconds=600)
        assert config.max_skip_seconds == 600

        config.max_skip_seconds = 120
        assert config.max_skip_seconds == 120

        config.max_skip_seconds = 0
        assert config.max_skip_seconds == 0

    def test_sleep_state_reduces_api_calls(self) -> None:
        """AnalyzerWorker uses longer interval when baby is sleeping."""
        call_count = 0

        def counting_sleep_analyze(
            _settings: Settings, _base64_image: str
        ) -> AnalysisResult:
            nonlocal call_count
            call_count += 1
            return _fake_analyze(_settings, _base64_image)

        state = MonitoringState()
        settings = Settings(openai_api_key="test-key")
        runtime_config = RuntimeConfig(
            analysis_interval_seconds=1,
            max_skip_seconds=0,
        )

        worker = AnalyzerWorker(
            state=state,
            settings=settings,
            runtime_config=runtime_config,
            analyze_fn=counting_sleep_analyze,
        )

        # Provide a frame, then change it each time to always trigger analysis
        frame1 = np.zeros((480, 640, 3), dtype=np.uint8)
        state.update_frame(frame1)
        worker.start()
        time.sleep(0.5)
        # First analysis runs and returns "睡眠中"
        assert call_count == 1
        # Now update frame so it changes
        frame2 = np.full((480, 640, 3), 100, dtype=np.uint8)
        state.update_frame(frame2)
        # During sleep, interval is 1s * 3 = 3s, so after 2s no new call
        time.sleep(2.0)
        assert call_count == 1  # Still 1, sleep interval hasn't elapsed
        worker.stop()

    def test_awake_state_uses_normal_interval(self) -> None:
        """AnalyzerWorker uses normal interval when baby is awake."""
        call_count = 0

        def counting_awake_analyze(
            _settings: Settings, _base64_image: str
        ) -> AnalysisResult:
            nonlocal call_count
            call_count += 1
            return _fake_analyze_awake(_settings, _base64_image)

        state = MonitoringState()
        settings = Settings(openai_api_key="test-key")
        runtime_config = RuntimeConfig(
            analysis_interval_seconds=1,
            max_skip_seconds=0,
        )

        worker = AnalyzerWorker(
            state=state,
            settings=settings,
            runtime_config=runtime_config,
            analyze_fn=counting_awake_analyze,
        )

        frame1 = np.zeros((480, 640, 3), dtype=np.uint8)
        state.update_frame(frame1)
        worker.start()
        time.sleep(0.5)
        assert call_count == 1
        # Change frame - awake state uses normal 1s interval
        frame2 = np.full((480, 640, 3), 100, dtype=np.uint8)
        state.update_frame(frame2)
        time.sleep(1.5)
        assert call_count >= 2  # Should have analyzed again within 1s
        worker.stop()

    def test_sleep_state_raises_diff_threshold(self) -> None:
        """AnalyzerWorker uses higher diff threshold when sleeping."""
        call_count = 0

        def counting_sleep_analyze(
            _settings: Settings, _base64_image: str
        ) -> AnalysisResult:
            nonlocal call_count
            call_count += 1
            return _fake_analyze(_settings, _base64_image)

        state = MonitoringState()
        settings = Settings(openai_api_key="test-key")
        runtime_config = RuntimeConfig(
            analysis_interval_seconds=1,
            max_skip_seconds=0,
        )

        worker = AnalyzerWorker(
            state=state,
            settings=settings,
            runtime_config=runtime_config,
            analyze_fn=counting_sleep_analyze,
            diff_threshold=5.0,
        )

        # Initial frame triggers first analysis (returns "睡眠中")
        frame1 = np.zeros((480, 640, 3), dtype=np.uint8)
        state.update_frame(frame1)
        worker._analyze_once()
        assert call_count == 1

        # Small change (diff ~3.0) - below sleep threshold (10.0) but above
        # normal threshold (5.0). Should be skipped during sleep.
        frame2 = np.full((480, 640, 3), 8, dtype=np.uint8)
        state.update_frame(frame2)
        worker._analyze_once()
        assert call_count == 1  # Skipped due to raised sleep threshold
