"""
SO-101 robot arm primitives for supply chain sorting.

Placeholder implementations — replace with actual LeRobot/calibration when hardware is ready.
- move_to_left_pile:  Move faulty/defective items left
- move_to_right_pile: Move good items right
"""
import time


def move_to_left_pile():
    """
    Execute script: move current item to the LEFT pile (faulty/defective).
    PLACEHOLDER — implement with SO-101 calibration + LeRobot.
    """
    # TODO: Connect to SO-101, run pick → move left → place
    print("🤖 ROBOT: Moving item to LEFT pile (faulty)")


def move_to_right_pile():
    """
    Execute script: move current item to the RIGHT pile (good).
    PLACEHOLDER — implement with SO-101 calibration + LeRobot.
    """
    # TODO: Connect to SO-101, run pick → move right → place
    print("🤖 ROBOT: Moving item to RIGHT pile (good)")
