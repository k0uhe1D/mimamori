"""Tests for RTSP camera module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.capture.rtsp_camera import RTSPCamera


class TestRTSPCamera:
    """Tests for RTSPCamera."""

    @patch("src.capture.rtsp_camera.cv2.VideoCapture")
    def test_init_success(self, mock_capture_cls: MagicMock) -> None:
        """RTSPCamera opens stream and sets buffer size."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_capture_cls.return_value = mock_cap

        cam = RTSPCamera("rtsp://example.com/stream")

        mock_capture_cls.assert_called_once_with("rtsp://example.com/stream")
        mock_cap.set.assert_called_once()
        cam.release()

    @patch("src.capture.rtsp_camera.cv2.VideoCapture")
    def test_init_failure_raises(self, mock_capture_cls: MagicMock) -> None:
        """RTSPCamera raises RuntimeError when stream cannot be opened."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_capture_cls.return_value = mock_cap

        with pytest.raises(RuntimeError, match="Failed to open RTSP stream"):
            RTSPCamera("rtsp://bad-url/stream")

    @patch("src.capture.rtsp_camera.cv2.VideoCapture")
    def test_read_frame_success(self, mock_capture_cls: MagicMock) -> None:
        """read_frame returns frame on success."""
        import numpy as np

        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        fake_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_cap.read.return_value = (True, fake_frame)
        mock_capture_cls.return_value = mock_cap

        cam = RTSPCamera("rtsp://example.com/stream")
        frame = cam.read_frame()

        assert frame is not None
        assert frame.shape == (480, 640, 3)
        cam.release()

    @patch("src.capture.rtsp_camera.time.sleep")
    @patch("src.capture.rtsp_camera.cv2.VideoCapture")
    def test_read_frame_reconnects_on_failure(
        self,
        mock_capture_cls: MagicMock,
        mock_sleep: MagicMock,
    ) -> None:
        """read_frame attempts reconnection when frame read fails."""
        import numpy as np

        mock_cap_initial = MagicMock()
        mock_cap_initial.isOpened.return_value = True
        mock_cap_initial.read.return_value = (False, None)

        mock_cap_reconnected = MagicMock()
        mock_cap_reconnected.isOpened.return_value = True
        fake_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_cap_reconnected.read.return_value = (True, fake_frame)

        mock_capture_cls.side_effect = [
            mock_cap_initial,
            mock_cap_reconnected,
        ]

        cam = RTSPCamera("rtsp://example.com/stream")
        frame = cam.read_frame()

        assert frame is not None
        mock_sleep.assert_called()
        cam.release()

    @patch("src.capture.rtsp_camera.time.sleep")
    @patch("src.capture.rtsp_camera.cv2.VideoCapture")
    def test_read_frame_returns_none_after_max_retries(
        self,
        mock_capture_cls: MagicMock,
        mock_sleep: MagicMock,
    ) -> None:
        """read_frame returns None after exhausting reconnection attempts."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (False, None)

        mock_cap_fail = MagicMock()
        mock_cap_fail.isOpened.return_value = False

        mock_capture_cls.side_effect = [mock_cap] + [mock_cap_fail] * 5

        cam = RTSPCamera("rtsp://example.com/stream")
        frame = cam.read_frame()

        assert frame is None
        assert mock_sleep.call_count == 5
        cam.release()

    @patch("src.capture.rtsp_camera.cv2.VideoCapture")
    def test_release(self, mock_capture_cls: MagicMock) -> None:
        """release() calls underlying capture release."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_capture_cls.return_value = mock_cap

        cam = RTSPCamera("rtsp://example.com/stream")
        cam.release()

        mock_cap.release.assert_called_once()
