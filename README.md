# Publisher Template for Python

Motion-triggered image publisher for Make87.

This module captures frames from a Raspberry Pi camera, detects motion using
an adaptive background model, and publishes JPEG images on the
``change_detector/images`` topic whenever motion is detected.