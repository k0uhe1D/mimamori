"""Frame encoding utilities for mimamori."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING

import cv2

if TYPE_CHECKING:
    import numpy as np
    import numpy.typing as npt


def encode_frame_to_base64(
    frame: npt.NDArray[np.uint8],
    quality: int = 85,
) -> str:
    """Encode a BGR frame to base64-encoded JPEG string.

    Args:
        frame: BGR image as numpy array.
        quality: JPEG compression quality (0-100).

    Returns:
        Base64-encoded JPEG string.

    Raises:
        ValueError: If frame encoding fails.
    """
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
    success, buffer = cv2.imencode(".jpg", frame, encode_params)
    if not success:
        msg = "Failed to encode frame to JPEG"
        raise ValueError(msg)
    return base64.b64encode(buffer.tobytes()).decode("utf-8")
