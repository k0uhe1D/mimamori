"""FastAPI application for mimamori web dashboard."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import cv2
from fastapi import FastAPI
from fastapi.requests import Request  # noqa: TC002
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from src.web.schemas import (
    HistoryItem,
    HistoryResponse,
    SettingsUpdateRequest,
    SettingsUpdateResponse,
    StatusResponse,
)

if TYPE_CHECKING:
    from collections.abc import Generator

    from src.config.runtime_config import RuntimeConfig
    from src.core.state import MonitoringState

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def create_app(
    state: MonitoringState,
    runtime_config: RuntimeConfig,
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        state: Shared monitoring state.
        runtime_config: Runtime-mutable configuration.

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(title="mimamori", docs_url=None, redoc_url=None)
    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request) -> HTMLResponse:
        """Render the main dashboard page."""
        return templates.TemplateResponse(request, "index.html")

    @app.get("/stream")
    async def video_stream() -> StreamingResponse:
        """MJPEG video stream of the latest camera frame."""
        return StreamingResponse(
            _generate_frames(state),
            media_type="multipart/x-mixed-replace; boundary=frame",
        )

    @app.get("/api/status")
    async def api_status() -> StatusResponse:
        """Get the latest analysis result."""
        result = state.get_latest_result()
        if result is None:
            return StatusResponse(has_result=False)
        return StatusResponse(
            has_result=True,
            timestamp=result.timestamp,
            posture=result.posture,
            sleep_state=result.sleep_state,
            summary=result.summary,
            confidence=result.confidence,
            anomalies=result.anomalies,
        )

    @app.get("/api/history")
    async def api_history() -> HistoryResponse:
        """Get analysis history."""
        history = state.get_history(limit=50)
        items = [
            HistoryItem(
                timestamp=r.timestamp,
                posture=r.posture,
                sleep_state=r.sleep_state,
                summary=r.summary,
                confidence=r.confidence,
                anomalies=r.anomalies,
            )
            for r in history
        ]
        return HistoryResponse(items=items)

    @app.post("/api/settings")
    async def api_update_settings(
        body: SettingsUpdateRequest,
    ) -> SettingsUpdateResponse:
        """Update runtime settings."""
        if body.analysis_interval_seconds is not None:
            runtime_config.analysis_interval_seconds = body.analysis_interval_seconds
            logger.info(
                "Updated analysis_interval_seconds to %d",
                body.analysis_interval_seconds,
            )
        if body.camera_url is not None:
            runtime_config.camera_url = body.camera_url
            logger.info("Updated camera_url to %s", body.camera_url)
        return SettingsUpdateResponse(
            analysis_interval_seconds=runtime_config.analysis_interval_seconds,
            camera_url=runtime_config.camera_url,
        )

    return app


def _generate_frames(
    state: MonitoringState,
) -> Generator[bytes, None, None]:
    """Generate MJPEG frames from monitoring state.

    Yields:
        MJPEG frame bytes with boundary markers.
    """
    import time

    while True:
        frame = state.get_frame()
        if frame is not None:
            success, buffer = cv2.imencode(".jpg", frame)
            if success:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
                )
        time.sleep(0.033)  # ~30fps
