"""Tests for timelapse GIF generation."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.sleep_tracker import generate_timelapse_gif

_COLORS = ("red", "green", "blue", "yellow", "purple")


def _create_jpeg(
    path: str, width: int = 100, height: int = 80, color: str = "red"
) -> None:
    """Create a minimal JPEG file for testing."""
    from PIL import Image

    img = Image.new("RGB", (width, height), color=color)
    img.save(path, format="JPEG")


class TestGenerateTimelapseGif:
    """Tests for generate_timelapse_gif function."""

    def test_generates_gif_from_jpegs(self, tmp_path: Path) -> None:
        """3 JPEGs produce a GIF with 3 frames."""
        paths = []
        for i in range(3):
            p = str(tmp_path / f"snap_{i}.jpg")
            _create_jpeg(p, color=_COLORS[i])
            paths.append(p)

        output = str(tmp_path / "timelapse.gif")
        result = generate_timelapse_gif(paths, output)

        assert result == output
        assert Path(output).exists()

        from PIL import Image

        gif = Image.open(output)
        assert getattr(gif, "n_frames", 1) == 3

    def test_returns_none_for_single_snapshot(self, tmp_path: Path) -> None:
        """1 JPEG returns None (need at least 2)."""
        p = str(tmp_path / "snap.jpg")
        _create_jpeg(p)
        output = str(tmp_path / "timelapse.gif")
        result = generate_timelapse_gif([p], output)
        assert result is None

    def test_returns_none_for_empty_list(self, tmp_path: Path) -> None:
        """0 paths returns None."""
        output = str(tmp_path / "timelapse.gif")
        result = generate_timelapse_gif([], output)
        assert result is None

    def test_skips_missing_files(self, tmp_path: Path) -> None:
        """Missing files are skipped; remaining images form the GIF."""
        paths = [str(tmp_path / "missing.jpg")]
        for i in range(2):
            p = str(tmp_path / f"snap_{i}.jpg")
            _create_jpeg(p, color=_COLORS[i])
            paths.append(p)

        output = str(tmp_path / "timelapse.gif")
        result = generate_timelapse_gif(paths, output)

        assert result == output
        from PIL import Image

        gif = Image.open(output)
        assert getattr(gif, "n_frames", 1) == 2

    def test_resizes_large_frames(self, tmp_path: Path) -> None:
        """Large images are resized to max_width."""
        paths = []
        for i in range(2):
            p = str(tmp_path / f"snap_{i}.jpg")
            _create_jpeg(p, width=1920, height=1080, color=_COLORS[i])
            paths.append(p)

        output = str(tmp_path / "timelapse.gif")
        result = generate_timelapse_gif(paths, output, max_width=320)
        assert result == output

        from PIL import Image

        gif = Image.open(output)
        assert gif.size[0] == 320
        assert gif.size[1] == pytest.approx(180, abs=1)
