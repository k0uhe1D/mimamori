"""Tests for FrameGrabber."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.core.grabber import FrameGrabber
from src.core.state import MonitoringState


def _make_camera(frame_value: object = None) -> MagicMock:
    """Create a mock camera."""
    camera = MagicMock()
    camera.read_frame.return_value = frame_value
    return camera


class TestFrameGrabberSwapCamera:
    """Tests for FrameGrabber.swap_camera()."""

    def test_swap_camera_releases_old_camera(self) -> None:
        """swap_camera releases the old camera."""
        old_camera = _make_camera()
        new_camera = _make_camera()
        state = MonitoringState()
        grabber = FrameGrabber(camera=old_camera, state=state)

        grabber.swap_camera(new_camera)

        old_camera.release.assert_called_once()

    def test_swap_camera_restarts_when_running(self) -> None:
        """swap_camera stops and restarts when grabber was running."""
        old_camera = _make_camera()
        new_camera = _make_camera()
        state = MonitoringState()
        grabber = FrameGrabber(camera=old_camera, state=state)

        grabber.start()
        assert grabber.running

        grabber.swap_camera(new_camera)

        old_camera.release.assert_called_once()
        assert grabber.running

        grabber.stop()

    def test_swap_camera_stays_stopped_when_not_running(self) -> None:
        """swap_camera does not start grabber if it was stopped."""
        old_camera = _make_camera()
        new_camera = _make_camera()
        state = MonitoringState()
        grabber = FrameGrabber(camera=old_camera, state=state)

        assert not grabber.running

        grabber.swap_camera(new_camera)

        old_camera.release.assert_called_once()
        assert not grabber.running


class TestFrameGrabberRunning:
    """Tests for FrameGrabber.running property."""

    def test_running_false_initially(self) -> None:
        """running is False before start."""
        camera = _make_camera()
        state = MonitoringState()
        grabber = FrameGrabber(camera=camera, state=state)
        assert not grabber.running

    def test_running_true_after_start(self) -> None:
        """running is True after start."""
        camera = _make_camera()
        state = MonitoringState()
        grabber = FrameGrabber(camera=camera, state=state)
        grabber.start()
        assert grabber.running
        grabber.stop()

    def test_running_false_after_stop(self) -> None:
        """running is False after stop."""
        camera = _make_camera()
        state = MonitoringState()
        grabber = FrameGrabber(camera=camera, state=state)
        grabber.start()
        grabber.stop()
        assert not grabber.running
