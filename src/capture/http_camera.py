"""HTTP snapshot camera for IP Webcam and similar apps."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import cv2

if TYPE_CHECKING:
    import numpy as np
    import numpy.typing as npt

logger = logging.getLogger(__name__)


class HTTPCamera:
    """Camera implementation that fetches JPEG snapshots via HTTP.

    Works with IP Webcam's /shot.jpg endpoint and any HTTP endpoint
    that returns a JPEG image. Zero buffering — each read_frame()
    fetches the current frame.
    """

    def __init__(self, shot_url: str) -> None:
        """Initialize HTTP camera.

        Args:
            shot_url: Full URL to the JPEG snapshot endpoint
                      (e.g. "http://192.168.3.77:8080/shot.jpg").

        Raises:
            RuntimeError: If the first snapshot fetch fails.
        """
        self._shot_url = shot_url
        self._cap = cv2.VideoCapture(shot_url)
        if not self._cap.isOpened():
            msg = f"Failed to open HTTP camera at {shot_url}"
            raise RuntimeError(msg)
        logger.info("HTTPCamera connected: %s", shot_url)

    def read_frame(self) -> npt.NDArray[np.uint8] | None:
        """Fetch the current frame via HTTP.

        Returns:
            BGR image as numpy array, or None if fetch failed.
        """
        self._cap.open(self._shot_url)
        ret, frame = self._cap.read()
        if not ret:
            logger.debug("Failed to fetch frame from %s", self._shot_url)
            return None
        return frame  # type: ignore[return-value]

    def release(self) -> None:
        """Release resources."""
        self._cap.release()
