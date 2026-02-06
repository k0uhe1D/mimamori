"""Frame grabber daemon thread for mimamori."""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.capture.camera import CameraProtocol
    from src.core.state import MonitoringState

logger = logging.getLogger(__name__)

_TARGET_FPS = 30
_FRAME_INTERVAL = 1.0 / _TARGET_FPS


class FrameGrabber:
    """Daemon thread that continuously grabs frames from a camera.

    Frames are written to a MonitoringState instance for consumption
    by the analyzer and web server.
    """

    def __init__(
        self,
        camera: CameraProtocol,
        state: MonitoringState,
    ) -> None:
        """Initialize frame grabber.

        Args:
            camera: Camera instance implementing CameraProtocol.
            state: Shared monitoring state to write frames to.
        """
        self._camera = camera
        self._state = state
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the frame grabber daemon thread."""
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="frame-grabber",
            daemon=True,
        )
        self._thread.start()
        logger.info("FrameGrabber started")

    def stop(self) -> None:
        """Stop the frame grabber and wait for thread to finish."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        logger.info("FrameGrabber stopped")

    def _run(self) -> None:
        """Frame grabbing loop."""
        while not self._stop_event.is_set():
            frame = self._camera.read_frame()
            if frame is not None:
                self._state.update_frame(frame)
            self._stop_event.wait(timeout=_FRAME_INTERVAL)
