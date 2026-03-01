#!/usr/bin/env python
"""
Record a trajectory by manually guiding the follower arm (kinesthetic teaching).

Torque is disabled during recording so the arm can be backdriven freely by hand.
Joint positions are sampled at a fixed rate and saved as a JSON file for replay.

Usage:
    python scripts/record_traj.py --port COM3
    python scripts/record_traj.py --port /dev/ttyUSB0 --hz 50 --duration 15 --output trajectories/demo.json
    python scripts/record_traj.py --port COM3 --robot-type so101_follower --robot-id my_arm
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


def main():
    parser = argparse.ArgumentParser(
        description="Record follower arm trajectory via hand guiding (torque-off)"
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
    parser.add_argument(
        "--hz", type=float, default=30.0,
        help="Sampling frequency in Hz (default: 30)",
    )
    parser.add_argument(
        "--duration", type=float, default=None,
        help="Max recording duration in seconds (default: run until Ctrl+C)",
    )
    parser.add_argument(
        "--output", default="trajectory.json",
        help="Output trajectory file path (default: trajectory.json)",
    )
    args = parser.parse_args()

    from lerobot.robots.so_follower import SOFollower
    from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

    config = SOFollowerRobotConfig(
        port=args.port,
        id=args.robot_id,
        disable_torque_on_disconnect=True,
    )
    robot = SOFollower(config)

    frames = []
    running = True

    def _stop(sig, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, _stop)

    print(f"Connecting to {args.robot_type} on {args.port} ...")
    robot.connect(calibrate=True)
    motor_names = list(robot.bus.motors.keys())

    print("Disabling torque — you can now move the arm freely by hand.")
    robot.bus.disable_torque()

    print(f"Sampling at {args.hz:.1f} Hz.  Press Ctrl+C to stop.")
    if args.duration:
        print(f"Will stop automatically after {args.duration:.1f}s.")
    print()

    dt = 1.0 / args.hz
    t_start = time.perf_counter()
    t_next = t_start

    try:
        while running:
            now = time.perf_counter()
            sleep_for = t_next - now
            if sleep_for > 0:
                time.sleep(sleep_for)
                now = time.perf_counter()

            positions = robot.bus.sync_read("Present_Position")

            frame = {"t": round(now - t_start, 6)}
            frame.update({f"{k}.pos": round(v, 4) for k, v in positions.items()})
            frames.append(frame)

            elapsed = now - t_start
            pos_str = "  ".join(f"{k}={v:7.2f}" for k, v in positions.items())
            print(f"\r  t={elapsed:6.2f}s  frames={len(frames):5d}  [{pos_str}]", end="", flush=True)

            if args.duration is not None and elapsed >= args.duration:
                running = False

            t_next += dt

    finally:
        print()  # newline after \r line

        # Before re-enabling torque, write current position as goal so the arm
        # doesn't snap to a stale goal_position value.
        if frames:
            goal = {k: v for k, v in frames[-1].items() if k != "t"}
            goal_raw = {k.removesuffix(".pos"): v for k, v in goal.items()}
            robot.bus.sync_write("Goal_Position", goal_raw)

        robot.bus.enable_torque()
        robot.disconnect()

    if not frames:
        print("No frames recorded — exiting.")
        return

    duration = frames[-1]["t"]
    print(f"Recorded {len(frames)} frames over {duration:.2f}s  ({len(frames)/duration:.1f} Hz actual).")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    trajectory = {
        "robot_type": args.robot_type,
        "port": args.port,
        "hz": args.hz,
        "motors": motor_names,
        "frames": frames,
    }
    output.write_text(json.dumps(trajectory, indent=2))
    print(f"Saved to: {output.resolve()}")


if __name__ == "__main__":
    main()
