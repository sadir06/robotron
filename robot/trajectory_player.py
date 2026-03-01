"""
Spawns robot_worker.py under lerobot's Python 3.10 as a subprocess.

This lets the main server (Python 3.13) control the robot without importing
torch/lerobot directly, avoiding the DLL version mismatch on Windows.
"""
import subprocess
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
_WORKER = Path(__file__).resolve().parent / "robot_worker.py"

# Find lerobot's Python executable
_LEROBOT_PYTHON = (
    _root / "lerobot" / ".venv" / "Scripts" / "python.exe"  # Windows
    if (_root / "lerobot" / ".venv" / "Scripts" / "python.exe").exists()
    else _root / "lerobot" / ".venv" / "bin" / "python"      # Linux
)


class TrajectoryPlayer:
    def __init__(self, port: str, robot_id: str = "my_follower", approach_duration: float = 2.0):
        self.port = port
        self.robot_id = robot_id
        self.approach_duration = approach_duration
        self._process: subprocess.Popen | None = None

    def _ensure_process(self):
        if self._process is not None and self._process.poll() is None:
            return  # already running

        self._process = subprocess.Popen(
            [
                str(_LEROBOT_PYTHON),
                str(_WORKER),
                "--port", self.port,
                "--robot-id", self.robot_id,
                "--approach-duration", str(self.approach_duration),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=sys.stderr,  # robot logs flow through to the main terminal
            text=True,
            bufsize=1,
        )

        line = self._process.stdout.readline().strip()
        if line != "READY":
            self._process.kill()
            raise RuntimeError(f"Robot worker failed to start. Got: {line!r}")

        print(f"[robot] Worker ready (pid={self._process.pid})", flush=True)

    def replay(self, direction: str):
        self._ensure_process()

        self._process.stdin.write(direction + "\n")
        self._process.stdin.flush()

        while True:
            line = self._process.stdout.readline()
            if not line:
                # EOF — worker process died
                code = self._process.poll()
                self._process = None
                raise RuntimeError(f"Robot worker died during replay (exit code {code})")
            line = line.strip()
            if line == "DONE":
                break
            if line.startswith("ERROR"):
                raise RuntimeError(f"Worker: {line}")
            if line:
                print(f"[robot] {line}", flush=True)

    def close(self):
        if self._process and self._process.poll() is None:
            try:
                self._process.stdin.write("quit\n")
                self._process.stdin.flush()
                self._process.wait(timeout=5)
            except Exception:
                self._process.kill()
        self._process = None
