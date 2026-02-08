"""Tests for web dashboard."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from src.analyzer.models import AnalysisResult
from src.config.runtime_config import RuntimeConfig
from src.config.settings import Settings
from src.core.state import MonitoringState
from src.web.app import create_app


def _make_app() -> tuple[TestClient, MonitoringState, RuntimeConfig]:
    """Create a test app with fresh state."""
    state = MonitoringState()
    runtime_config = RuntimeConfig(analysis_interval_seconds=30)
    app = create_app(state=state, runtime_config=runtime_config)
    client = TestClient(app)
    return client, state, runtime_config


def _make_app_with_settings() -> tuple[TestClient, MonitoringState, RuntimeConfig]:
    """Create a test app with Settings for API key availability."""
    state = MonitoringState()
    runtime_config = RuntimeConfig(
        analysis_interval_seconds=5,
        llm_provider="gemini",
        llm_model="gemini-2.5-flash",
    )
    settings = Settings(
        openai_api_key="test-openai-key",
        gemini_api_key="test-gemini-key",
    )
    app = create_app(state=state, runtime_config=runtime_config, settings=settings)
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

    def test_update_llm_settings(self) -> None:
        """POST /api/settings updates LLM provider and model."""
        client, _, runtime_config = _make_app()
        response = client.post(
            "/api/settings",
            json={"llm_provider": "gemini", "llm_model": "gemini-2.5-flash"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["llm_provider"] == "gemini"
        assert data["llm_model"] == "gemini-2.5-flash"
        assert runtime_config.llm_provider == "gemini"
        assert runtime_config.llm_model == "gemini-2.5-flash"

    def test_update_capture_dimensions(self) -> None:
        """POST /api/settings updates capture dimensions."""
        client, _, runtime_config = _make_app()
        response = client.post(
            "/api/settings",
            json={"capture_width": 1280, "capture_height": 720},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["capture_width"] == 1280
        assert data["capture_height"] == 720
        assert runtime_config.capture_width == 1280
        assert runtime_config.capture_height == 720


class TestApiGetSettings:
    """Tests for GET /api/settings endpoint."""

    def test_get_settings_defaults(self) -> None:
        """GET /api/settings returns current runtime config values."""
        client, _, _ = _make_app()
        response = client.get("/api/settings")
        assert response.status_code == 200
        data = response.json()
        assert data["analysis_interval_seconds"] == 30
        assert data["camera_url"] == ""
        assert data["camera_device_index"] == 0
        assert data["llm_provider"] == "openai"
        assert data["llm_model"] == "gpt-4o"
        assert data["capture_width"] == 640
        assert data["capture_height"] == 480
        assert data["openai_available"] is False
        assert data["gemini_available"] is False

    def test_get_settings_with_api_keys(self) -> None:
        """GET /api/settings shows provider availability from Settings."""
        client, _, _ = _make_app_with_settings()
        response = client.get("/api/settings")
        assert response.status_code == 200
        data = response.json()
        assert data["openai_available"] is True
        assert data["gemini_available"] is True
        assert data["llm_provider"] == "gemini"
        assert data["llm_model"] == "gemini-2.5-flash"


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


class TestApiAnalysisControl:
    """Tests for POST /api/analysis/pause and /api/analysis/resume endpoints."""

    def test_analysis_pause(self) -> None:
        """POST /api/analysis/pause pauses the worker."""
        state = MonitoringState()
        runtime_config = RuntimeConfig()
        worker_mock = MagicMock()
        app = create_app(state=state, runtime_config=runtime_config, worker=worker_mock)
        client = TestClient(app)
        response = client.post("/api/analysis/pause")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["paused"] is True
        worker_mock.pause.assert_called_once()

    def test_analysis_resume(self) -> None:
        """POST /api/analysis/resume resumes the worker."""
        state = MonitoringState()
        runtime_config = RuntimeConfig()
        worker_mock = MagicMock()
        app = create_app(state=state, runtime_config=runtime_config, worker=worker_mock)
        client = TestClient(app)
        response = client.post("/api/analysis/resume")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["paused"] is False
        worker_mock.resume.assert_called_once()

    def test_analysis_control_not_available(self) -> None:
        """Analysis control returns error when no worker provided."""
        client, _, _ = _make_app()
        response = client.post("/api/analysis/pause")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert data["message"] == "Analysis control not available"


class TestApiRecordingControl:
    """Tests for POST /api/recording/start and /api/recording/stop."""

    def test_recording_start(self) -> None:
        """POST /api/recording/start starts recording."""
        state = MonitoringState()
        runtime_config = RuntimeConfig()
        recorder_mock = MagicMock()
        recorder_mock.recording = False
        recorder_mock.start.return_value = "/tmp/test.mp4"
        app = create_app(
            state=state, runtime_config=runtime_config, recorder=recorder_mock
        )
        client = TestClient(app)
        response = client.post("/api/recording/start")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["recording"] is True
        assert data["file"] == "/tmp/test.mp4"
        recorder_mock.start.assert_called_once()

    def test_recording_stop(self) -> None:
        """POST /api/recording/stop stops recording."""
        state = MonitoringState()
        runtime_config = RuntimeConfig()
        recorder_mock = MagicMock()
        recorder_mock.recording = True
        recorder_mock.stop.return_value = "/tmp/test.mp4"
        app = create_app(
            state=state, runtime_config=runtime_config, recorder=recorder_mock
        )
        client = TestClient(app)
        response = client.post("/api/recording/stop")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["recording"] is False
        recorder_mock.stop.assert_called_once()

    def test_recording_not_available(self) -> None:
        """Recording control returns error when no recorder provided."""
        client, _, _ = _make_app()
        response = client.post("/api/recording/start")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert data["message"] == "Recording not available"


class TestApiIPWebcam:
    """Tests for IP Webcam proxy endpoints."""

    def test_control_not_configured(self) -> None:
        """POST /api/ipwebcam/control returns error when camera is not HTTP."""
        client, _, _ = _make_app()
        response = client.post("/api/ipwebcam/control", json={"path": "/enabletorch"})
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert data["message"] == "IP Webcam not configured"

    def test_control_disallowed_path(self) -> None:
        """POST /api/ipwebcam/control rejects disallowed paths."""
        client, _, runtime_config = _make_app()
        runtime_config.camera_url = "http://192.168.1.1:8080"
        response = client.post("/api/ipwebcam/control", json={"path": "/admin/delete"})
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert data["message"] == "Command not allowed"

    def test_control_allowed_paths(self) -> None:
        """Allowed paths pass the whitelist check."""
        from src.web.app import _is_allowed_ipwebcam_path

        assert _is_allowed_ipwebcam_path("/enabletorch") is True
        assert _is_allowed_ipwebcam_path("/disabletorch") is True
        assert _is_allowed_ipwebcam_path("/focus") is True
        assert _is_allowed_ipwebcam_path("/settings/night_vision?set=on") is True
        assert _is_allowed_ipwebcam_path("/ptz?zoom=150") is True
        assert _is_allowed_ipwebcam_path("/admin") is False

    def test_status_not_configured(self) -> None:
        """GET /api/ipwebcam/status returns ok=false when not HTTP camera."""
        client, _, _ = _make_app()
        response = client.get("/api/ipwebcam/status")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False


class TestApiSleepStatus:
    """Tests for GET /api/sleep/status endpoint."""

    def test_sleep_status_no_tracker(self) -> None:
        """GET /api/sleep/status returns not sleeping when no tracker."""
        client, _, _ = _make_app()
        response = client.get("/api/sleep/status")
        assert response.status_code == 200
        data = response.json()
        assert data["is_sleeping"] is False
        assert data["current_session"] is None

    def test_sleep_status_not_sleeping(self) -> None:
        """GET /api/sleep/status returns not sleeping when tracker has no session."""
        state = MonitoringState()
        runtime_config = RuntimeConfig()
        tracker_mock = MagicMock()
        tracker_mock.active_session = None
        app = create_app(
            state=state, runtime_config=runtime_config, sleep_tracker=tracker_mock
        )
        client = TestClient(app)
        response = client.get("/api/sleep/status")
        assert response.status_code == 200
        data = response.json()
        assert data["is_sleeping"] is False

    def test_sleep_status_sleeping(self) -> None:
        """GET /api/sleep/status returns current session when sleeping."""
        from datetime import UTC, datetime

        from src.core.sleep_session import SleepSession

        state = MonitoringState()
        runtime_config = RuntimeConfig()
        session = SleepSession(
            start_time=datetime(2025, 6, 1, 22, 0, 0, tzinfo=UTC),
            snapshot_paths=["/tmp/snap1.jpg", "/tmp/snap2.jpg"],
        )
        tracker_mock = MagicMock()
        tracker_mock.active_session = session
        app = create_app(
            state=state, runtime_config=runtime_config, sleep_tracker=tracker_mock
        )
        client = TestClient(app)
        response = client.get("/api/sleep/status")
        assert response.status_code == 200
        data = response.json()
        assert data["is_sleeping"] is True
        assert data["current_session"]["is_active"] is True
        assert data["current_session"]["snapshot_count"] == 2


class TestApiSleepHistory:
    """Tests for GET /api/sleep/history endpoint."""

    def test_sleep_history_no_tracker(self) -> None:
        """GET /api/sleep/history returns empty when no tracker."""
        client, _, _ = _make_app()
        response = client.get("/api/sleep/history")
        assert response.status_code == 200
        data = response.json()
        assert data["sessions"] == []
        assert data["total_sleep_seconds"] == 0.0

    def test_sleep_history_with_sessions(self) -> None:
        """GET /api/sleep/history returns session list and total."""
        from datetime import UTC, datetime

        from src.core.sleep_session import SleepSession

        state = MonitoringState()
        runtime_config = RuntimeConfig()
        sessions = [
            SleepSession(
                start_time=datetime(2025, 6, 1, 22, 0, 0, tzinfo=UTC),
                end_time=datetime(2025, 6, 2, 0, 0, 0, tzinfo=UTC),
            ),
            SleepSession(
                start_time=datetime(2025, 6, 2, 2, 0, 0, tzinfo=UTC),
                end_time=datetime(2025, 6, 2, 5, 0, 0, tzinfo=UTC),
            ),
        ]
        tracker_mock = MagicMock()
        tracker_mock.get_sessions.return_value = sessions
        app = create_app(
            state=state, runtime_config=runtime_config, sleep_tracker=tracker_mock
        )
        client = TestClient(app)
        response = client.get("/api/sleep/history")
        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 2
        assert data["total_sleep_seconds"] == 18000.0  # 2h + 3h = 5h

    def test_sleep_history_daily_timelapse_available(self) -> None:
        """GET /api/sleep/history includes daily_timelapse_available field."""
        from datetime import UTC, datetime

        from src.core.sleep_session import SleepSession

        state = MonitoringState()
        runtime_config = RuntimeConfig()
        sessions = [
            SleepSession(
                start_time=datetime(2025, 6, 1, 22, 0, 0, tzinfo=UTC),
                end_time=datetime(2025, 6, 2, 0, 0, 0, tzinfo=UTC),
            ),
        ]
        tracker_mock = MagicMock()
        tracker_mock.get_sessions.return_value = sessions
        tracker_mock.get_daily_timelapse.return_value = "/tmp/daily.gif"
        app = create_app(
            state=state, runtime_config=runtime_config, sleep_tracker=tracker_mock
        )
        client = TestClient(app)
        response = client.get("/api/sleep/history")
        assert response.status_code == 200
        data = response.json()
        assert data["daily_timelapse_available"] is True

    def test_sleep_history_daily_timelapse_not_available(self) -> None:
        """GET /api/sleep/history returns false when no daily timelapse."""
        from datetime import UTC, datetime

        from src.core.sleep_session import SleepSession

        state = MonitoringState()
        runtime_config = RuntimeConfig()
        sessions = [
            SleepSession(
                start_time=datetime(2025, 6, 1, 22, 0, 0, tzinfo=UTC),
                end_time=datetime(2025, 6, 2, 0, 0, 0, tzinfo=UTC),
            ),
        ]
        tracker_mock = MagicMock()
        tracker_mock.get_sessions.return_value = sessions
        tracker_mock.get_daily_timelapse.return_value = None
        app = create_app(
            state=state, runtime_config=runtime_config, sleep_tracker=tracker_mock
        )
        client = TestClient(app)
        response = client.get("/api/sleep/history")
        assert response.status_code == 200
        data = response.json()
        assert data["daily_timelapse_available"] is False


class TestApiSleepTimelapse:
    """Tests for GET /api/sleep/timelapse/{date_str} endpoint."""

    def test_timelapse_no_tracker(self) -> None:
        """Returns 404 when no sleep tracker configured."""
        client, _, _ = _make_app()
        response = client.get("/api/sleep/timelapse/2025-06-01")
        assert response.status_code == 404

    def test_timelapse_not_available(self) -> None:
        """Returns 404 when no daily timelapse exists for the date."""
        state = MonitoringState()
        runtime_config = RuntimeConfig()
        tracker_mock = MagicMock()
        tracker_mock.get_daily_timelapse.return_value = None
        app = create_app(
            state=state, runtime_config=runtime_config, sleep_tracker=tracker_mock
        )
        client = TestClient(app)
        response = client.get("/api/sleep/timelapse/2025-06-01")
        assert response.status_code == 404

    def test_timelapse_served(self, tmp_path: Path) -> None:
        """Returns 200 with GIF content when daily timelapse exists."""
        from PIL import Image

        gif_path = str(tmp_path / "20250601_daily_timelapse.gif")
        img1 = Image.new("RGB", (100, 80), "red")
        img2 = Image.new("RGB", (100, 80), "blue")
        img1.save(gif_path, save_all=True, append_images=[img2], duration=500, loop=0)

        state = MonitoringState()
        runtime_config = RuntimeConfig()
        tracker_mock = MagicMock()
        tracker_mock.get_daily_timelapse.return_value = gif_path
        app = create_app(
            state=state, runtime_config=runtime_config, sleep_tracker=tracker_mock
        )
        client = TestClient(app)
        response = client.get("/api/sleep/timelapse/2025-06-01")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/gif"

    def test_timelapse_invalid_date(self) -> None:
        """Returns 400 for invalid date format."""
        state = MonitoringState()
        runtime_config = RuntimeConfig()
        tracker_mock = MagicMock()
        app = create_app(
            state=state, runtime_config=runtime_config, sleep_tracker=tracker_mock
        )
        client = TestClient(app)
        response = client.get("/api/sleep/timelapse/not-a-date")
        assert response.status_code == 400
