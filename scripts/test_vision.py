"""
Capture one frame from the camera and run it through the VLM.
Shows the raw response so you can diagnose classification issues.

Usage:
    python scripts/test_vision.py
    python scripts/test_vision.py --save frame.jpg   # also saves the captured image
"""
import argparse
import sys
import numpy as np
import cv2
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # env vars already set, or not needed

from camera import get_camera, capture_latest
from vision import classify_item, _load_prompt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", metavar="PATH", help="Save captured frame to this path")
    parser.add_argument("--loops", type=int, default=1, help="Run N times (default: 1)")
    args = parser.parse_args()

    print("Opening camera...")
    cap = get_camera()
    if not cap.isOpened():
        print("ERROR: Camera failed to open")
        sys.exit(1)

    # Warm up
    for _ in range(5):
        cap.read()

    print(f"\n--- Prompt in use ---\n{_load_prompt()}\n")
    print("-" * 60)

    for i in range(args.loops):
        frame = capture_latest(cap)
        if not frame:
            print("ERROR: Failed to capture frame")
            continue

        if args.save:
            path = args.save if args.loops == 1 else f"{Path(args.save).stem}_{i}{Path(args.save).suffix}"
            Path(path).write_bytes(frame)
            print(f"Frame saved to: {path}")

        # Show the captured frame
        img = cv2.imdecode(np.frombuffer(frame, np.uint8), cv2.IMREAD_COLOR)
        cv2.imshow(f"Frame {i+1}", img)
        cv2.waitKey(1)

        print(f"Sending to VLM... ({len(frame)/1024:.1f} KB)")
        label, latency, raw = classify_item(frame)

        print(f"\nRaw response:\n  {raw!r}")
        print(f"\nParsed label : {label}")
        print(f"Latency      : {latency*1000:.0f}ms")
        print("-" * 60)

        cv2.waitKey(0)  # hold window open until keypress before next shot

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
