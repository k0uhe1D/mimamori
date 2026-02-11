"""Analyzer worker daemon thread for mimamori."""

from __future__ import annotations

import logging
import threading
import time
from typing import TYPE_CHECKING

import cv2
import numpy as np

from src.capture.encoding import encode_frame_to_base64

if TYPE_CHECKING:
    from collections.abc import Callable

    import numpy.typing as npt

    from src.analyzer.models import AnalysisResult
    from src.config.runtime_config import RuntimeConfig
    from src.config.settings import Settings
    from src.core.state import MonitoringState

logger = logging.getLogger(__name__)

_DEFAULT_DIFF_THRESHOLD = 5.0
_SLEEP_STATE = "睡眠中"
_SLEEP_INTERVAL_MULTIPLIER = 3
_SLEEP_DIFF_MULTIPLIER = 2.0
_SLEEP_MAX_SKIP_MULTIPLIER = 2


class AnalyzerWorker:
    """Daemon thread that periodically analyzes frames via LLM.

    Reads the latest frame from MonitoringState, sends it to the
    configured LLM provider, and stores the result back in state.
    Skips analysis when frames haven't changed significantly.
    """

    def __init__(
        self,
        state: MonitoringState,
        settings: Settings,
        runtime_config: RuntimeConfig,
        analyze_fn: Callable[[Settings, str], AnalysisResult],
        diff_threshold: float = _DEFAULT_DIFF_THRESHOLD,
    ) -> None:
        """Initialize analyzer worker.

        Args:
            state: Shared monitoring state.
            settings: Application settings.
            runtime_config: Runtime-mutable configuration.
            analyze_fn: Callable (settings, base64_image) -> AnalysisResult.
            diff_threshold: Mean pixel difference threshold to trigger analysis.
        """
        self._state = state
        self._settings = settings
        self._runtime_config = runtime_config
        self._analyze_fn = analyze_fn
        self._diff_threshold = diff_threshold
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_analyzed_frame: npt.NDArray[np.uint8] | None = None
        self._last_analysis_time: float | None = None

    def start(self) -> None:
        """Start the analyzer worker daemon thread."""
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="analyzer-worker",
            daemon=True,
        )
        self._thread.start()
        logger.info("AnalyzerWorker started")

    def stop(self) -> None:
        """Stop the analyzer worker and wait for thread to finish."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=10.0)
            self._thread = None
        logger.info("AnalyzerWorker stopped")

    def pause(self) -> None:
        """Pause analysis (worker thread keeps running but skips analysis)."""
        self._pause_event.set()
        logger.info("AnalyzerWorker paused")

    def resume(self) -> None:
        """Resume analysis after pause."""
        self._pause_event.clear()
        logger.info("AnalyzerWorker resumed")

    @property
    def paused(self) -> bool:
        """Check if the analyzer is currently paused."""
        return self._pause_event.is_set()

    def _is_sleeping(self) -> bool:
        """Check if the latest analysis indicates the baby is sleeping.

        Returns:
            True if the most recent result has sleep_state == "睡眠中".
        """
        result = self._state.get_latest_result()
        return result is not None and result.sleep_state == _SLEEP_STATE

    def _run(self) -> None:
        """Analysis loop."""
        while not self._stop_event.is_set():
            if not self._pause_event.is_set():
                try:
                    self._analyze_once()
                except Exception:
                    logger.exception("Analysis failed, will retry next interval")

            interval = self._runtime_config.analysis_interval_seconds
            if self._is_sleeping():
                interval *= _SLEEP_INTERVAL_MULTIPLIER
            self._stop_event.wait(timeout=interval)

    def _is_frame_changed(self, frame: npt.NDArray[np.uint8]) -> bool:
        """Check if the frame has changed significantly from the last analyzed frame.

        Uses a higher threshold during sleep to ignore minor movements
        like breathing.

        Args:
            frame: Current frame to compare.

        Returns:
            True if the frame has changed enough to warrant analysis.
        """
        if self._last_analyzed_frame is None:
            return True
        if frame.shape != self._last_analyzed_frame.shape:
            return True
        diff = cv2.absdiff(frame, self._last_analyzed_frame)
        mean_diff: float = float(np.mean(diff.astype(np.float64)))
        threshold = self._diff_threshold
        if self._is_sleeping():
            threshold *= _SLEEP_DIFF_MULTIPLIER
        if mean_diff < threshold:
            logger.debug(
                "Frame unchanged (diff=%.2f < threshold=%.2f), skipping",
                mean_diff,
                threshold,
            )
            return False
        return True

    def _should_force_analysis(self) -> bool:
        """Check if analysis should be forced due to elapsed time.

        Uses a longer timeout during sleep to reduce unnecessary API calls.

        Returns:
            True if max_skip_seconds has elapsed since the last analysis.
        """
        if self._last_analysis_time is None:
            return False
        max_skip = self._runtime_config.max_skip_seconds
        if max_skip <= 0:
            return False
        if self._is_sleeping():
            max_skip *= _SLEEP_MAX_SKIP_MULTIPLIER
        return time.monotonic() - self._last_analysis_time >= max_skip

    def _analyze_once(self) -> None:
        """Perform a single analysis cycle."""
        frame = self._state.get_frame()
        if frame is None:
            logger.debug("No frame available for analysis")
            return

        if not self._is_frame_changed(frame):
            if not self._should_force_analysis():
                return
            logger.info(
                "Forcing analysis after %d seconds without change",
                self._runtime_config.max_skip_seconds,
            )

        self._last_analyzed_frame = frame.copy()
        base64_image = encode_frame_to_base64(frame)
        result = self._analyze_fn(self._settings, base64_image)
        self._state.add_result(result)
        self._last_analysis_time = time.monotonic()

        logger.info(
            "Analysis complete: posture=%s, sleep=%s, anomalies=%d",
            result.posture,
            result.sleep_state,
            len(result.anomalies),
        )
