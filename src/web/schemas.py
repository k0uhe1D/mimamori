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


class HistoryItem(BaseModel):
    """Single history entry."""

    timestamp: datetime
    posture: str
    sleep_state: str
    summary: str
    confidence: str
    anomalies: list[str]


class HistoryResponse(BaseModel):
    """Response for /api/history endpoint."""

    items: list[HistoryItem]


class SettingsUpdateRequest(BaseModel):
    """Request for POST /api/settings endpoint."""

    analysis_interval_seconds: int | None = None
    camera_url: str | None = None


class SettingsUpdateResponse(BaseModel):
    """Response for POST /api/settings endpoint."""

    analysis_interval_seconds: int
    camera_url: str
