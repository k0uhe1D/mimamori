"""Runtime-mutable configuration for mimamori."""

from __future__ import annotations

import threading


class RuntimeConfig:
    """Thread-safe runtime configuration that can be updated while running.

    Unlike Settings (frozen dataclass), RuntimeConfig allows modifying
    values at runtime, protected by a threading lock.
    """

    def __init__(
        self,
        analysis_interval_seconds: int = 30,
        camera_url: str = "",
        camera_device_index: int = 0,
    ) -> None:
        """Initialize runtime configuration.

        Args:
            analysis_interval_seconds: Interval between LLM analyses.
            camera_url: RTSP camera URL (empty string for local device).
            camera_device_index: Local camera device index.
        """
        self._lock = threading.Lock()
        self._analysis_interval_seconds = analysis_interval_seconds
        self._camera_url = camera_url
        self._camera_device_index = camera_device_index

    @property
    def analysis_interval_seconds(self) -> int:
        """Get the analysis interval in seconds."""
        with self._lock:
            return self._analysis_interval_seconds

    @analysis_interval_seconds.setter
    def analysis_interval_seconds(self, value: int) -> None:
        """Set the analysis interval in seconds."""
        with self._lock:
            self._analysis_interval_seconds = value

    @property
    def camera_url(self) -> str:
        """Get the camera URL."""
        with self._lock:
            return self._camera_url

    @camera_url.setter
    def camera_url(self, value: str) -> None:
        """Set the camera URL."""
        with self._lock:
            self._camera_url = value

    @property
    def camera_device_index(self) -> int:
        """Get the camera device index."""
        with self._lock:
            return self._camera_device_index

    @camera_device_index.setter
    def camera_device_index(self, value: int) -> None:
        """Set the camera device index."""
        with self._lock:
            self._camera_device_index = value
