"""Thread-safe shared state for mimamori monitoring."""

from __future__ import annotations

import threading
from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np
    import numpy.typing as npt

    from src.analyzer.models import AnalysisResult

_DEFAULT_HISTORY_MAXLEN = 100


class MonitoringState:
    """Thread-safe shared state between frame grabber, analyzer, and web server.

    Stores the latest camera frame, latest analysis result, and a bounded
    history of past results.
    """

    def __init__(self, history_maxlen: int = _DEFAULT_HISTORY_MAXLEN) -> None:
        """Initialize monitoring state.

        Args:
            history_maxlen: Maximum number of analysis results to keep in history.
        """
        self._lock = threading.Lock()
        self._frame: npt.NDArray[np.uint8] | None = None
        self._latest_result: AnalysisResult | None = None
        self._history: deque[AnalysisResult] = deque(maxlen=history_maxlen)

    def update_frame(self, frame: npt.NDArray[np.uint8]) -> None:
        """Update the latest camera frame.

        Args:
            frame: BGR image as numpy array.
        """
        with self._lock:
            self._frame = frame.copy()

    def get_frame(self) -> npt.NDArray[np.uint8] | None:
        """Get a copy of the latest camera frame.

        Returns:
            Copy of the latest frame, or None if no frame has been captured.
        """
        with self._lock:
            if self._frame is None:
                return None
            return self._frame.copy()

    def add_result(self, result: AnalysisResult) -> None:
        """Add an analysis result to state and history.

        Args:
            result: The analysis result to store.
        """
        with self._lock:
            self._latest_result = result
            self._history.append(result)

    def get_latest_result(self) -> AnalysisResult | None:
        """Get the most recent analysis result.

        Returns:
            The latest AnalysisResult, or None if no analysis has been performed.
        """
        with self._lock:
            return self._latest_result

    def get_history(self, limit: int = 0) -> list[AnalysisResult]:
        """Get analysis history, most recent first.

        Args:
            limit: Maximum number of results to return (0 for all).

        Returns:
            List of AnalysisResult in reverse chronological order.
        """
        with self._lock:
            items = list(reversed(self._history))
            if limit > 0:
                return items[:limit]
            return items
