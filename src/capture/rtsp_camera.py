"""RTSP camera capture for mimamori."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any, cast

import cv2

if TYPE_CHECKING:
    import numpy as np
    import numpy.typing as npt

logger = logging.getLogger(__name__)

_MAX_RECONNECT_ATTEMPTS = 5
_INITIAL_BACKOFF_SECONDS = 1.0


class RTSPCamera:
    """Camera implementation using OpenCV VideoCapture with RTSP URL.

    Connects to an IP camera (e.g. Iriun Webcam) via RTSP stream.
    Supports automatic reconnection with exponential backoff.
    """

    def __init__(self, url: str) -> None:
        """Initialize RTSP camera capture.

        Args:
            url: RTSP stream URL (e.g. rtsp://192.168.1.100:8554/video).

        Raises:
            RuntimeError: If initial connection to the RTSP stream fails.
        """
        self._url = url
        self._cap = self._connect()

    def _connect(self) -> cv2.VideoCapture:
        """Create and configure a VideoCapture for the RTSP URL.

        Returns:
            Opened VideoCapture instance.

        Raises:
            RuntimeError: If the stream cannot be opened.
        """
        cap = cv2.VideoCapture(self._url)
        if not cap.isOpened():
            msg = f"Failed to open RTSP stream: {self._url}"
            raise RuntimeError(msg)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap

    def _reconnect(self) -> bool:
        """Attempt to reconnect with exponential backoff.

        Returns:
            True if reconnection succeeded, False after all attempts exhausted.
        """
        backoff = _INITIAL_BACKOFF_SECONDS
        for attempt in range(1, _MAX_RECONNECT_ATTEMPTS + 1):
            logger.warning(
                "RTSP reconnect attempt %d/%d (backoff %.1fs)",
                attempt,
                _MAX_RECONNECT_ATTEMPTS,
                backoff,
            )
            time.sleep(backoff)
            try:
                self._cap.release()
                self._cap = self._connect()
            except RuntimeError:
                backoff *= 2
                continue
            logger.info("RTSP reconnected on attempt %d", attempt)
            return True
        return False

    def read_frame(self) -> npt.NDArray[np.uint8] | None:
        """Capture a single frame from the RTSP stream.

        If the read fails, attempts automatic reconnection.

        Returns:
            BGR image as numpy array, or None if capture failed.
        """
        ret: bool
        frame: Any
        ret, frame = self._cap.read()
        if ret:
            return cast("npt.NDArray[np.uint8]", frame)

        logger.warning("RTSP frame read failed, attempting reconnect")
        if self._reconnect():
            ret, frame = self._cap.read()
            if ret:
                return cast("npt.NDArray[np.uint8]", frame)
        return None

    def release(self) -> None:
        """Release camera resources."""
        self._cap.release()
