"""Data models for analysis results."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class AnalysisResult:
    """Result of a newborn status analysis.

    Attributes:
        timestamp: When the analysis was performed (UTC).
        posture: Detected posture (e.g., "仰向け", "うつ伏せ", "横向き").
        sleep_state: Sleep state (e.g., "睡眠中", "覚醒", "不明").
        anomalies: List of detected anomalies, empty if none.
        summary: Overall status summary from the LLM.
        confidence: Confidence assessment (e.g., "high", "medium", "low").
        raw_response: Full raw text response from the LLM.
    """

    timestamp: datetime
    posture: str
    sleep_state: str
    summary: str
    confidence: str
    raw_response: str
    anomalies: list[str] = field(default_factory=list)

    @classmethod
    def create_now(
        cls,
        *,
        posture: str,
        sleep_state: str,
        summary: str,
        confidence: str,
        raw_response: str,
        anomalies: list[str] | None = None,
    ) -> AnalysisResult:
        """Create an AnalysisResult with current UTC timestamp."""
        return cls(
            timestamp=datetime.now(tz=UTC),
            posture=posture,
            sleep_state=sleep_state,
            summary=summary,
            confidence=confidence,
            raw_response=raw_response,
            anomalies=anomalies or [],
        )
