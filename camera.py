"""
Continuous video capture for supply chain QC.

Streams frames from 3rd-person / external USB camera. Optimized for:
- Live video (minimal buffering, always latest frame)
- External cameras via CAMERA_INDEX
"""
import os
import time
from typing import Iterator, Optional

import cv2


def get_camera(
    index: int = None,
    width: int = None,
    height: int = None,
) -> cv2.VideoCapture:
    """
    Open camera. Uses CAMERA_INDEX from .env for external cameras.
    Index 0 = default (often built-in), 1/2/3 = USB cameras.
    Run: python scripts/list_cameras.py to find your camera index.
    """
    index = index if index is not None else int(os.getenv("CAMERA_INDEX", "0"))
    width = width or int(os.getenv("CAMERA_WIDTH", "640"))
    height = height or int(os.getenv("CAMERA_HEIGHT", "480"))
    # Windows: CAP_DSHOW often works better with USB cameras
    if os.name == "nt":
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(index)
    else:
        cap = cv2.VideoCapture(index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimal buffer = lowest latency
    cap.set(cv2.CAP_PROP_FPS, 30)  # Request 30fps for smooth video
    return cap


def frame_generator(
    cap: cv2.VideoCapture,
    encode_jpeg: bool = True,
    quality: int = 85,
) -> Iterator[bytes]:
    """
    Yield JPEG-encoded frames from continuous video stream.
    Drains buffer so we always get the latest frame (not stale).
    """
    params = [cv2.IMWRITE_JPEG_QUALITY, quality]
    while True:
        for _ in range(4):
            cap.grab()
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.005)
            continue
        if encode_jpeg:
            _, buf = cv2.imencode(".jpg", frame, params)
            yield buf.tobytes()
        else:
            yield frame


def capture_latest(cap: cv2.VideoCapture) -> Optional[bytes]:
    """
    Grab the most recent frame from the live video stream.
    Drains buffer to avoid processing old frames.
    """
    for _ in range(4):
        cap.grab()
    ret, frame = cap.read()
    if not ret:
        return None
    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return buf.tobytes()
