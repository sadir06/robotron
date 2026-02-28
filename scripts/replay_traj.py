#!/usr/bin/env python
"""
Replay a recorded trajectory on the follower arm.

The arm first moves smoothly to the trajectory's starting position, then
executes the recording at the original speed (or scaled with --speed).

Usage:
    python scripts/replay_traj.py --port COM3 --input trajectory.json
    python scripts/replay_traj.py --port COM3 --input trajectories/demo.json --speed 0.5
    python scripts/replay_traj.py --port COM3 --input traj.json --loop --approach-duration 5
"""

import argparse
import json
import signal
import sys
import time
from pathlib import Path

# Auto-add the lerobot venv site-packages so no manual activation is needed.
_repo_root = Path(__file__).resolve().parent.parent
for _candidate in [
    _repo_root / "lerobot" / ".venv" / "Lib" / "site-packages",   # Windows
    _repo_root / "lerobot" / ".venv" / "lib" / "python3.10" / "site-packages",  # Linux
    _repo_root / "lerobot" / "src",  # editable install fallback
]:
    if _candidate.exists() and str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))


def lerp_positions(a: dict, b: dict, alpha: float) -> dict:
    """Linearly interpolate between two position dicts (keys: '<motor>.pos')."""
    return {k: a[k] + (b[k] - a[k]) * alpha for k in a}


def move_to_position(robot, target: dict, duration: float, hz: float = 50.0) -> None:
    """Smoothly move from the current position to `target` over `duration` seconds.

    Args:
        robot: Connected SOFollower instance.
        target: Dict of {<motor>.pos: value} for the desired end position.
        duration: Time in seconds for the approach motion.
        hz: Control loop rate during approach (default: 50 Hz).
    """
    if duration <= 0:
        robot.send_action(target)
        return

    current_raw = robot.bus.sync_read("Present_Position")
    current = {f"{k}.pos": v for k, v in current_raw.items()}

    steps = max(1, int(duration * hz))
    dt = duration / steps

    for i in range(1, steps + 1):
        alpha = i / steps
        interp = lerp_positions(current, target, alpha)
        robot.send_action(interp)
        time.sleep(dt)


_TRAJ_DIR = Path(__file__).resolve().parent.parent / "trajectories"


def main():
    parser = argparse.ArgumentParser(
        description="Replay a recorded follower arm trajectory"
    )
    parser.add_argument(
        "--port", required=True,
        help="Serial port of the arm (e.g. COM3 or /dev/ttyUSB0)",
    )
    parser.add_argument(
        "--robot-type", default="so100_follower",
        choices=["so100_follower", "so101_follower"],
        help="Robot model type (default: so100_follower)",
    )
    parser.add_argument(
        "--robot-id", default="my_follower",
        help="Robot ID used for calibration file lookup (default: my_follower)",
    )

    # Direction shortcuts or explicit file path (mutually exclusive)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--left",       action="store_true", help="Replay trajectories/left.json")
    source.add_argument("--up",         action="store_true", help="Replay trajectories/up.json")
    source.add_argument("--right",      action="store_true", help="Replay trajectories/right.json")
    source.add_argument("--left-pick",  action="store_true", help="Replay trajectories/left_pick.json")
    source.add_argument("--right-pick", action="store_true", help="Replay trajectories/right_pick.json")
    source.add_argument("--input", help="Explicit trajectory JSON file path")

    parser.add_argument(
        "--speed", type=float, default=1.0,
        help="Playback speed multiplier — 0.5 = half speed, 2.0 = double (default: 1.0)",
    )
    parser.add_argument(
        "--approach-duration", type=float, default=3.0,
        help="Seconds to smoothly move to the start position (default: 3.0, 0 = jump directly)",
    )
    parser.add_argument(
        "--loop", action="store_true",
        help="Loop the trajectory continuously until Ctrl+C",
    )
    args = parser.parse_args()

    if args.left:
        input_path = _TRAJ_DIR / "left.json"
    elif args.up:
        input_path = _TRAJ_DIR / "up.json"
    elif args.right:
        input_path = _TRAJ_DIR / "right.json"
    elif args.left_pick:
        input_path = _TRAJ_DIR / "left_pick.json"
    elif args.right_pick:
        input_path = _TRAJ_DIR / "right_pick.json"
    else:
        input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: trajectory file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    trajectory = json.loads(input_path.read_text())
    frames = trajectory["frames"]
    recorded_hz = trajectory["hz"]
    motors = trajectory["motors"]

    if not frames:
        print("Error: trajectory file contains no frames.", file=sys.stderr)
        sys.exit(1)

    total_duration = frames[-1]["t"]
    print(f"Loaded {len(frames)} frames  |  {recorded_hz} Hz  |  {total_duration:.2f}s  |  motors: {motors}")
    print(f"Playback speed: {args.speed}x  →  effective duration: {total_duration / args.speed:.2f}s")

    from lerobot.robots.so_follower import SOFollower
    from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

    config = SOFollowerRobotConfig(
        port=args.port,
        id=args.robot_id,
        disable_torque_on_disconnect=True,
    )
    robot = SOFollower(config)

    running = True

    def _stop(sig, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, _stop)

    print(f"\nConnecting to {args.robot_type} on {args.port} ...")
    robot.connect(calibrate=True)

    # Extract the first frame's joint positions as the approach target.
    first_frame = {k: v for k, v in frames[0].items() if k != "t"}

    if args.approach_duration > 0:
        print(f"Moving to start position over {args.approach_duration:.1f}s ...")
        move_to_position(robot, first_frame, duration=args.approach_duration)
        print("Reached start position.")
    else:
        robot.send_action(first_frame)

    iteration = 0
    try:
        while running:
            iteration += 1
            if args.loop:
                print(f"\n--- Replay iteration {iteration} ---")
            else:
                print("\nStarting replay  (press Ctrl+C to abort) ...")

            t_replay_start = time.perf_counter()

            for i, frame in enumerate(frames):
                if not running:
                    break

                # When this frame should be sent, scaled by speed
                target_t = frame["t"] / args.speed
                now = time.perf_counter()
                wait = target_t - (now - t_replay_start)
                if wait > 0:
                    time.sleep(wait)

                action = {k: v for k, v in frame.items() if k != "t"}
                robot.send_action(action)

                print(
                    f"\r  frame={i + 1:5d}/{len(frames)}"
                    f"  t={frame['t']:6.2f}s / {total_duration:.2f}s",
                    end="", flush=True,
                )

            print()  # newline after \r line

            if not args.loop:
                break

    finally:
        robot.disconnect()

    print("Replay complete.")


if __name__ == "__main__":
    main()
