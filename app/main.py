"""
Motion-triggered JPEG publisher for Make87.

A tiny daemon that watches the Pi camera, detects motion, and publishes a JPEG
over Zenoh—rate-limited by a configurable FPS ceiling.
"""

from __future__ import annotations

import logging
import random
import time
from typing import Final

import cv2
import numpy as np
from picamera2 import Picamera2

import make87 as m87
from make87.interfaces.zenoh import ZenohInterface
from make87_messages.core.header_pb2 import Header
from make87_messages.image.compressed.image_jpeg_pb2 import ImageJPEG

# ─────────────────────────────────────────  tunables  ──────────────────────────────────────────
RESOLUTION: Final[tuple[int, int]] = (640, 480)
FRAME_SLEEP_S: Final[float] = 0.2            # idle delay between camera reads
PIXEL_THRESHOLD: Final[int] = 1_000          # motion mask pixels that trigger a publish
TOPIC: Final[str] = "DETECTED_CHANGED_IMAGE"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("motion_publisher")


# ─────────────────────────────────────────  helpers  ───────────────────────────────────────────
def start_camera(size: tuple[int, int]) -> Picamera2:
    cam = Picamera2()
    cam.configure(cam.create_video_configuration(main={"size": size}))
    cam.start()
    return cam


def has_motion(mask: np.ndarray, threshold: int) -> bool:
    changed = cv2.countNonZero(mask)
    log.debug("mask changed pixels = %d (limit %d)", changed, threshold)
    return changed > threshold


def encode(frame: np.ndarray) -> bytes | None:
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return buf.tobytes() if ok else None


def publish(jpeg: bytes, pub) -> None:
    header = Header(entity_path="/camera", reference_id=random.randrange(10**10))
    header.timestamp.GetCurrentTime()

    encoded = m87.encodings.ProtobufEncoder(ImageJPEG).encode(ImageJPEG(header=header, data=jpeg))
    pub.put(encoded)
    log.info("✅ published %d bytes", len(jpeg))


# ───────────────────────────────────────────  main  ────────────────────────────────────────────
def main() -> None:
    cam = start_camera(RESOLUTION)
    bg_subtractor = cv2.createBackgroundSubtractorMOG2()

    cfg = m87.config.load_config_from_env()
    fps_limit = float(m87.config.get_config_value(cfg, "trigger_limit_fps", default=0.1) or 0.1)
    min_interval = 1.0 / max(fps_limit, 0.001)

    zenoh = ZenohInterface("zenoh-client", make87_config=cfg)
    pub = zenoh.get_publisher(TOPIC)

    last_sent = 0.0
    log.info("motion publisher running (≤ %.2f fps)", fps_limit)

    try:
        while True:
            frame = cam.capture_array()
            if frame is None:
                time.sleep(FRAME_SLEEP_S)
                continue

            if not has_motion(bg_subtractor.apply(frame), PIXEL_THRESHOLD):
                time.sleep(FRAME_SLEEP_S)
                continue

            now = time.time()
            if now - last_sent < min_interval:
                time.sleep(FRAME_SLEEP_S)
                continue

            jpeg = encode(frame)
            if jpeg:
                publish(jpeg, pub)
                last_sent = now

            time.sleep(FRAME_SLEEP_S)

    finally:
        cam.stop()
        log.info("camera stopped")


if __name__ == "__main__":
    main()
