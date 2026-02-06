"""Configuration management for mimamori."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables.

    Attributes:
        openai_api_key: OpenAI API key for GPT-4o Vision API.
        camera_device_index: Camera device index for OpenCV VideoCapture.
        analysis_interval_seconds: Interval between analyses in periodic mode.
        capture_width: Requested capture width in pixels.
        capture_height: Requested capture height in pixels.
        openai_model: OpenAI model to use for analysis.
    """

    openai_api_key: str
    camera_device_index: int = 0
    analysis_interval_seconds: int = 30
    capture_width: int = 640
    capture_height: int = 480
    openai_model: str = "gpt-4o"

    @classmethod
    def from_env(cls) -> Settings:
        """Create Settings from environment variables.

        Environment variables:
            OPENAI_API_KEY (required): OpenAI API key.
            CAMERA_DEVICE_INDEX (optional, default 0): Camera device index.
            ANALYSIS_INTERVAL_SECONDS (optional, default 30): Analysis interval.
            CAPTURE_WIDTH (optional, default 640): Capture width.
            CAPTURE_HEIGHT (optional, default 480): Capture height.
            OPENAI_MODEL (optional, default "gpt-4o"): OpenAI model name.

        Raises:
            ValueError: If OPENAI_API_KEY is not set.
        """
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            msg = "OPENAI_API_KEY environment variable is required"
            raise ValueError(msg)

        return cls(
            openai_api_key=api_key,
            camera_device_index=int(os.environ.get("CAMERA_DEVICE_INDEX", "0")),
            analysis_interval_seconds=int(
                os.environ.get("ANALYSIS_INTERVAL_SECONDS", "30")
            ),
            capture_width=int(os.environ.get("CAPTURE_WIDTH", "640")),
            capture_height=int(os.environ.get("CAPTURE_HEIGHT", "480")),
            openai_model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
        )
