"""
SO-101 robot arm primitives for supply chain sorting.

GOOD item  → left_pick  trajectory
FAULTY item → right_pick trajectory

Configure via environment variables:
  FOLLOWER_PORT  — serial port  (default: COM3)
  FOLLOWER_ID    — calibration ID (default: my_follower)
  APPROACH_DURATION — seconds to move to traj start (default: 2.0)
"""
import os
from robot.trajectory_player import TrajectoryPlayer

_player = TrajectoryPlayer(
    port=os.getenv("FOLLOWER_PORT", "COM3"),
    robot_id=os.getenv("FOLLOWER_ID", "my_follower"),
    approach_duration=float(os.getenv("APPROACH_DURATION", "2.0")),
)


def move_to_left_pile():
    """FAULTY item — replay right_pick trajectory."""
    print("[robot] FAULTY → right_pick")
    _player.replay("right_pick")


def move_to_right_pile():
    """GOOD item — replay left_pick trajectory."""
    print("[robot] GOOD → left_pick")
    _player.replay("left_pick")
