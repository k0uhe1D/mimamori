"""Tests for web dashboard."""

from __future__ import annotations

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
