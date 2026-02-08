"""Sleep session data model for mimamori monitoring system."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class SleepSession:
    """Represents a single sleep session.

    Tracks when the baby fell asleep, woke up, and stores paths to
    snapshots captured during sleep for timelapse generation.

    Attributes:
        start_time: When the baby fell asleep (UTC).
        end_time: When the baby woke up (UTC), None if still sleeping.
        snapshot_paths: Paths to JPEG snapshots captured during sleep.
    """

    start_time: datetime
    end_time: datetime | None = None
    snapshot_paths: list[str] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float:
        """Calculate sleep duration in seconds.

        Returns:
            Seconds from start_time to end_time (or now if still active).
        """
        end = self.end_time if self.end_time is not None else datetime.now(tz=UTC)
        return (end - self.start_time).total_seconds()

    @property
    def is_active(self) -> bool:
        """Check if this sleep session is still active.

        Returns:
            True if end_time is None (baby still sleeping).
        """
        return self.end_time is None
