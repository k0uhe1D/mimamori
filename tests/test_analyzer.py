"""Tests for analyzer module."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from src.analyzer import AnalysisResult, analyze_frame


class TestAnalysisResult:
    """Tests for AnalysisResult dataclass."""

    def test_create_now_sets_timestamp(self) -> None:
        """create_now() sets a UTC timestamp."""
        result = AnalysisResult.create_now(
            posture="仰向け",
            sleep_state="睡眠中",
            summary="正常",
            confidence="high",
            raw_response="{}",
        )
        assert result.timestamp is not None
        assert result.posture == "仰向け"
        assert result.anomalies == []
        assert result.actions == []

    def test_create_now_with_anomalies(self) -> None:
        """create_now() accepts anomalies list."""
        result = AnalysisResult.create_now(
            posture="うつ伏せ",
            sleep_state="睡眠中",
            summary="危険",
            confidence="high",
            raw_response="{}",
            anomalies=["うつ伏せ姿勢を検知"],
        )
        assert len(result.anomalies) == 1

    def test_create_now_with_actions(self) -> None:
        """create_now() accepts actions list."""
        result = AnalysisResult.create_now(
            posture="仰向け",
            sleep_state="覚醒",
            summary="元気に動いている",
            confidence="high",
            raw_response="{}",
            actions=["右手を挙げている", "あくびをしている"],
        )
        assert len(result.actions) == 2
        assert "右手を挙げている" in result.actions


class TestAnalyzeFrame:
    """Tests for analyze_frame function."""

    @patch("src.analyzer.client.OpenAI")
    def test_successful_analysis(self, mock_openai_cls: MagicMock) -> None:
        """analyze_frame returns parsed result on valid JSON response."""
        response_json = json.dumps(
            {
                "posture": "仰向け",
                "sleep_state": "睡眠中",
                "actions": ["右手を挙げている", "目を閉じている"],
                "anomalies": [],
                "summary": "新生児は仰向けで安全に睡眠中です。",
                "confidence": "high",
            }
        )
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = response_json
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[mock_choice]
        )
        mock_openai_cls.return_value = mock_client

        result = analyze_frame(
            base64_image="fake_base64",
            api_key="test-key",
        )
        assert result.posture == "仰向け"
        assert result.sleep_state == "睡眠中"
        assert result.confidence == "high"
        assert result.anomalies == []
        assert result.actions == ["右手を挙げている", "目を閉じている"]

    @patch("src.analyzer.client.OpenAI")
    def test_invalid_json_response_graceful(self, mock_openai_cls: MagicMock) -> None:
        """analyze_frame handles non-JSON responses gracefully."""
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Sorry, I cannot analyze this image."
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[mock_choice]
        )
        mock_openai_cls.return_value = mock_client

        result = analyze_frame(
            base64_image="fake_base64",
            api_key="test-key",
        )
        assert result.posture == "不明"
        assert result.confidence == "low"
        assert "JSON解析に失敗" in result.anomalies[0]
