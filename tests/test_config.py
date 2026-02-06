"""Tests for configuration module."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from src.config import Settings


class TestSettings:
    """Tests for Settings dataclass."""

    def test_from_env_with_openai_key(self) -> None:
        """Settings.from_env() works with OPENAI_API_KEY set."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-123"}):
            settings = Settings.from_env()
        assert settings.openai_api_key == "test-key-123"
        assert settings.llm_provider == "openai"
        assert settings.camera_device_index == 0
        assert settings.analysis_interval_seconds == 30

    def test_from_env_missing_openai_key_raises(self) -> None:
        """Settings.from_env() raises ValueError without OPENAI_API_KEY."""
        env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
        with (
            patch.dict(os.environ, env, clear=True),
            pytest.raises(ValueError, match="OPENAI_API_KEY"),
        ):
            Settings.from_env()

    def test_from_env_gemini_provider(self) -> None:
        """Settings.from_env() works with LLM_PROVIDER=gemini."""
        env = {
            "LLM_PROVIDER": "gemini",
            "GEMINI_API_KEY": "gemini-key-123",
        }
        with patch.dict(os.environ, env):
            settings = Settings.from_env()
        assert settings.llm_provider == "gemini"
        assert settings.gemini_api_key == "gemini-key-123"

    def test_from_env_gemini_missing_key_raises(self) -> None:
        """Settings.from_env() raises ValueError without GEMINI_API_KEY."""
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("OPENAI_API_KEY", "GEMINI_API_KEY")
        }
        env["LLM_PROVIDER"] = "gemini"
        with (
            patch.dict(os.environ, env, clear=True),
            pytest.raises(ValueError, match="GEMINI_API_KEY"),
        ):
            Settings.from_env()

    def test_from_env_custom_values(self) -> None:
        """Settings.from_env() reads custom environment values."""
        env = {
            "OPENAI_API_KEY": "key",
            "CAMERA_DEVICE_INDEX": "2",
            "ANALYSIS_INTERVAL_SECONDS": "60",
            "CAPTURE_WIDTH": "1280",
            "CAPTURE_HEIGHT": "720",
            "OPENAI_MODEL": "gpt-4o-mini",
        }
        with patch.dict(os.environ, env):
            settings = Settings.from_env()
        assert settings.camera_device_index == 2
        assert settings.analysis_interval_seconds == 60
        assert settings.capture_width == 1280
        assert settings.capture_height == 720
        assert settings.openai_model == "gpt-4o-mini"

    def test_settings_is_frozen(self) -> None:
        """Settings instances are immutable."""
        settings = Settings(openai_api_key="key")
        with pytest.raises(AttributeError):
            settings.openai_api_key = "new-key"  # type: ignore[misc]
