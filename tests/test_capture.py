"""Tests for capture module."""

from __future__ import annotations

import base64
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.capture import OpenCVCamera, encode_frame_to_base64


class TestOpenCVCamera:
    """Tests for OpenCVCamera class."""

    @patch("src.capture.camera.cv2.VideoCapture")
    def test_init_success(self, mock_cap_cls: MagicMock) -> None:
        """Camera initializes when device is available."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap_cls.return_value = mock_cap
        camera = OpenCVCamera(device_index=0)
        camera.release()
        mock_cap.release.assert_called_once()

    @patch("src.capture.camera.cv2.VideoCapture")
    def test_init_failure_raises(self, mock_cap_cls: MagicMock) -> None:
        """Camera raises RuntimeError when device unavailable."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_cap_cls.return_value = mock_cap
        with pytest.raises(RuntimeError, match="Failed to open camera"):
            OpenCVCamera(device_index=99)

    @patch("src.capture.camera.cv2.VideoCapture")
    def test_read_frame_success(self, mock_cap_cls: MagicMock) -> None:
        """read_frame returns numpy array on success."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        fake_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_cap.read.return_value = (True, fake_frame)
        mock_cap_cls.return_value = mock_cap
        camera = OpenCVCamera()
        frame = camera.read_frame()
        assert frame is not None
        assert frame.shape == (480, 640, 3)

    @patch("src.capture.camera.cv2.VideoCapture")
    def test_read_frame_failure_returns_none(self, mock_cap_cls: MagicMock) -> None:
        """read_frame returns None on capture failure."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (False, None)
        mock_cap_cls.return_value = mock_cap
        camera = OpenCVCamera()
        assert camera.read_frame() is None


class TestEncodeFrame:
    """Tests for encode_frame_to_base64."""

    def test_encode_returns_valid_base64(self) -> None:
        """Encoding a frame produces valid base64 string."""
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        result = encode_frame_to_base64(frame)
        decoded = base64.b64decode(result)
        # JPEG files start with FF D8
        assert decoded[:2] == b"\xff\xd8"
