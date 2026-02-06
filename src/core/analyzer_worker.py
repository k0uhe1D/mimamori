"""Analyzer worker daemon thread for mimamori."""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

from src.capture.encoding import encode_frame_to_base64

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.analyzer.models import AnalysisResult
    from src.config.runtime_config import RuntimeConfig
    from src.config.settings import Settings
    from src.core.state import MonitoringState

logger = logging.getLogger(__name__)


class AnalyzerWorker:
    """Daemon thread that periodically analyzes frames via LLM.

    Reads the latest frame from MonitoringState, sends it to the
    configured LLM provider, and stores the result back in state.
    """

    def __init__(
        self,
        state: MonitoringState,
        settings: Settings,
        runtime_config: RuntimeConfig,
        analyze_fn: Callable[[Settings, str], AnalysisResult],
    ) -> None:
        """Initialize analyzer worker.

        Args:
            state: Shared monitoring state.
            settings: Application settings.
            runtime_config: Runtime-mutable configuration.
            analyze_fn: Callable (settings, base64_image) -> AnalysisResult.
        """
        self._state = state
        self._settings = settings
        self._runtime_config = runtime_config
        self._analyze_fn = analyze_fn
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

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

    def _run(self) -> None:
        """Analysis loop."""
        while not self._stop_event.is_set():
            try:
                self._analyze_once()
            except Exception:
                logger.exception("Analysis failed, will retry next interval")

            interval = self._runtime_config.analysis_interval_seconds
            self._stop_event.wait(timeout=interval)

    def _analyze_once(self) -> None:
        """Perform a single analysis cycle."""
        frame = self._state.get_frame()
        if frame is None:
            logger.debug("No frame available for analysis")
            return

        base64_image = encode_frame_to_base64(frame)
        result = self._analyze_fn(self._settings, base64_image)
        self._state.add_result(result)

        logger.info(
            "Analysis complete: posture=%s, sleep=%s, anomalies=%d",
            result.posture,
            result.sleep_state,
            len(result.anomalies),
        )
