#!/usr/bin/env python
"""
Record a directional trajectory via teleoperation (leader → follower).

Move the leader arm by hand; the follower mirrors it in real-time and the
motion is saved as a named trajectory for later replay.

Usage:
    python scripts/record_teleop.py --left  --leader-port COM3 --follower-port COM4
    python scripts/record_teleop.py --up    --leader-port COM3 --follower-port COM4
    python scripts/record_teleop.py --right --leader-port COM3 --follower-port COM4

    # Optional overrides:
    python scripts/record_teleop.py --left --leader-port COM3 --follower-port COM4 \\
        --hz 50 --output-dir trajectories --leader-id my_leader --follower-id my_follower

Output:
    trajectories/left.json   (or up.json / right.json)
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
    _repo_root / "lerobot" / ".venv" / "Lib" / "site-packages",          # Windows
    _repo_root / "lerobot" / ".venv" / "lib" / "python3.10" / "site-packages",  # Linux
    _repo_root / "lerobot" / "src",                                        # editable fallback
]:
    if _candidate.exists() and str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))


def main():
    parser = argparse.ArgumentParser(
        description="Teleop-record a directional trajectory (leader arm → follower arm)"
    )

    # Direction — mutually exclusive flags
    direction_group = parser.add_mutually_exclusive_group(required=True)
    direction_group.add_argument("--left",       action="store_true", help="Record the 'push left' trajectory")
    direction_group.add_argument("--up",         action="store_true", help="Record the 'push up' trajectory")
    direction_group.add_argument("--right",      action="store_true", help="Record the 'push right' trajectory")
    direction_group.add_argument("--left-pick",  action="store_true", help="Record the 'left pick' trajectory")
    direction_group.add_argument("--right-pick", action="store_true", help="Record the 'right pick' trajectory")

    # Ports
    parser.add_argument("--leader-port",   required=True, help="Serial port for the leader arm (e.g. COM3)")
    parser.add_argument("--follower-port", required=True, help="Serial port for the follower arm (e.g. COM4)")

    # Optional
    parser.add_argument("--leader-type",   default="so100_leader",   choices=["so100_leader", "so101_leader"])
    parser.add_argument("--follower-type", default="so100_follower",  choices=["so100_follower", "so101_follower"])
    parser.add_argument("--leader-id",     default="my_leader",   help="Leader calibration ID (default: my_leader)")
    parser.add_argument("--follower-id",   default="my_follower", help="Follower calibration ID (default: my_follower)")
    parser.add_argument("--hz",            type=float, default=30.0, help="Control/recording rate in Hz (default: 30)")
    parser.add_argument("--duration",      type=float, default=None, help="Max recording duration in seconds (default: until Ctrl+C)")
    parser.add_argument("--output-dir",    default="trajectories", help="Directory to save trajectory files (default: trajectories/)")

    args = parser.parse_args()

    # Resolve direction label
    if args.left:
        direction = "left"
    elif args.up:
        direction = "up"
    elif args.right:
        direction = "right"
    elif args.left_pick:
        direction = "left_pick"
    else:
        direction = "right_pick"

    from lerobot.robots.so_follower import SOFollower
    from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig
    from lerobot.teleoperators.so_leader import SOLeader
    from lerobot.teleoperators.so_leader.config_so_leader import SOLeaderTeleopConfig

    leader_config = SOLeaderTeleopConfig(
        port=args.leader_port,
        id=args.leader_id,
    )
    follower_config = SOFollowerRobotConfig(
        port=args.follower_port,
        id=args.follower_id,
        disable_torque_on_disconnect=True,
    )

    leader   = SOLeader(leader_config)
    follower = SOFollower(follower_config)

    frames   = []
    running  = False   # set True when user presses Enter to begin
    stopping = False   # set True when user presses Enter to stop

    def _sigint(sig, frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, _sigint)

    # Background thread: first Enter starts, second Enter stops.
    def _watch_enter():
        nonlocal running, stopping
        input()          # wait for first Enter
        running = True
        input()          # wait for second Enter
        stopping = True

    import threading
    enter_thread = threading.Thread(target=_watch_enter, daemon=True)

    print(f"Direction : {direction.upper()}")
    print(f"Connecting leader   ({args.leader_type})   on {args.leader_port} ...")
    leader.connect(calibrate=True)

    print(f"Connecting follower ({args.follower_type}) on {args.follower_port} ...")
    follower.connect(calibrate=True)

    motor_names = list(leader.bus.motors.keys())

    # Teleop loop runs even before recording so the follower tracks the leader
    # while the user positions the arm before hitting Enter.
    enter_thread.start()
    print()
    print("Position the arm, then press ENTER to start recording.")
    print("Press ENTER again (or Ctrl+C) to stop.")
    if args.duration:
        print(f"Will also stop automatically after {args.duration:.1f}s of recording.")
    print()

    dt = 1.0 / args.hz
    t_start = None
    t_next  = time.perf_counter()

    try:
        while not stopping:
            now = time.perf_counter()
            sleep_for = t_next - now
            if sleep_for > 0:
                time.sleep(sleep_for)
                now = time.perf_counter()

            # Always mirror leader → follower (even before recording starts)
            action = leader.get_action()
            follower.send_action(action)

            if running:
                if t_start is None:
                    t_start = now
                    print("  Recording started!\n")

                elapsed = now - t_start
                frame = {"t": round(elapsed, 6)}
                frame.update({k: round(v, 4) for k, v in action.items()})
                frames.append(frame)

                pos_str = "  ".join(f"{k.split('.')[0]}={v:7.2f}" for k, v in action.items())
                print(f"\r  [{direction}]  t={elapsed:6.2f}s  frames={len(frames):5d}  [{pos_str}]",
                      end="", flush=True)

                if args.duration is not None and elapsed >= args.duration:
                    stopping = True

            t_next += dt

    finally:
        print()
        follower.disconnect()
        leader.disconnect()

    if not frames:
        print("No frames recorded — exiting.")
        return

    total_t = frames[-1]["t"]
    actual_hz = len(frames) / total_t if total_t > 0 else 0
    print(f"Recorded {len(frames)} frames over {total_t:.2f}s  ({actual_hz:.1f} Hz actual).")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{direction}.json"

    trajectory = {
        "direction":     direction,
        "leader_type":   args.leader_type,
        "follower_type": args.follower_type,
        "leader_port":   args.leader_port,
        "follower_port": args.follower_port,
        "hz":            args.hz,
        "motors":        motor_names,
        "frames":        frames,
    }
    output_path.write_text(json.dumps(trajectory, indent=2))
    print(f"Saved to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
