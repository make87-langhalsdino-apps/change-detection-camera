from __future__ import annotations

"""Motion-triggered image publisher for Make87.

This module captures frames from a Raspberry Pi camera, detects motion using
an adaptive background model, and publishes JPEG images on the
``change_detector/images`` topic whenever motion is detected.
"""

import time
from typing import Final, Tuple

import cv2
import numpy as np
from picamera2 import Picamera2
import make87
from make87.topics import get_publisher
from make87_messages.image.compressed.image_jpeg import ImageJPEG

# Configuration ----------------------------------------------------------------
RESOLUTION: Final[Tuple[int, int]] = (640, 480)
FRAME_RATE_LIMIT_S: Final[float] = 0.2
MOTION_PIXEL_THRESHOLD: Final[int] = 1_000
PUBLISH_INTERVAL_S: Final[float] = 1.0
TOPIC_NAME: Final[str] = "DETECTED_CHANGED_IMAGE"


# Helpers ----------------------------------------------------------------------

def init_camera(resolution: tuple[int, int]) -> Picamera2:
    """Configure and start the PiCamera.

    Args:
        resolution: Desired frame size as ``(width, height)`` in pixels.

    Returns:
        A ready-to-use :class:`Picamera2` instance.
    """
    camera = Picamera2()
    camera_config = camera.create_video_configuration(main={"size": resolution})
    camera.configure(camera_config)
    camera.start()
    return camera


def motion_mask(frame: np.ndarray, subtractor: cv2.BackgroundSubtractor) -> np.ndarray:
    """Compute a foreground mask highlighting motion areas.

    Args:
        frame: Current video frame (BGR).
        subtractor: Background-subtractor instance.

    Returns:
        Binary mask where moving pixels are non-zero.
    """
    return subtractor.apply(frame)


def has_motion(mask: np.ndarray, threshold: int) -> bool:
    """Return ``True`` when *mask* contains significant motion.

    Args:
        mask: Foreground mask returned from :func:`motion_mask`.
        threshold: Minimum number of changed pixels.
    """
    return int(cv2.countNonZero(mask)) > threshold


def encode_jpeg(frame: np.ndarray) -> bytes | None:
    """Encode *frame* to JPEG.

    Args:
        frame: Image to encode.

    Returns:
        JPEG bytes on success; ``None`` otherwise.
    """
    success, buffer = cv2.imencode(".jpg", frame)
    return buffer.tobytes() if success else None


def main() -> None:
    """Run the motion-triggered publisher."""
    make87.initialize()
    camera = init_camera(RESOLUTION)
    subtractor = cv2.createBackgroundSubtractorMOG2()
    publisher = get_publisher(name=TOPIC_NAME, message_type=ImageJPEG)

    last_publish: float = 0.0

    try:
        while True:
            frame = camera.capture_array()
            if frame is None:  # Camera hiccup; skip this iteration.
                continue

            mask = motion_mask(frame, subtractor)
            if not has_motion(mask, MOTION_PIXEL_THRESHOLD):
                time.sleep(FRAME_RATE_LIMIT_S)
                continue

            now = time.time()
            if now - last_publish < PUBLISH_INTERVAL_S:
                time.sleep(FRAME_RATE_LIMIT_S)
                continue

            encoded = encode_jpeg(frame)
            if encoded is None:
                continue

            publisher.publish(ImageJPEG(data=encoded))
            last_publish = now
            time.sleep(FRAME_RATE_LIMIT_S)
    finally:
        camera.stop()


if __name__ == "__main__":
    main()
