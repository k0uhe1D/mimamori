"""Camera capture module for mimamori."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, cast

import cv2

if TYPE_CHECKING:
    import numpy as np
    import numpy.typing as npt


class CameraProtocol(Protocol):
    """Protocol defining the camera interface for capture operations."""

    def read_frame(self) -> npt.NDArray[np.uint8] | None:
        """Capture a single frame from the camera."""
        ...

    def release(self) -> None:
        """Release camera resources."""
        ...


class OpenCVCamera:
    """Camera implementation using OpenCV VideoCapture.

    Works with Mac built-in camera (device_index=0) and
    Iriun Webcam (/dev/video* on Raspberry Pi).
    """

    def __init__(
        self,
        device_index: int = 0,
        width: int = 640,
        height: int = 480,
    ) -> None:
        """Initialize camera capture.

        Args:
            device_index: Camera device index (0 for default).
            width: Requested capture width in pixels.
            height: Requested capture height in pixels.

        Raises:
            RuntimeError: If camera cannot be opened.
        """
        self._cap = cv2.VideoCapture(device_index)
        if not self._cap.isOpened():
            msg = f"Failed to open camera at device index {device_index}"
            raise RuntimeError(msg)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    def read_frame(self) -> npt.NDArray[np.uint8] | None:
        """Capture a single frame from the camera.

        Returns:
            BGR image as numpy array, or None if capture failed.
        """
        ret: bool
        frame: Any
        ret, frame = self._cap.read()
        if not ret:
            return None
        return cast("npt.NDArray[np.uint8]", frame)

    def release(self) -> None:
        """Release camera resources."""
        self._cap.release()
