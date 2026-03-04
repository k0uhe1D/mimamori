"""Camera factory helpers for local/RTSP/HTTP sources."""

from __future__ import annotations

import logging
from urllib.parse import ParseResult, urlparse, urlunparse

from src.capture.camera import CameraProtocol, OpenCVCamera
from src.capture.http_camera import HTTPCamera
from src.capture.rtsp_camera import RTSPCamera

logger = logging.getLogger(__name__)


def build_http_snapshot_url(
    camera_url: str,
    snapshot_path: str = "/shot.jpg",
) -> str:
    """Build an HTTP snapshot URL from a base URL or return full URL as-is.

    If `camera_url` already contains a non-root path, it is treated as a full
    snapshot endpoint URL. If path is empty/root, `snapshot_path` is appended.
    """
    parsed = urlparse(camera_url)
    if parsed.path and parsed.path != "/":
        return camera_url

    normalized_path = (
        snapshot_path if snapshot_path.startswith("/") else f"/{snapshot_path}"
    )
    with_path: ParseResult = parsed._replace(path=normalized_path)
    return urlunparse(with_path)


def create_camera(
    camera_url: str,
    device_index: int,
    width: int,
    height: int,
    http_snapshot_path: str = "/shot.jpg",
) -> CameraProtocol:
    """Create a camera instance from URL/device settings."""
    if camera_url.startswith(("http://", "https://")):
        shot_url = build_http_snapshot_url(camera_url, http_snapshot_path)
        logger.info("Using HTTP camera: %s", shot_url)
        return HTTPCamera(shot_url=shot_url)
    if camera_url:
        logger.info("Using RTSP camera: %s", camera_url)
        return RTSPCamera(url=camera_url)
    logger.info("Using local camera device: %d", device_index)
    return OpenCVCamera(device_index=device_index, width=width, height=height)
