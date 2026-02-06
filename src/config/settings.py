"""Configuration management for mimamori."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables.

    Attributes:
        llm_provider: LLM provider to use ("openai" or "gemini").
        openai_api_key: OpenAI API key for GPT-4o Vision API.
        gemini_api_key: Google Gemini API key.
        camera_device_index: Camera device index for OpenCV VideoCapture.
        camera_url: RTSP camera URL (empty for local device).
        analysis_interval_seconds: Interval between analyses in periodic mode.
        capture_width: Requested capture width in pixels.
        capture_height: Requested capture height in pixels.
        openai_model: OpenAI model to use for analysis.
        gemini_model: Gemini model to use for analysis.
    """

    llm_provider: str = "openai"
    openai_api_key: str = ""
    gemini_api_key: str = ""
    camera_device_index: int = 0
    camera_url: str = ""
    analysis_interval_seconds: int = 5
    capture_width: int = 640
    capture_height: int = 480
    openai_model: str = "gpt-4o"
    gemini_model: str = "gemini-2.5-flash"

    @classmethod
    def from_env(cls) -> Settings:
        """Create Settings from environment variables.

        Environment variables:
            LLM_PROVIDER (optional, default "openai"): "openai" or "gemini".
            OPENAI_API_KEY: OpenAI API key (required when provider is openai).
            GEMINI_API_KEY: Google Gemini API key (required when provider is gemini).
            CAMERA_DEVICE_INDEX (optional, default 0): Camera device index.
            CAMERA_URL (optional): RTSP camera URL.
            ANALYSIS_INTERVAL_SECONDS (optional, default 5): Analysis interval.
            CAPTURE_WIDTH (optional, default 640): Capture width.
            CAPTURE_HEIGHT (optional, default 480): Capture height.
            OPENAI_MODEL (optional, default "gpt-4o"): OpenAI model name.
            GEMINI_MODEL (optional, default "gemini-2.5-flash"): Gemini model name.

        Raises:
            ValueError: If required API key for the selected provider is not set.
        """
        provider = os.environ.get("LLM_PROVIDER", "openai").lower()
        openai_key = os.environ.get("OPENAI_API_KEY", "")
        gemini_key = os.environ.get("GEMINI_API_KEY", "")

        if provider == "openai" and not openai_key:
            msg = (
                "OPENAI_API_KEY environment variable is required"
                " when LLM_PROVIDER=openai"
            )
            raise ValueError(msg)
        if provider == "gemini" and not gemini_key:
            msg = (
                "GEMINI_API_KEY environment variable is required"
                " when LLM_PROVIDER=gemini"
            )
            raise ValueError(msg)

        return cls(
            llm_provider=provider,
            openai_api_key=openai_key,
            gemini_api_key=gemini_key,
            camera_device_index=int(os.environ.get("CAMERA_DEVICE_INDEX", "0")),
            camera_url=os.environ.get("CAMERA_URL", ""),
            analysis_interval_seconds=int(
                os.environ.get("ANALYSIS_INTERVAL_SECONDS", "5")
            ),
            capture_width=int(os.environ.get("CAPTURE_WIDTH", "640")),
            capture_height=int(os.environ.get("CAPTURE_HEIGHT", "480")),
            openai_model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
            gemini_model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
        )
