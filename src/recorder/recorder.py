"""Video recorder for mimamori monitoring system."""

from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import cv2

if TYPE_CHECKING:
    import numpy as np
    import numpy.typing as npt

    from src.core.state import MonitoringState

logger = logging.getLogger(__name__)

_DEFAULT_OUTPUT_DIR = "recordings"
_DEFAULT_FPS = 10.0
_FRAME_INTERVAL = 1.0 / _DEFAULT_FPS


class VideoRecorder:
    """Records video from MonitoringState frames to MP4 files.

    Runs as a daemon thread, grabbing frames from state and writing
    them to a timestamped MP4 file using OpenCV VideoWriter.
    """

    def __init__(
        self,
        state: MonitoringState,
        output_dir: str = _DEFAULT_OUTPUT_DIR,
        fps: float = _DEFAULT_FPS,
    ) -> None:
        """Initialize video recorder.

        Args:
            state: Shared monitoring state to read frames from.
            output_dir: Directory to save recordings.
            fps: Frames per second for output video.
        """
        self._state = state
        self._output_dir = Path(output_dir)
        self._fps = fps
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._current_file: str = ""

    @property
    def recording(self) -> bool:
        """Check if recording is currently active."""
        return self._thread is not None and self._thread.is_alive()

    @property
    def current_file(self) -> str:
        """Get the path of the current recording file."""
        return self._current_file

    def start(self) -> str:
        """Start recording to a new timestamped file.

        Returns:
            Path of the output file.
        """
        if self.recording:
            return self._current_file

        self._output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        self._current_file = str(self._output_dir / f"{timestamp}.mp4")

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="video-recorder",
            daemon=True,
        )
        self._thread.start()
        logger.info("Recording started: %s", self._current_file)
        return self._current_file

    def stop(self) -> str:
        """Stop recording.

        Returns:
            Path of the completed recording file.
        """
        filepath = self._current_file
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        logger.info("Recording stopped: %s", filepath)
        return filepath

    def _run(self) -> None:
        """Recording loop."""
        writer: cv2.VideoWriter | None = None
        try:
            while not self._stop_event.is_set():
                frame = self._state.get_frame()
                if frame is not None:
                    if writer is None:
                        writer = self._create_writer(frame)
                    writer.write(frame)
                self._stop_event.wait(timeout=_FRAME_INTERVAL)
        finally:
            if writer is not None:
                writer.release()

    def _create_writer(self, frame: npt.NDArray[np.uint8]) -> cv2.VideoWriter:
        """Create a VideoWriter based on frame dimensions.

        Args:
            frame: Sample frame to determine dimensions.

        Returns:
            Configured cv2.VideoWriter instance.
        """
        height, width = frame.shape[:2]
        fourcc: int = cv2.VideoWriter_fourcc(*"mp4v")  # type: ignore[attr-defined]
        writer = cv2.VideoWriter(self._current_file, fourcc, self._fps, (width, height))
        logger.debug(
            "VideoWriter created: %s (%dx%d @ %.1f fps)",
            self._current_file,
            width,
            height,
            self._fps,
        )
        return writer
