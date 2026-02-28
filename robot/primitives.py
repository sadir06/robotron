"""
SO-101 arm control primitives via LeRobot.
Only used when ROBOT_ENABLED=true in .env

For hackathon: we use pre-calibrated positions rather than inverse kinematics.
Each board square maps to a known set of joint angles recorded during calibration.
"""
import os
import json
import time
from pathlib import Path


class SO101Robot:
    """Real SO-101 arm controller via LeRobot."""
    
    def __init__(self, calibration_path: str = "robot/calibration.json"):
        self.calibration = self._load_calibration(calibration_path)
        self.robot = None
        self.connected = False
    
    def connect(self):
        """Connect to the physical SO-101 arm."""
        try:
            from lerobot.robots.so101_follower import SO101Follower, SO101FollowerConfig
            
            port = os.getenv("ROBOT_PORT", "/dev/ttyUSB0")
            robot_id = os.getenv("ROBOT_ID", "ttt_arm")
            
            config = SO101FollowerConfig(port=port, id=robot_id)
            self.robot = SO101Follower(config)
            self.robot.connect()
            self.connected = True
            print(f"🤖 SO-101 connected on {port}")
        except ImportError:
            raise RuntimeError(
                "LeRobot not installed. Install with: pip install lerobot\n"
                "Or set ROBOT_ENABLED=false to use mock robot."
            )
        except Exception as e:
            raise RuntimeError(f"Failed to connect to SO-101: {e}")
    
    def disconnect(self):
        if self.robot:
            self.robot.disconnect()
            self.connected = False
            print("🤖 SO-101 disconnected")
    
    def pick_piece(self, piece_type: str = "O"):
        """Pick up a piece from the tray."""
        tray_pos = self.calibration["piece_tray"]
        
        self._move_to_position(tray_pos["hover"])
        time.sleep(0.3)
        self._move_to_position(tray_pos["grab"])
        time.sleep(0.2)
        self._gripper_close()
        time.sleep(0.3)
        self._move_to_position(tray_pos["hover"])
        time.sleep(0.2)
    
    def place_piece(self, row: int, col: int):
        """Place a piece on the board."""
        key = f"{row},{col}"
        if key not in self.calibration["board"]:
            raise ValueError(f"No calibration for position [{row},{col}]")
        
        pos = self.calibration["board"][key]
        
        self._move_to_position(pos["hover"])
        time.sleep(0.3)
        self._move_to_position(pos["place"])
        time.sleep(0.2)
        self._gripper_open()
        time.sleep(0.3)
        self._move_to_position(pos["hover"])
        time.sleep(0.2)
    
    def home(self):
        """Return to home position."""
        self._move_to_position(self.calibration["home"])
    
    def celebrate(self):
        """Victory animation."""
        home = self.calibration["home"]
        for _ in range(3):
            self._move_to_position(self.calibration.get("celebrate_up", home))
            time.sleep(0.2)
            self._move_to_position(self.calibration.get("celebrate_down", home))
            time.sleep(0.2)
        self.home()
    
    def sulk(self):
        """Defeat animation."""
        self._move_to_position(self.calibration.get("sulk", self.calibration["home"]))
        time.sleep(1.0)
        self.home()
    
    def execute_move(self, row: int, col: int, piece_type: str = "O"):
        """Full move: pick → place → home."""
        print(f"🤖 Executing: {piece_type} → [{row},{col}]")
        self.pick_piece(piece_type)
        self.place_piece(row, col)
        self.home()
        print(f"🤖 Move complete ✓")
    
    def _move_to_position(self, joint_angles: list[float]):
        """Send joint angle command to robot."""
        if self.robot:
            # LeRobot send_action expects a dict or tensor of joint positions
            import torch
            action = torch.tensor(joint_angles, dtype=torch.float32)
            self.robot.send_action(action)
    
    def _gripper_close(self):
        """Close the gripper."""
        if self.robot:
            import torch
            # Last joint is typically the gripper
            current = self.calibration.get("gripper_closed", [0.0])
            self.robot.send_action(torch.tensor(current, dtype=torch.float32))
    
    def _gripper_open(self):
        """Open the gripper."""
        if self.robot:
            import torch
            current = self.calibration.get("gripper_open", [1.0])
            self.robot.send_action(torch.tensor(current, dtype=torch.float32))
    
    def _load_calibration(self, path: str) -> dict:
        """Load calibration file."""
        cal_path = Path(path)
        if not cal_path.exists():
            print(f"⚠️  No calibration file at {path}. Run scripts/calibrate_board.py first.")
            return self._default_calibration()
        return json.loads(cal_path.read_text())
    
    def _default_calibration(self) -> dict:
        """Placeholder calibration — must be replaced with real values."""
        return {
            "home": [0.0, -1.0, 1.0, 0.0, 0.0, 0.5],
            "piece_tray": {
                "hover": [0.3, -0.5, 0.8, 0.0, 0.0, 0.5],
                "grab": [0.3, -0.5, 0.5, 0.0, 0.0, 0.5],
            },
            "board": {
                "0,0": {"hover": [-0.3, -0.5, 0.8, 0.0, 0.0, 0.5], "place": [-0.3, -0.5, 0.5, 0.0, 0.0, 0.5]},
                "0,1": {"hover": [0.0, -0.5, 0.8, 0.0, 0.0, 0.5], "place": [0.0, -0.5, 0.5, 0.0, 0.0, 0.5]},
                "0,2": {"hover": [0.3, -0.5, 0.8, 0.0, 0.0, 0.5], "place": [0.3, -0.5, 0.5, 0.0, 0.0, 0.5]},
                "1,0": {"hover": [-0.3, -0.8, 0.8, 0.0, 0.0, 0.5], "place": [-0.3, -0.8, 0.5, 0.0, 0.0, 0.5]},
                "1,1": {"hover": [0.0, -0.8, 0.8, 0.0, 0.0, 0.5], "place": [0.0, -0.8, 0.5, 0.0, 0.0, 0.5]},
                "1,2": {"hover": [0.3, -0.8, 0.8, 0.0, 0.0, 0.5], "place": [0.3, -0.8, 0.5, 0.0, 0.0, 0.5]},
                "2,0": {"hover": [-0.3, -1.1, 0.8, 0.0, 0.0, 0.5], "place": [-0.3, -1.1, 0.5, 0.0, 0.0, 0.5]},
                "2,1": {"hover": [0.0, -1.1, 0.8, 0.0, 0.0, 0.5], "place": [0.0, -1.1, 0.5, 0.0, 0.0, 0.5]},
                "2,2": {"hover": [0.3, -1.1, 0.8, 0.0, 0.0, 0.5], "place": [0.3, -1.1, 0.5, 0.0, 0.0, 0.5]},
            },
            "gripper_closed": [0.0],
            "gripper_open": [1.0],
        }
