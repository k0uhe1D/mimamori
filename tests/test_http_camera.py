"""Tests for HTTPCamera."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.capture.http_camera import HTTPCamera


class TestHTTPCamera:
    """Tests for HTTPCamera."""

    @patch("src.capture.http_camera.cv2.VideoCapture")
    def test_init_success(self, mock_cap_cls: MagicMock) -> None:
        """HTTPCamera opens VideoCapture with the shot URL."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap_cls.return_value = mock_cap

        camera = HTTPCamera(shot_url="http://192.168.1.1:8080/shot.jpg")
        mock_cap_cls.assert_called_once_with("http://192.168.1.1:8080/shot.jpg")
        assert camera is not None

    @patch("src.capture.http_camera.cv2.VideoCapture")
    def test_init_failure_raises(self, mock_cap_cls: MagicMock) -> None:
        """HTTPCamera raises RuntimeError when connection fails."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_cap_cls.return_value = mock_cap

        with pytest.raises(RuntimeError, match="Failed to open HTTP camera"):
            HTTPCamera(shot_url="http://bad-host/shot.jpg")

    @patch("src.capture.http_camera.cv2.VideoCapture")
    def test_read_frame_success(self, mock_cap_cls: MagicMock) -> None:
        """HTTPCamera.read_frame() returns a frame."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_cap.read.return_value = (True, frame)
        mock_cap_cls.return_value = mock_cap

        camera = HTTPCamera(shot_url="http://192.168.1.1:8080/shot.jpg")
        result = camera.read_frame()
        assert result is not None
        assert result.shape == (480, 640, 3)

    @patch("src.capture.http_camera.cv2.VideoCapture")
    def test_read_frame_failure_returns_none(self, mock_cap_cls: MagicMock) -> None:
        """HTTPCamera.read_frame() returns None on fetch failure."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (False, None)
        mock_cap_cls.return_value = mock_cap

        camera = HTTPCamera(shot_url="http://192.168.1.1:8080/shot.jpg")
        result = camera.read_frame()
        assert result is None

    @patch("src.capture.http_camera.cv2.VideoCapture")
    def test_release(self, mock_cap_cls: MagicMock) -> None:
        """HTTPCamera.release() releases the VideoCapture."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap_cls.return_value = mock_cap

        camera = HTTPCamera(shot_url="http://192.168.1.1:8080/shot.jpg")
        camera.release()
        mock_cap.release.assert_called_once()
