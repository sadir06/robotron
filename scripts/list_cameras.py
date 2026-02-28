"""
List available cameras. Use this to find your external camera index.

  python scripts/list_cameras.py

Index 0 = default (often built-in). Index 1, 2, 3... = USB/external cameras.
Set CAMERA_INDEX in .env to use a specific camera.
"""
import cv2

print("Scanning for cameras (0-9)...\n")
for i in range(10):
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        print(f"  Camera {i}: available ({w}x{h})")
    else:
        cap.release()
print("\nSet CAMERA_INDEX in .env to your camera number (e.g. CAMERA_INDEX=1)")
