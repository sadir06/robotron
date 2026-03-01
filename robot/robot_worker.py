"""
Robot worker process — runs under lerobot's Python 3.10.

Connects to the follower arm once, then accepts replay commands from stdin.
Stays alive between commands so the arm connection is persistent.

Protocol (line-based):
  stdin  → direction name (e.g. "left_pick") or "quit"
  stdout → "READY" once connected, "DONE" after each replay, "ERROR <msg>" on failure
"""
import argparse
import json
import sys
import time
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
for _candidate in [
    _root / "lerobot" / ".venv" / "Lib" / "site-packages",
    _root / "lerobot" / ".venv" / "lib" / "python3.10" / "site-packages",
    _root / "lerobot" / "src",
]:
    if _candidate.exists() and str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

_TRAJ_DIR = _root / "trajectories"


def _lerp(a: dict, b: dict, alpha: float) -> dict:
    return {k: a[k] + (b[k] - a[k]) * alpha for k in a}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", required=True)
    parser.add_argument("--robot-id", default="my_follower")
    parser.add_argument("--approach-duration", type=float, default=2.0)
    args = parser.parse_args()

    from lerobot.robots.so_follower import SOFollower
    from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

    config = SOFollowerRobotConfig(
        port=args.port,
        id=args.robot_id,
        disable_torque_on_disconnect=True,
    )
    robot = SOFollower(config)
    robot.connect(calibrate=True)

    cache: dict[str, list[dict]] = {}

    def load(direction: str) -> list[dict]:
        if direction not in cache:
            path = _TRAJ_DIR / f"{direction}.json"
            if not path.exists():
                raise FileNotFoundError(f"No trajectory file: {path}")
            cache[direction] = json.loads(path.read_text())["frames"]
        return cache[direction]

    def approach(target: dict):
        if args.approach_duration <= 0:
            robot.send_action(target)
            return
        current_raw = robot.bus.sync_read("Present_Position")
        current = {f"{k}.pos": v for k, v in current_raw.items()}
        steps = max(1, int(args.approach_duration * 50))
        dt = args.approach_duration / steps
        for i in range(1, steps + 1):
            robot.send_action(_lerp(current, target, i / steps))
            time.sleep(dt)

    def replay(direction: str):
        frames = load(direction)
        approach({k: v for k, v in frames[0].items() if k != "t"})
        t_start = time.perf_counter()
        for frame in frames:
            wait = frame["t"] - (time.perf_counter() - t_start)
            if wait > 0:
                time.sleep(wait)
            robot.send_action({k: v for k, v in frame.items() if k != "t"})

    print("READY", flush=True)

    for line in sys.stdin:
        direction = line.strip()
        if not direction or direction == "quit":
            break
        try:
            replay(direction)
            print("DONE", flush=True)
        except Exception as e:
            print(f"ERROR {e}", flush=True)

    robot.disconnect()


if __name__ == "__main__":
    main()
