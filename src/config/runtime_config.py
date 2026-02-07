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
        llm_provider: str = "openai",
        llm_model: str = "gpt-4o",
        capture_width: int = 640,
        capture_height: int = 480,
        max_skip_seconds: int = 300,
    ) -> None:
        """Initialize runtime configuration.

        Args:
            analysis_interval_seconds: Interval between LLM analyses.
            camera_url: RTSP camera URL (empty string for local device).
            camera_device_index: Local camera device index.
            llm_provider: LLM provider ("openai" or "gemini").
            llm_model: LLM model name.
            capture_width: Capture width in pixels.
            capture_height: Capture height in pixels.
            max_skip_seconds: Max seconds to skip analysis for unchanged frames.
                Set to 0 to disable forced analysis.
        """
        self._lock = threading.Lock()
        self._analysis_interval_seconds = analysis_interval_seconds
        self._camera_url = camera_url
        self._camera_device_index = camera_device_index
        self._llm_provider = llm_provider
        self._llm_model = llm_model
        self._capture_width = capture_width
        self._capture_height = capture_height
        self._max_skip_seconds = max_skip_seconds

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

    @property
    def llm_provider(self) -> str:
        """Get the LLM provider."""
        with self._lock:
            return self._llm_provider

    @llm_provider.setter
    def llm_provider(self, value: str) -> None:
        """Set the LLM provider."""
        with self._lock:
            self._llm_provider = value

    @property
    def llm_model(self) -> str:
        """Get the LLM model name."""
        with self._lock:
            return self._llm_model

    @llm_model.setter
    def llm_model(self, value: str) -> None:
        """Set the LLM model name."""
        with self._lock:
            self._llm_model = value

    @property
    def capture_width(self) -> int:
        """Get the capture width in pixels."""
        with self._lock:
            return self._capture_width

    @capture_width.setter
    def capture_width(self, value: int) -> None:
        """Set the capture width in pixels."""
        with self._lock:
            self._capture_width = value

    @property
    def capture_height(self) -> int:
        """Get the capture height in pixels."""
        with self._lock:
            return self._capture_height

    @capture_height.setter
    def capture_height(self, value: int) -> None:
        """Set the capture height in pixels."""
        with self._lock:
            self._capture_height = value

    @property
    def max_skip_seconds(self) -> int:
        """Get the max seconds to skip analysis for unchanged frames."""
        with self._lock:
            return self._max_skip_seconds

    @max_skip_seconds.setter
    def max_skip_seconds(self, value: int) -> None:
        """Set the max seconds to skip analysis for unchanged frames."""
        with self._lock:
            self._max_skip_seconds = value
