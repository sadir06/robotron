# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Structure

This is a monorepo in early development with two components:

- **`lerobot/`** — The LeRobot robotics library (separate git repository). All robot training, evaluation, data collection, and policy logic lives here. This directory has its own `CLAUDE.md` with full development instructions.
- **`frontend/`** — Frontend application (currently empty, not yet developed).

## Working with LeRobot

For all work within `lerobot/`, refer to `lerobot/CLAUDE.md` for:
- Environment setup (conda + pip)
- Testing with pytest
- Linting with ruff and mypy
- CLI entry points (`lerobot-train`, `lerobot-eval`, `lerobot-record`, etc.)
- Architecture details (policy system, dataset format, robot interface, processor pipeline)

Note: `lerobot/` has its own `.git` directory and is tracked independently.

## Trajectory Recording & Replay

`scripts/record_traj.py` and `scripts/replay_traj.py` implement kinesthetic teaching — record by hand-guiding the arm, replay the exact motion.

Both scripts auto-discover the lerobot venv — no activation needed. Run with any Python 3.10+:

**Teleop-record** — control leader arm by hand, follower mirrors it, trajectory saved by direction:
```bash
python scripts/record_teleop.py --left  --leader-port COM3 --follower-port COM4
python scripts/record_teleop.py --up    --leader-port COM3 --follower-port COM4
python scripts/record_teleop.py --right --leader-port COM3 --follower-port COM4
# outputs: trajectories/left.json, trajectories/up.json, trajectories/right.json
```

**Hand-guide record** — torque disabled, move follower arm directly by hand:
```bash
python scripts/record_traj.py --port COM3 --output trajectories/demo.json
```

**Replay** — smoothly approaches start position, then replays at original speed:
```bash
python scripts/replay_traj.py --port COM3 --input trajectories/left.json
python scripts/replay_traj.py --port COM3 --input trajectories/left.json --speed 0.5 --loop
```

Trajectory files are JSON: `{direction, hz, motors, frames: [{t, <motor>.pos, ...}]}`.
