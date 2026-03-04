"""Video capture module for mimamori."""

from src.capture.camera import CameraProtocol, OpenCVCamera
from src.capture.encoding import encode_frame_to_base64
from src.capture.factory import build_http_snapshot_url, create_camera
from src.capture.http_camera import HTTPCamera
from src.capture.rtsp_camera import RTSPCamera

__all__ = [
    "CameraProtocol",
    "HTTPCamera",
    "OpenCVCamera",
    "RTSPCamera",
    "build_http_snapshot_url",
    "create_camera",
    "encode_frame_to_base64",
]
