"""FastAPI application for mimamori web dashboard."""

from __future__ import annotations

import asyncio
import logging
import ssl
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING, Any

import cv2
from fastapi import FastAPI
from fastapi.requests import Request  # noqa: TC002
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from src.web.schemas import (
    AnalysisControlResponse,
    CameraSwapRequest,
    CameraSwapResponse,
    HistoryItem,
    HistoryResponse,
    IPWebcamControlRequest,
    IPWebcamControlResponse,
    RecordingControlResponse,
    SettingsGetResponse,
    SettingsUpdateRequest,
    SettingsUpdateResponse,
    SleepHistoryResponse,
    SleepSessionItem,
    SleepStatusResponse,
    StatusResponse,
    StreamControlResponse,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

    from src.config.runtime_config import RuntimeConfig
    from src.config.settings import Settings
    from src.core.analyzer_worker import AnalyzerWorker
    from src.core.grabber import FrameGrabber
    from src.core.sleep_tracker import SleepTracker
    from src.core.state import MonitoringState
    from src.recorder.recorder import VideoRecorder

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def create_app(
    state: MonitoringState,
    runtime_config: RuntimeConfig,
    swap_camera_fn: Callable[[str, int], None] | None = None,
    grabber: FrameGrabber | None = None,
    settings: Settings | None = None,
    worker: AnalyzerWorker | None = None,
    recorder: VideoRecorder | None = None,
    sleep_tracker: SleepTracker | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        state: Shared monitoring state.
        runtime_config: Runtime-mutable configuration.
        swap_camera_fn: Callback to swap camera (url, device_index).
        grabber: FrameGrabber instance for stop/start control.
        settings: Application settings (for API key availability info).
        worker: AnalyzerWorker instance for pause/resume control.
        recorder: VideoRecorder instance for recording control.
        sleep_tracker: SleepTracker instance for sleep monitoring.

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

    @app.post("/api/analysis/pause")
    async def api_analysis_pause() -> AnalysisControlResponse:
        """Pause the analyzer worker."""
        if worker is None:
            return AnalysisControlResponse(
                ok=False, paused=False, message="Analysis control not available"
            )
        worker.pause()
        logger.info("Analysis paused via API")
        return AnalysisControlResponse(ok=True, paused=True, message="Analysis paused")

    @app.post("/api/analysis/resume")
    async def api_analysis_resume() -> AnalysisControlResponse:
        """Resume the analyzer worker."""
        if worker is None:
            return AnalysisControlResponse(
                ok=False, paused=False, message="Analysis control not available"
            )
        worker.resume()
        logger.info("Analysis resumed via API")
        return AnalysisControlResponse(
            ok=True, paused=False, message="Analysis resumed"
        )

    @app.post("/api/recording/start")
    async def api_recording_start() -> RecordingControlResponse:
        """Start recording video."""
        if recorder is None:
            return RecordingControlResponse(
                ok=False, recording=False, message="Recording not available"
            )
        if recorder.recording:
            return RecordingControlResponse(
                ok=True,
                recording=True,
                file=recorder.current_file,
                message="Already recording",
            )
        filepath = recorder.start()
        logger.info("Recording started via API: %s", filepath)
        return RecordingControlResponse(
            ok=True, recording=True, file=filepath, message="Recording started"
        )

    @app.post("/api/recording/stop")
    async def api_recording_stop() -> RecordingControlResponse:
        """Stop recording video."""
        if recorder is None:
            return RecordingControlResponse(
                ok=False, recording=False, message="Recording not available"
            )
        if not recorder.recording:
            return RecordingControlResponse(
                ok=True, recording=False, message="Not recording"
            )
        filepath = recorder.stop()
        logger.info("Recording stopped via API: %s", filepath)
        return RecordingControlResponse(
            ok=True, recording=False, file=filepath, message="Recording stopped"
        )

    @app.post("/api/ipwebcam/control")
    async def api_ipwebcam_control(
        body: IPWebcamControlRequest,
    ) -> IPWebcamControlResponse:
        """Proxy control commands to IP Webcam."""
        cam_url = runtime_config.camera_url
        if not cam_url.startswith(("http://", "https://")):
            return IPWebcamControlResponse(ok=False, message="IP Webcam not configured")
        if not _is_allowed_ipwebcam_path(body.path):
            return IPWebcamControlResponse(ok=False, message="Command not allowed")
        url = cam_url.rstrip("/") + body.path
        try:
            await asyncio.to_thread(_ipwebcam_fetch, url)
        except Exception:
            logger.exception("IP Webcam control failed: %s", body.path)
            return IPWebcamControlResponse(ok=False, message="Request failed")
        logger.info("IP Webcam control: %s", body.path)
        return IPWebcamControlResponse(ok=True)

    @app.get("/api/ipwebcam/status")
    async def api_ipwebcam_status() -> JSONResponse:
        """Get current IP Webcam status and available settings."""
        cam_url = runtime_config.camera_url
        if not cam_url.startswith(("http://", "https://")):
            return JSONResponse({"ok": False})
        url = cam_url.rstrip("/") + "/status.json?show_avail=1"
        try:
            import json

            raw = await asyncio.to_thread(_ipwebcam_fetch, url)
            data: dict[str, Any] = json.loads(raw)
            return JSONResponse({"ok": True, **data})
        except Exception:
            logger.exception("IP Webcam status fetch failed")
            return JSONResponse({"ok": False})

    @app.get("/api/sleep/status")
    async def api_sleep_status() -> SleepStatusResponse:
        """Get current sleep tracking status."""
        if sleep_tracker is None:
            return SleepStatusResponse(is_sleeping=False)
        session = sleep_tracker.active_session
        if session is None:
            return SleepStatusResponse(is_sleeping=False)
        return SleepStatusResponse(
            is_sleeping=True,
            current_session=SleepSessionItem(
                start_time=session.start_time,
                end_time=session.end_time,
                duration_seconds=session.duration_seconds,
                is_active=session.is_active,
                snapshot_count=len(session.snapshot_paths),
            ),
        )

    @app.get("/api/sleep/history")
    async def api_sleep_history() -> SleepHistoryResponse:
        """Get sleep session history."""
        if sleep_tracker is None:
            return SleepHistoryResponse(sessions=[], total_sleep_seconds=0.0)
        sessions = sleep_tracker.get_sessions(limit=50)
        items = [
            SleepSessionItem(
                start_time=s.start_time,
                end_time=s.end_time,
                duration_seconds=s.duration_seconds,
                is_active=s.is_active,
                snapshot_count=len(s.snapshot_paths),
            )
            for s in sessions
        ]
        total = sum(s.duration_seconds for s in sessions)
        return SleepHistoryResponse(sessions=items, total_sleep_seconds=total)

    return app


_IPWEBCAM_SSL_CTX = ssl.create_default_context()
_IPWEBCAM_SSL_CTX.check_hostname = False
_IPWEBCAM_SSL_CTX.verify_mode = ssl.CERT_NONE

_ALLOWED_IPWEBCAM_PATHS = frozenset({"/enabletorch", "/disabletorch", "/focus"})
_ALLOWED_IPWEBCAM_PREFIXES = ("/settings/", "/ptz")


def _is_allowed_ipwebcam_path(path: str) -> bool:
    """Check if the IP Webcam path is in the whitelist."""
    if path in _ALLOWED_IPWEBCAM_PATHS:
        return True
    return any(path.startswith(p) for p in _ALLOWED_IPWEBCAM_PREFIXES)


def _ipwebcam_fetch(url: str) -> str:
    """Fetch a URL from IP Webcam (sync, run via asyncio.to_thread)."""
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, context=_IPWEBCAM_SSL_CTX, timeout=5) as resp:
        result: str = resp.read().decode("utf-8")
        return result


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
