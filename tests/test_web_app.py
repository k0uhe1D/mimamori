"""Tests for web dashboard."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from src.analyzer.models import AnalysisResult
from src.config.runtime_config import RuntimeConfig
from src.core.state import MonitoringState
from src.web.app import create_app


def _make_app() -> tuple[TestClient, MonitoringState, RuntimeConfig]:
    """Create a test app with fresh state."""
    state = MonitoringState()
    runtime_config = RuntimeConfig(analysis_interval_seconds=30)
    app = create_app(state=state, runtime_config=runtime_config)
    client = TestClient(app)
    return client, state, runtime_config


def _make_app_with_controls() -> tuple[
    TestClient, MonitoringState, RuntimeConfig, MagicMock, MagicMock
]:
    """Create a test app with camera swap and stream control."""
    state = MonitoringState()
    runtime_config = RuntimeConfig(analysis_interval_seconds=30)
    swap_fn = MagicMock()
    grabber = MagicMock()
    grabber.running = True
    app = create_app(
        state=state,
        runtime_config=runtime_config,
        swap_camera_fn=swap_fn,
        grabber=grabber,
    )
    client = TestClient(app)
    return client, state, runtime_config, swap_fn, grabber


class TestDashboard:
    """Tests for the dashboard page."""

    def test_dashboard_returns_html(self) -> None:
        """GET / returns HTML page."""
        client, _, _ = _make_app()
        response = client.get("/")
        assert response.status_code == 200
        assert "mimamori" in response.text


class TestApiStatus:
    """Tests for /api/status endpoint."""

    def test_status_no_result(self) -> None:
        """GET /api/status returns has_result=false when no analysis yet."""
        client, _, _ = _make_app()
        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert data["has_result"] is False

    def test_status_with_result(self) -> None:
        """GET /api/status returns latest result."""
        client, state, _ = _make_app()
        result = AnalysisResult.create_now(
            posture="仰向け",
            sleep_state="睡眠中",
            summary="正常",
            confidence="high",
            raw_response="{}",
        )
        state.add_result(result)

        response = client.get("/api/status")
        data = response.json()
        assert data["has_result"] is True
        assert data["posture"] == "仰向け"
        assert data["sleep_state"] == "睡眠中"


class TestApiHistory:
    """Tests for /api/history endpoint."""

    def test_history_empty(self) -> None:
        """GET /api/history returns empty list initially."""
        client, _, _ = _make_app()
        response = client.get("/api/history")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []

    def test_history_with_items(self) -> None:
        """GET /api/history returns past results."""
        client, state, _ = _make_app()
        for i in range(3):
            state.add_result(
                AnalysisResult.create_now(
                    posture=f"posture-{i}",
                    sleep_state="睡眠中",
                    summary="ok",
                    confidence="high",
                    raw_response="{}",
                )
            )

        response = client.get("/api/history")
        data = response.json()
        assert len(data["items"]) == 3


class TestApiSettings:
    """Tests for POST /api/settings endpoint."""

    def test_update_interval(self) -> None:
        """POST /api/settings updates analysis interval."""
        client, _, runtime_config = _make_app()
        response = client.post(
            "/api/settings",
            json={"analysis_interval_seconds": 60},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["analysis_interval_seconds"] == 60
        assert runtime_config.analysis_interval_seconds == 60

    def test_update_camera_url(self) -> None:
        """POST /api/settings updates camera URL."""
        client, _, runtime_config = _make_app()
        response = client.post(
            "/api/settings",
            json={"camera_url": "rtsp://new/stream"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["camera_url"] == "rtsp://new/stream"
        assert runtime_config.camera_url == "rtsp://new/stream"


class TestApiCameraSwap:
    """Tests for POST /api/camera/swap endpoint."""

    def test_swap_camera_by_url(self) -> None:
        """POST /api/camera/swap with URL calls swap_camera_fn."""
        client, _, runtime_config, swap_fn, _ = _make_app_with_controls()
        response = client.post(
            "/api/camera/swap",
            json={"camera_url": "rtsp://192.168.1.100:8554/video"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["camera_url"] == "rtsp://192.168.1.100:8554/video"
        swap_fn.assert_called_once_with("rtsp://192.168.1.100:8554/video", 0)
        assert runtime_config.camera_url == "rtsp://192.168.1.100:8554/video"

    def test_swap_camera_by_device_index(self) -> None:
        """POST /api/camera/swap with device index calls swap_camera_fn."""
        client, _, runtime_config, swap_fn, _ = _make_app_with_controls()
        response = client.post(
            "/api/camera/swap",
            json={"camera_device_index": 1},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["camera_device_index"] == 1
        swap_fn.assert_called_once_with("", 1)
        assert runtime_config.camera_device_index == 1

    def test_swap_camera_not_available(self) -> None:
        """POST /api/camera/swap returns error when no swap_camera_fn."""
        client, _, _ = _make_app()
        response = client.post(
            "/api/camera/swap",
            json={"camera_device_index": 1},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert data["message"] == "Camera swap not available"

    def test_swap_camera_failure(self) -> None:
        """POST /api/camera/swap handles exceptions from swap_camera_fn."""
        client, _, _, swap_fn, _ = _make_app_with_controls()
        swap_fn.side_effect = RuntimeError("Camera not found")
        response = client.post(
            "/api/camera/swap",
            json={"camera_device_index": 99},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert data["message"] == "Failed to swap camera"


class TestApiStreamControl:
    """Tests for POST /api/stream/stop and /api/stream/start endpoints."""

    def test_stream_stop(self) -> None:
        """POST /api/stream/stop stops the grabber."""
        client, _, _, _, grabber = _make_app_with_controls()
        response = client.post("/api/stream/stop")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["running"] is False
        grabber.stop.assert_called_once()

    def test_stream_start(self) -> None:
        """POST /api/stream/start starts the grabber."""
        client, _, _, _, grabber = _make_app_with_controls()
        grabber.running = False
        response = client.post("/api/stream/start")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["running"] is True
        grabber.start.assert_called_once()

    def test_stream_start_already_running(self) -> None:
        """POST /api/stream/start returns ok when already running."""
        client, _, _, _, grabber = _make_app_with_controls()
        grabber.running = True
        response = client.post("/api/stream/start")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["message"] == "Stream already running"
        grabber.start.assert_not_called()

    def test_stream_control_not_available(self) -> None:
        """Stream control returns error when no grabber provided."""
        client, _, _ = _make_app()
        response = client.post("/api/stream/stop")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert data["message"] == "Stream control not available"
