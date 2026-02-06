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
    CameraSwapRequest,
    CameraSwapResponse,
    HistoryItem,
    HistoryResponse,
    SettingsGetResponse,
    SettingsUpdateRequest,
    SettingsUpdateResponse,
    StatusResponse,
    StreamControlResponse,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

    from src.config.runtime_config import RuntimeConfig
    from src.config.settings import Settings
    from src.core.grabber import FrameGrabber
    from src.core.state import MonitoringState

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def create_app(
    state: MonitoringState,
    runtime_config: RuntimeConfig,
    swap_camera_fn: Callable[[str, int], None] | None = None,
    grabber: FrameGrabber | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        state: Shared monitoring state.
        runtime_config: Runtime-mutable configuration.
        swap_camera_fn: Callback to swap camera (url, device_index).
        grabber: FrameGrabber instance for stop/start control.
        settings: Application settings (for API key availability info).

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
            actions=result.actions,
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
                actions=r.actions,
            )
            for r in history
        ]
        return HistoryResponse(items=items)

    @app.get("/api/settings")
    async def api_get_settings() -> SettingsGetResponse:
        """Get current runtime settings."""
        return SettingsGetResponse(
            analysis_interval_seconds=runtime_config.analysis_interval_seconds,
            camera_url=runtime_config.camera_url,
            camera_device_index=runtime_config.camera_device_index,
            llm_provider=runtime_config.llm_provider,
            llm_model=runtime_config.llm_model,
            capture_width=runtime_config.capture_width,
            capture_height=runtime_config.capture_height,
            openai_available=bool(settings and settings.openai_api_key),
            gemini_available=bool(settings and settings.gemini_api_key),
        )

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
        if body.camera_device_index is not None:
            runtime_config.camera_device_index = body.camera_device_index
            logger.info("Updated camera_device_index to %d", body.camera_device_index)
        if body.llm_provider is not None:
            runtime_config.llm_provider = body.llm_provider
            logger.info("Updated llm_provider to %s", body.llm_provider)
        if body.llm_model is not None:
            runtime_config.llm_model = body.llm_model
            logger.info("Updated llm_model to %s", body.llm_model)
        if body.capture_width is not None:
            runtime_config.capture_width = body.capture_width
            logger.info("Updated capture_width to %d", body.capture_width)
        if body.capture_height is not None:
            runtime_config.capture_height = body.capture_height
            logger.info("Updated capture_height to %d", body.capture_height)
        return SettingsUpdateResponse(
            analysis_interval_seconds=runtime_config.analysis_interval_seconds,
            camera_url=runtime_config.camera_url,
            camera_device_index=runtime_config.camera_device_index,
            llm_provider=runtime_config.llm_provider,
            llm_model=runtime_config.llm_model,
            capture_width=runtime_config.capture_width,
            capture_height=runtime_config.capture_height,
        )

    @app.post("/api/camera/swap")
    async def api_camera_swap(body: CameraSwapRequest) -> CameraSwapResponse:
        """Swap to a different camera source."""
        if swap_camera_fn is None:
            return CameraSwapResponse(
                ok=False,
                camera_url=runtime_config.camera_url,
                camera_device_index=runtime_config.camera_device_index,
                message="Camera swap not available",
            )
        url = body.camera_url or ""
        device_index = body.camera_device_index or 0
        try:
            swap_camera_fn(url, device_index)
        except Exception:
            logger.exception("Failed to swap camera")
            return CameraSwapResponse(
                ok=False,
                camera_url=runtime_config.camera_url,
                camera_device_index=runtime_config.camera_device_index,
                message="Failed to swap camera",
            )
        runtime_config.camera_url = url
        runtime_config.camera_device_index = device_index
        logger.info(
            "Camera swapped: url=%s, device_index=%d",
            url,
            device_index,
        )
        return CameraSwapResponse(
            ok=True,
            camera_url=url,
            camera_device_index=device_index,
            message="Camera swapped successfully",
        )

    @app.post("/api/stream/stop")
    async def api_stream_stop() -> StreamControlResponse:
        """Stop the frame grabber."""
        if grabber is None:
            return StreamControlResponse(
                ok=False, running=False, message="Stream control not available"
            )
        grabber.stop()
        logger.info("Stream stopped via API")
        return StreamControlResponse(ok=True, running=False, message="Stream stopped")

    @app.post("/api/stream/start")
    async def api_stream_start() -> StreamControlResponse:
        """Start the frame grabber."""
        if grabber is None:
            return StreamControlResponse(
                ok=False, running=False, message="Stream control not available"
            )
        if grabber.running:
            return StreamControlResponse(
                ok=True, running=True, message="Stream already running"
            )
        grabber.start()
        logger.info("Stream started via API")
        return StreamControlResponse(ok=True, running=True, message="Stream started")

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
