"""
Supply chain QC pipeline: Camera → VLM → Robot.

Continuous loop. Low latency optimized.

Tunable via .env:
  REALTIME_FPS             — max VLM calls per second (default: 2)
  REALTIME_STABILITY_FRAMES — consecutive matching frames before acting (default: 3)
  POST_ACTION_WAIT         — seconds to pause after robot moves (default: 4.0)
  DISPLAY_WINDOW           — show live camera feed with label overlay (default: true)
"""
import os
import time
import threading
from datetime import datetime
from typing import Callable, Optional

import cv2
import numpy as np

from camera import get_camera, capture_latest
from vision import classify_item

_DISPLAY = os.getenv("DISPLAY_WINDOW", "true").lower() in ("true", "1", "yes")

_LABEL_COLORS = {
    "GOOD":    (0, 200, 0),
    "FAULTY":  (0, 0, 220),
    "NOTHING": (120, 120, 120),
}


def _show_frame(frame_bytes: bytes, label: str, raw: str, latency_ms: float) -> None:
    """Decode JPEG bytes and display with label overlay in an OpenCV window."""
    arr = np.frombuffer(frame_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return

    color = _LABEL_COLORS.get(label, (200, 200, 200))
    h, w = img.shape[:2]

    # Semi-transparent banner at the top
    overlay = img.copy()
    cv2.rectangle(overlay, (0, 0), (w, 52), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.55, img, 0.45, 0, img)

    # Label (large)
    cv2.putText(img, label, (10, 38), cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 2, cv2.LINE_AA)

    # Latency
    cv2.putText(img, f"{latency_ms:.0f}ms", (w - 90, 36),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1, cv2.LINE_AA)

    # Raw VLM response (bottom strip, truncated to fit)
    short = raw if len(raw) <= 70 else raw[:67] + "..."
    cv2.rectangle(img, (0, h - 28), (w, h), (0, 0, 0), -1)
    cv2.putText(img, short, (6, h - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                (200, 200, 200), 1, cv2.LINE_AA)

    cv2.imshow("QC Pipeline", img)
    cv2.waitKey(1)

# How long to wait between VLM calls when nothing is happening
_VLM_INTERVAL     = 1.0 / max(1, int(os.getenv("REALTIME_FPS", "2")))
# How many consecutive GOOD frames before acting (avoids false positives)
_STABILITY_FRAMES = max(1, int(os.getenv("REALTIME_STABILITY_FRAMES", "1")))
# How many consecutive FAULTY frames before acting (catches hallucinations)
_FAULTY_FRAMES    = max(1, int(os.getenv("FAULTY_STABILITY_FRAMES", "2")))
# How long to pause captures after the robot executes a move
_POST_ACTION_WAIT = float(os.getenv("POST_ACTION_WAIT", "4.0"))
# How many consecutive NOTHING frames before the streak is cleared (item removed)
_NOTHING_RESET    = max(1, int(os.getenv("NOTHING_RESET_FRAMES", "4")))


def get_robot():
    """Return (move_left, move_right, close) based on config."""
    if os.getenv("ROBOT_ENABLED", "false").lower() in ("true", "1", "yes"):
        from robot.primitives import move_to_left_pile, move_to_right_pile, _player
        return move_to_left_pile, move_to_right_pile, _player.close
    from robot.mock_robot import move_to_left_pile, move_to_right_pile
    return move_to_left_pile, move_to_right_pile, lambda: None


def run_pipeline(
    broadcast: Callable[[dict], None],
    stop_event: Optional[threading.Event] = None,
):
    cap = get_camera()
    if not cap.isOpened():
        broadcast({"event": "error", "message": "Camera failed to open"})
        return

    move_left, move_right, close_robot = get_robot()
    stop = stop_event or threading.Event()
    item_count = 0

    # Stability tracking
    streak_label: str | None = None
    streak_count: int = 0
    nothing_count: int = 0

    # Timing
    next_vlm_time: float = 0.0
    resume_after: float = 0.0

    # Warm up camera buffer
    for _ in range(5):
        cap.read()

    broadcast({"event": "started", "message": "Pipeline running"})
    print(f"[pipeline] Started  |  good={_STABILITY_FRAMES} frames  |  faulty={_FAULTY_FRAMES} frames  |  "
          f"rate=1/{_VLM_INTERVAL:.1f}s  |  post-action wait={_POST_ACTION_WAIT}s")

    while not stop.is_set():
        now = time.perf_counter()

        # Post-action cooldown — arm is moving or box needs to be refilled
        if now < resume_after:
            time.sleep(0.2)
            continue

        # VLM rate limiter
        if now < next_vlm_time:
            time.sleep(next_vlm_time - now)
            continue

        frame = capture_latest(cap)
        if not frame:
            time.sleep(0.01)
            continue

        try:
            label, latency_sec, raw = classify_item(frame)
        except Exception as e:
            broadcast({"event": "error", "message": str(e)})
            print(f"[VLM ERROR] {e}")
            time.sleep(2)
            continue
        finally:
            next_vlm_time = time.perf_counter() + _VLM_INTERVAL

        if _DISPLAY:
            _show_frame(frame, label, raw, latency_sec * 1000)

        ts = datetime.now().strftime("%H:%M:%S")

        if label == "NOTHING":
            nothing_count += 1
            print(f"\r[{ts}] · NOTHING x{nothing_count}  ({latency_sec*1000:.0f}ms)", end="", flush=True)
            broadcast({"event": "item_nothing", "item_id": item_count,
                       "label": label, "raw_response": raw,
                       "latency_ms": round(latency_sec * 1000, 1), "action": None})
            # Only clear the streak once the box is clearly empty for several frames
            if nothing_count >= _NOTHING_RESET and streak_label is not None:
                print()
                streak_label = None
                streak_count = 0
            continue

        # Item visible — reset nothing counter
        nothing_count = 0
        is_faulty = label == "FAULTY"
        required = _FAULTY_FRAMES if is_faulty else _STABILITY_FRAMES

        # Accumulate consecutive matching frames
        if label == streak_label:
            streak_count += 1
        else:
            if streak_label is not None:
                print()
            streak_label = label
            streak_count = 1

        if streak_count < required:
            tag = "FAULTY" if is_faulty else "GOOD"
            print(f"\r[{ts}]  {tag}  {streak_count}/{required}  ({latency_sec*1000:.0f}ms)  \"{raw}\"",
                  end="", flush=True)
            continue

        print()
        streak_label = None
        streak_count = 0

        # Confirmed — act
        item_count += 1
        action = "right_pick" if is_faulty else "left_pick"

        print(f"[{ts}] #{item_count:04d}  {label:<6}  ({latency_sec*1000:.0f}ms)  -> {action}  \"{raw}\"")

        payload = {
            "event": "item_processed",
            "item_id": item_count,
            "label": label,
            "raw_response": raw,
            "latency_ms": round(latency_sec * 1000, 1),
            "action": action,
        }
        broadcast(payload)

        if is_faulty:
            move_left()
        else:
            move_right()

        resume_after = time.perf_counter() + _POST_ACTION_WAIT

    close_robot()
    if _DISPLAY:
        cv2.destroyAllWindows()
