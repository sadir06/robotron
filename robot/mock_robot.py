"""Mock robot for testing without SO-101 hardware. Blocks until move complete."""
import time

_MOCK_MOVE_DURATION = 0.5  # Simulate robot taking 0.5s per move


def move_to_left_pile():
    """Simulate moving to left pile (faulty). Blocks until complete."""
    print("🤖 Robot: Moving to LEFT pile (faulty)...")
    time.sleep(_MOCK_MOVE_DURATION)
    print("🤖 Robot: Move complete.")


def move_to_right_pile():
    """Simulate moving to right pile (good). Blocks until complete."""
    print("🤖 Robot: Moving to RIGHT pile (good)...")
    time.sleep(_MOCK_MOVE_DURATION)
    print("🤖 Robot: Move complete.")
