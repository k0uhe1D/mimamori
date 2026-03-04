"""Tests for main entry point."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np

from src.__main__ import run_once
from src.analyzer.models import AnalysisResult
from src.config import Settings


class TestRunOnce:
    """Tests for run_once function."""

    @patch("src.__main__.analyze_frame")
    @patch("src.__main__.encode_frame_to_base64")
    @patch("src.__main__.create_camera")
    def test_run_once_success(
        self,
        mock_create_camera: MagicMock,
        mock_encode: MagicMock,
        mock_analyze: MagicMock,
    ) -> None:
        """run_once returns 0 on successful capture and analysis."""
        mock_camera = MagicMock()
        mock_camera.read_frame.return_value = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_create_camera.return_value = mock_camera
        mock_encode.return_value = "base64data"
        mock_analyze.return_value = AnalysisResult.create_now(
            posture="仰向け",
            sleep_state="睡眠中",
            summary="正常",
            confidence="high",
            raw_response="{}",
        )

        settings = Settings(openai_api_key="test-key")
        assert run_once(settings) == 0
        mock_camera.release.assert_called_once()

    @patch("src.__main__.create_camera")
    def test_run_once_capture_failure(self, mock_create_camera: MagicMock) -> None:
        """run_once returns 1 when frame capture fails."""
        mock_camera = MagicMock()
        mock_camera.read_frame.return_value = None
        mock_create_camera.return_value = mock_camera

        settings = Settings(openai_api_key="test-key")
        assert run_once(settings) == 1
        mock_camera.release.assert_called_once()
