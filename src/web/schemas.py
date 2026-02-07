"""Pydantic schemas for mimamori Web API."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003

from pydantic import BaseModel


class StatusResponse(BaseModel):
    """Response for /api/status endpoint."""

    has_result: bool
    timestamp: datetime | None = None
    posture: str = ""
    sleep_state: str = ""
    summary: str = ""
    confidence: str = ""
    anomalies: list[str] = []
    actions: list[str] = []


class HistoryItem(BaseModel):
    """Single history entry."""

    timestamp: datetime
    posture: str
    sleep_state: str
    summary: str
    confidence: str
    anomalies: list[str]
    actions: list[str] = []


class HistoryResponse(BaseModel):
    """Response for /api/history endpoint."""

    items: list[HistoryItem]


class SettingsGetResponse(BaseModel):
    """Response for GET /api/settings endpoint."""

    analysis_interval_seconds: int
    camera_url: str
    camera_device_index: int
    llm_provider: str
    llm_model: str
    capture_width: int
    capture_height: int
    openai_available: bool
    gemini_available: bool


class SettingsUpdateRequest(BaseModel):
    """Request for POST /api/settings endpoint."""

    analysis_interval_seconds: int | None = None
    camera_url: str | None = None
    camera_device_index: int | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    capture_width: int | None = None
    capture_height: int | None = None


class SettingsUpdateResponse(BaseModel):
    """Response for POST /api/settings endpoint."""

    analysis_interval_seconds: int
    camera_url: str
    camera_device_index: int
    llm_provider: str
    llm_model: str
    capture_width: int
    capture_height: int


class CameraSwapRequest(BaseModel):
    """Request for POST /api/camera/swap endpoint."""

    camera_url: str | None = None
    camera_device_index: int | None = None


class CameraSwapResponse(BaseModel):
    """Response for POST /api/camera/swap endpoint."""

    ok: bool
    camera_url: str
    camera_device_index: int
    message: str = ""


class StreamControlResponse(BaseModel):
    """Response for POST /api/stream/stop and /api/stream/start endpoints."""

    ok: bool
    running: bool
    message: str = ""


class AnalysisControlResponse(BaseModel):
    """Response for POST /api/analysis/pause and /api/analysis/resume."""

    ok: bool
    paused: bool
    message: str = ""


class RecordingControlResponse(BaseModel):
    """Response for POST /api/recording/start and /api/recording/stop."""

    ok: bool
    recording: bool
    file: str = ""
    message: str = ""


class IPWebcamControlRequest(BaseModel):
    """Request for POST /api/ipwebcam/control."""

    path: str


class IPWebcamControlResponse(BaseModel):
    """Response for POST /api/ipwebcam/control."""

    ok: bool
    message: str = ""


class SleepSessionItem(BaseModel):
    """Single sleep session entry."""

    start_time: datetime
    end_time: datetime | None = None
    duration_seconds: float
    is_active: bool
    snapshot_count: int
    timelapse_available: bool = False


class SleepStatusResponse(BaseModel):
    """Response for GET /api/sleep/status."""

    is_sleeping: bool
    current_session: SleepSessionItem | None = None


class SleepHistoryResponse(BaseModel):
    """Response for GET /api/sleep/history."""

    sessions: list[SleepSessionItem]
    total_sleep_seconds: float
