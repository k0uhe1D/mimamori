"""Tests for VideoRecorder."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from src.core.state import MonitoringState
from src.recorder.recorder import VideoRecorder


class TestVideoRecorder:
    """Tests for VideoRecorder."""

    def test_recording_false_initially(self) -> None:
        """VideoRecorder is not recording initially."""
        state = MonitoringState()
        recorder = VideoRecorder(state=state)
        assert not recorder.recording
        assert recorder.current_file == ""

    def test_start_creates_file(self, tmp_path: Path) -> None:
        """VideoRecorder.start() creates a recording file."""
        state = MonitoringState()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        state.update_frame(frame)

        recorder = VideoRecorder(state=state, output_dir=str(tmp_path))
        filepath = recorder.start()
        assert recorder.recording
        assert filepath.endswith(".mp4")
        assert recorder.current_file == filepath
        time.sleep(0.3)
        recorder.stop()
        assert not recorder.recording
        assert Path(filepath).exists()

    def test_stop_returns_filepath(self, tmp_path: Path) -> None:
        """VideoRecorder.stop() returns the completed file path."""
        state = MonitoringState()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        state.update_frame(frame)

        recorder = VideoRecorder(state=state, output_dir=str(tmp_path))
        started_path = recorder.start()
        time.sleep(0.3)
        stopped_path = recorder.stop()
        assert started_path == stopped_path

    def test_start_when_already_recording(self, tmp_path: Path) -> None:
        """VideoRecorder.start() returns current file if already recording."""
        state = MonitoringState()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        state.update_frame(frame)

        recorder = VideoRecorder(state=state, output_dir=str(tmp_path))
        path1 = recorder.start()
        path2 = recorder.start()
        assert path1 == path2
        recorder.stop()
