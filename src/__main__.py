"""Main entry point for mimamori newborn monitoring system.

Usage:
    python -m src                          # One-shot: capture and analyze once
    python -m src --mode periodic          # Periodic: analyze every N seconds
    python -m src --mode web               # Web dashboard with live stream
    python -m src --device 1               # Use camera device index 1
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from dataclasses import replace
from typing import TYPE_CHECKING

from src.analyzer import AnalysisResult, analyze_frame, analyze_frame_gemini
from src.capture import OpenCVCamera, RTSPCamera, encode_frame_to_base64
from src.config import RuntimeConfig, Settings
from src.core import AnalyzerWorker, FrameGrabber, MonitoringState

if TYPE_CHECKING:
    from src.capture.camera import CameraProtocol

logger = logging.getLogger(__name__)


def _call_analyzer(settings: Settings, base64_image: str) -> AnalysisResult:
    """Route analysis to the configured LLM provider.

    Args:
        settings: Application settings.
        base64_image: Base64-encoded JPEG image string.

    Returns:
        AnalysisResult from the selected LLM provider.
    """
    if settings.llm_provider == "gemini":
        return analyze_frame_gemini(
            base64_image=base64_image,
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
        )
    return analyze_frame(
        base64_image=base64_image,
        api_key=settings.openai_api_key,
        model=settings.openai_model,
    )


def _create_camera(settings: Settings) -> CameraProtocol:
    """Create a camera instance based on settings.

    Args:
        settings: Application settings.

    Returns:
        Camera instance (RTSPCamera if camera_url is set, else OpenCVCamera).
    """
    if settings.camera_url:
        logger.info("Using RTSP camera: %s", settings.camera_url)
        return RTSPCamera(url=settings.camera_url)
    logger.info("Using local camera device: %d", settings.camera_device_index)
    return OpenCVCamera(
        device_index=settings.camera_device_index,
        width=settings.capture_width,
        height=settings.capture_height,
    )


def run_web(settings: Settings) -> int:
    """Start the web dashboard with live monitoring.

    Args:
        settings: Application settings.

    Returns:
        Exit code (0 for normal exit).
    """
    import uvicorn

    from src.web.app import create_app

    camera = _create_camera(settings)
    state = MonitoringState()
    runtime_config = RuntimeConfig(
        analysis_interval_seconds=settings.analysis_interval_seconds,
        camera_url=settings.camera_url,
    )

    grabber = FrameGrabber(camera=camera, state=state)
    worker = AnalyzerWorker(
        state=state,
        settings=settings,
        runtime_config=runtime_config,
        analyze_fn=_call_analyzer,
    )

    grabber.start()
    worker.start()

    app = create_app(state=state, runtime_config=runtime_config)

    try:
        logger.info("Starting web dashboard on http://localhost:8000")
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
    finally:
        worker.stop()
        grabber.stop()
        camera.release()

    return 0


def run_once(settings: Settings) -> int:
    """Capture one frame, analyze it, and print the result.

    Args:
        settings: Application settings.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    camera = OpenCVCamera(
        device_index=settings.camera_device_index,
        width=settings.capture_width,
        height=settings.capture_height,
    )
    try:
        frame = camera.read_frame()
        if frame is None:
            logger.error("Failed to capture frame from camera")
            return 1

        base64_image = encode_frame_to_base64(frame)
        result = _call_analyzer(settings, base64_image)

        print(f"[{result.timestamp.isoformat()}] 解析結果:")
        print(f"  姿勢: {result.posture}")
        print(f"  睡眠状態: {result.sleep_state}")
        print(f"  要約: {result.summary}")
        print(f"  信頼度: {result.confidence}")
        if result.anomalies:
            print(f"  異常: {', '.join(result.anomalies)}")
        else:
            print("  異常: なし")
    finally:
        camera.release()

    return 0


def run_periodic(settings: Settings) -> int:
    """Run capture-analyze loop at configured interval.

    Args:
        settings: Application settings.

    Returns:
        Exit code (0 for normal exit, 1 for failure).
    """
    camera = OpenCVCamera(
        device_index=settings.camera_device_index,
        width=settings.capture_width,
        height=settings.capture_height,
    )
    try:
        logger.info(
            "Starting periodic monitoring (interval: %ds). Press Ctrl+C to stop.",
            settings.analysis_interval_seconds,
        )
        while True:
            frame = camera.read_frame()
            if frame is None:
                logger.warning("Failed to capture frame, retrying...")
                time.sleep(1)
                continue

            base64_image = encode_frame_to_base64(frame)
            result = _call_analyzer(settings, base64_image)

            print(f"\n[{result.timestamp.isoformat()}] 解析結果:")
            print(f"  姿勢: {result.posture}")
            print(f"  睡眠状態: {result.sleep_state}")
            print(f"  要約: {result.summary}")
            if result.anomalies:
                print(f"  *** 異常検知: {', '.join(result.anomalies)} ***")

            time.sleep(settings.analysis_interval_seconds)
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user.")
    finally:
        camera.release()

    return 0


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="mimamori - 新生児モニタリングシステム",
    )
    parser.add_argument(
        "--mode",
        choices=["oneshot", "periodic", "web"],
        default="oneshot",
        help="Run mode: oneshot (default), periodic, or web",
    )
    parser.add_argument(
        "--device",
        type=int,
        default=None,
        help="Override camera device index",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    settings = Settings.from_env()
    if args.device is not None:
        settings = replace(settings, camera_device_index=args.device)

    if args.mode == "web":
        exit_code = run_web(settings)
    elif args.mode == "periodic":
        exit_code = run_periodic(settings)
    else:
        exit_code = run_once(settings)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
