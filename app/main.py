from __future__ import annotations
"""
Motion-triggered image publisher for Make87. 
"""

import logging
import random
import time
from typing import Final, Tuple

import cv2
import numpy as np
from picamera2 import Picamera2

import make87
from make87.interfaces.zenoh import ZenohInterface
from make87_messages.core.header_pb2 import Header
from make87_messages.image.compressed.image_jpeg_pb2 import ImageJPEG

# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------
RESOLUTION: Final[Tuple[int, int]] = (640, 480)
FRAME_RATE_LIMIT_S: Final[float] = 0.2
MOTION_PIXEL_THRESHOLD: Final[int] = 1_000
PUBLISH_INTERVAL_S: Final[float] = 1.0
TOPIC_NAME: Final[str] = "DETECTED_CHANGED_IMAGE"

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger("motion_publisher")


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
def init_camera(resolution: tuple[int, int]) -> Picamera2:
    cam = Picamera2()
    cam_cfg = cam.create_video_configuration(main={"size": resolution})
    cam.configure(cam_cfg)
    cam.start()
    return cam


def motion_mask(frame: np.ndarray, subtractor: cv2.BackgroundSubtractor) -> np.ndarray:
    return subtractor.apply(frame)


def has_motion(mask: np.ndarray, threshold: int) -> bool:
    return int(cv2.countNonZero(mask)) > threshold


def encode_jpeg(frame: np.ndarray, quality: int = 90) -> bytes | None:
    """Encode frame and return raw JPEG bytes (or ``None`` on failure)."""
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return buf.tobytes() if ok else None

def publish(jpeg, publisher):
    header = Header(entity_path="/camera", reference_id=random.randint(0, 9999999999))
    header.timestamp.GetCurrentTime()
    msg = ImageJPEG(header=header, data=jpeg.tobytes())
    message_encoded = make87.encodings.ProtobufEncoder(message_type=ImageJPEG).encode(msg)
    publisher.put(message_encoded)
    log.debug("Published full frame.")

# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------
def main() -> None:
    camera = init_camera(RESOLUTION)
    subtractor = cv2.createBackgroundSubtractorMOG2()
    config = make87.config.load_config_from_env()
    zenoh_interface = ZenohInterface(name="zenoh-client", make87_config=config)
    
    publisher = zenoh_interface.get_publisher(
            name="FULL_FRAME"
    )


    last_publish = 0.0
    log.info("Started motion detector/publisher.")

    try:
        while True:
            frame = camera.capture_array()
            if frame is None:
                continue  # camera hiccup

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
                log.warning("JPEG encode failed – skipping frame.")
                continue

            publish(ImageJPEG(data=encoded), publisher)
            last_publish = now
            log.debug("Published motion frame.")
            time.sleep(FRAME_RATE_LIMIT_S)

    finally:
        camera.stop()
        log.info("Camera stopped.")


if __name__ == "__main__":
    main()
