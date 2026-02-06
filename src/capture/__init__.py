"""Video capture module for mimamori."""

from src.capture.camera import CameraProtocol, OpenCVCamera
from src.capture.encoding import encode_frame_to_base64

__all__ = ["CameraProtocol", "OpenCVCamera", "encode_frame_to_base64"]
