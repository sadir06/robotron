"""
Continuous video capture for supply chain QC.

Streams frames from 3rd-person / external USB camera. Optimized for:
- Live video (minimal buffering, always latest frame)
- External cameras via CAMERA_INDEX

Image enhancement (applied before every VLM call):
  CAMERA_CLAHE=true       — adaptive contrast (CLAHE), default: true
  CAMERA_SHARPEN=true     — unsharp mask sharpening, default: true
  CAMERA_BRIGHTNESS=0     — brightness offset -255..255, default: 0
  CAMERA_EXPOSURE=-5      — manual exposure (CAP_DSHOW), leave unset for auto
"""
import os
import time
import threading
from typing import Iterator, Optional

import cv2
import numpy as np

_CLAHE_ON   = os.getenv("CAMERA_CLAHE",   "true").lower() in ("true", "1", "yes")
_SHARPEN_ON = os.getenv("CAMERA_SHARPEN", "true").lower() in ("true", "1", "yes")
_BRIGHTNESS = int(os.getenv("CAMERA_BRIGHTNESS", "0"))

# CLAHE object is expensive to create — build once
_clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))

# Background reader — continuously pulls frames so capture_latest always gets
# the freshest one, even after a multi-second VLM call.
_latest_raw: Optional[np.ndarray] = None
_frame_lock = threading.Lock()


def _reader_loop(cap: cv2.VideoCapture) -> None:
    global _latest_raw
    while True:
        ret, frame = cap.read()
        if ret:
            with _frame_lock:
                _latest_raw = frame


def _enhance(frame: np.ndarray) -> np.ndarray:
    """Apply brightness correction, CLAHE, and sharpening to a BGR frame."""
    # 1. Brightness offset (simple, no gamma)
    if _BRIGHTNESS != 0:
        frame = cv2.convertScaleAbs(frame, alpha=1.0, beta=_BRIGHTNESS)

    # 2. CLAHE on luminance only (preserves colour, lifts local contrast)
    if _CLAHE_ON:
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l = _clahe.apply(l)
        frame = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)

    # 3. Unsharp mask — makes blurry details crisper
    if _SHARPEN_ON:
        blurred = cv2.GaussianBlur(frame, (0, 0), 3)
        frame = cv2.addWeighted(frame, 1.6, blurred, -0.6, 0)

    return frame


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
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_FPS, 30)

    # Optional manual exposure (set CAMERA_EXPOSURE=-5 in .env to try)
    exposure = os.getenv("CAMERA_EXPOSURE", "").strip()
    if exposure:
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # switch to manual mode
        cap.set(cv2.CAP_PROP_EXPOSURE, float(exposure))

    # Start background reader so capture_latest always returns the freshest frame
    t = threading.Thread(target=_reader_loop, args=(cap,), daemon=True)
    t.start()

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
        frame = _enhance(frame)
        if encode_jpeg:
            _, buf = cv2.imencode(".jpg", frame, params)
            yield buf.tobytes()
        else:
            yield frame


def capture_latest(cap: cv2.VideoCapture) -> Optional[bytes]:
    """
    Return the most recent frame from the background reader thread.
    Always fresh — no stale frames after long VLM calls.
    """
    with _frame_lock:
        frame = _latest_raw
    if frame is None:
        return None
    frame = _enhance(frame.copy())
    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return buf.tobytes()
