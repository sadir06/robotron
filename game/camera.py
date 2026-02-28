"""
Camera module — captures the board image.
Supports: live webcam, image file, or interactive file picker.
"""
import os
import sys
from pathlib import Path


def capture_board(source: str = "camera") -> bytes:
    """
    Capture an image of the tic-tac-toe board.
    
    Args:
        source: "camera" for live webcam, or a file path for testing
    
    Returns:
        JPEG image bytes
    """
    if source != "camera":
        # Load from file
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")
        print(f"📷 Loading board image from: {path}")
        return path.read_bytes()
    
    # Live camera capture
    try:
        import cv2
    except ImportError:
        print("⚠️  OpenCV not installed. Install with: pip install opencv-python")
        print("   Falling back to file input mode.")
        return _prompt_for_file()
    
    camera_index = int(os.getenv("CAMERA_INDEX", "0"))
    width = int(os.getenv("CAMERA_WIDTH", "1280"))
    height = int(os.getenv("CAMERA_HEIGHT", "720"))
    
    cap = cv2.VideoCapture(camera_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    
    if not cap.isOpened():
        print("⚠️  Cannot open camera. Falling back to file input.")
        cap.release()
        return _prompt_for_file()
    
    # Show preview and wait for capture
    print("📷 Camera ready. Press SPACE to capture, Q to quit.")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Draw grid overlay to help positioning
        h, w = frame.shape[:2]
        cv2.putText(frame, "Press SPACE to capture board", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        cv2.imshow("NemesisTTT - Board Capture", frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord(" "):
            # Capture!
            _, jpeg = cv2.imencode(".jpg", frame)
            cap.release()
            cv2.destroyAllWindows()
            print("📷 Board captured!")
            return jpeg.tobytes()
        elif key == ord("q"):
            cap.release()
            cv2.destroyAllWindows()
            sys.exit(0)
    
    cap.release()
    cv2.destroyAllWindows()
    raise RuntimeError("Camera capture failed")


def capture_board_auto() -> bytes:
    """
    Auto-capture without preview (for automated game loop).
    Takes a single frame and returns it.
    """
    try:
        import cv2
    except ImportError:
        return _prompt_for_file()
    
    camera_index = int(os.getenv("CAMERA_INDEX", "0"))
    cap = cv2.VideoCapture(camera_index)
    
    if not cap.isOpened():
        return _prompt_for_file()
    
    # Warm up camera (first few frames are often dark)
    for _ in range(5):
        cap.read()
    
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        raise RuntimeError("Failed to capture frame")
    
    _, jpeg = cv2.imencode(".jpg", frame)
    return jpeg.tobytes()


def _prompt_for_file() -> bytes:
    """Fallback: ask user to provide an image file path."""
    path = input("📁 Enter path to board image (or drag & drop): ").strip().strip("'\"")
    return Path(path).read_bytes()
