"""
Supply chain QC pipeline: Camera → VLM → Robot.

Continuous loop. Low latency optimized.
"""
import os
import time
import threading
import asyncio
from typing import Callable, Optional

from camera import get_camera, capture_latest
from vision import classify_item


def get_robot():
    """Return real or mock robot based on config."""
    if os.getenv("ROBOT_ENABLED", "false").lower() in ("true", "1", "yes"):
        from robot.primitives import move_to_left_pile, move_to_right_pile
        return move_to_left_pile, move_to_right_pile
    from robot.mock_robot import move_to_left_pile, move_to_right_pile
    return move_to_left_pile, move_to_right_pile


def run_pipeline(
    broadcast: Callable[[dict], None],
    stop_event: Optional[threading.Event] = None,
):
    """
    Main loop. Runs in background thread.
    - Captures frame
    - VLM classifies FAULTY vs GOOD
    - Robot moves to left (faulty) or right (good)
    - Broadcasts status over WebSocket
    """
    cap = get_camera()
    if not cap.isOpened():
        broadcast({"event": "error", "message": "Camera failed to open"})
        return
    move_left, move_right = get_robot()
    stop = stop_event or threading.Event()
    item_count = 0

    # Warm up
    for _ in range(5):
        cap.read()

    broadcast({"event": "started", "message": "Pipeline running"})

    while not stop.is_set():
        frame = capture_latest(cap)
        if not frame:
            time.sleep(0.01)
            continue

        try:
            label, latency_sec, raw_response = classify_item(frame)
        except Exception as e:
            broadcast({"event": "error", "message": str(e)})
            time.sleep(1)
            continue

        payload = {
            "event": "item_processed" if label != "NOTHING" else "item_nothing",
            "item_id": item_count + 1 if label != "NOTHING" else item_count,
            "label": label,
            "raw_response": raw_response,
            "latency_ms": round(latency_sec * 1000, 1),
        }

        if label == "NOTHING":
            payload["action"] = None
            broadcast(payload)
            continue

        item_count += 1
        is_faulty = label == "FAULTY"
        payload["action"] = "left" if is_faulty else "right"

        if is_faulty:
            move_left()
        else:
            move_right()

        broadcast(payload)
