"""Tests for camera factory helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.capture.factory import build_http_snapshot_url, create_camera


class TestBuildHttpSnapshotUrl:
    """Tests for HTTP snapshot URL normalization."""

    def test_appends_snapshot_path_when_base_url(self) -> None:
        """Base URL gets default snapshot path."""
        assert (
            build_http_snapshot_url("http://192.168.1.10:8080")
            == "http://192.168.1.10:8080/shot.jpg"
        )

    def test_keeps_existing_path_as_full_endpoint(self) -> None:
        """URL with path is treated as full endpoint."""
        assert (
            build_http_snapshot_url("http://192.168.1.10:8080/photo.jpg")
            == "http://192.168.1.10:8080/photo.jpg"
        )

    def test_accepts_custom_snapshot_path_without_leading_slash(self) -> None:
        """Custom snapshot path is normalized with leading slash."""
        assert (
            build_http_snapshot_url(
                "http://192.168.1.10:8080",
                snapshot_path="photoaf.jpg",
            )
            == "http://192.168.1.10:8080/photoaf.jpg"
        )


class TestCreateCamera:
    """Tests for create_camera dispatcher."""

    @patch("src.capture.factory.HTTPCamera")
    def test_http_camera_from_base_url(self, mock_http_camera: MagicMock) -> None:
        """HTTP URL builds snapshot endpoint and returns HTTPCamera."""
        obj = MagicMock()
        mock_http_camera.return_value = obj

        camera = create_camera(
            camera_url="http://192.168.1.10:8080",
            device_index=0,
            width=640,
            height=480,
            http_snapshot_path="/shot.jpg",
        )

        assert camera is obj
        mock_http_camera.assert_called_once_with(
            shot_url="http://192.168.1.10:8080/shot.jpg"
        )

    @patch("src.capture.factory.HTTPCamera")
    def test_http_camera_with_full_snapshot_url(
        self,
        mock_http_camera: MagicMock,
    ) -> None:
        """HTTP URL with path is used as-is."""
        obj = MagicMock()
        mock_http_camera.return_value = obj

        camera = create_camera(
            camera_url="http://192.168.1.10:8080/photo.jpg",
            device_index=0,
            width=640,
            height=480,
        )

        assert camera is obj
        mock_http_camera.assert_called_once_with(
            shot_url="http://192.168.1.10:8080/photo.jpg"
        )

    @patch("src.capture.factory.RTSPCamera")
    def test_rtsp_camera(self, mock_rtsp_camera: MagicMock) -> None:
        """RTSP URL returns RTSPCamera."""
        obj = MagicMock()
        mock_rtsp_camera.return_value = obj

        camera = create_camera(
            camera_url="rtsp://example.com/stream",
            device_index=0,
            width=640,
            height=480,
        )

        assert camera is obj
        mock_rtsp_camera.assert_called_once_with(url="rtsp://example.com/stream")

    @patch("src.capture.factory.OpenCVCamera")
    def test_local_camera(self, mock_local_camera: MagicMock) -> None:
        """Empty URL returns OpenCVCamera."""
        obj = MagicMock()
        mock_local_camera.return_value = obj

        camera = create_camera(
            camera_url="",
            device_index=2,
            width=1280,
            height=720,
        )

        assert camera is obj
        mock_local_camera.assert_called_once_with(
            device_index=2,
            width=1280,
            height=720,
        )
