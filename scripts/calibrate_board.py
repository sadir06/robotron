"""
Board Calibration Script for SO-101.

Run this at the hackathon to map each board square to arm joint angles.
Uses the leader arm (teleoperation) to record positions.

Usage:
  python scripts/calibrate_board.py

Process:
  1. Use the leader arm to move the follower to each position
  2. Press Enter to record that position
  3. Saves calibration.json with all positions
"""
import os
import sys
import json
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OUTPUT_PATH = Path("robot/calibration.json")

POSITIONS_TO_CALIBRATE = [
    ("home", "Move arm to HOME/rest position"),
    ("piece_tray.hover", "Move arm ABOVE the piece tray"),
    ("piece_tray.grab", "Move arm DOWN to grab a piece from tray"),
    ("board.0,0", "Move arm to board TOP-LEFT square"),
    ("board.0,1", "Move arm to board TOP-CENTER square"),
    ("board.0,2", "Move arm to board TOP-RIGHT square"),
    ("board.1,0", "Move arm to board MIDDLE-LEFT square"),
    ("board.1,1", "Move arm to board CENTER square"),
    ("board.1,2", "Move arm to board MIDDLE-RIGHT square"),
    ("board.2,0", "Move arm to board BOTTOM-LEFT square"),
    ("board.2,1", "Move arm to board BOTTOM-CENTER square"),
    ("board.2,2", "Move arm to board BOTTOM-RIGHT square"),
]


def calibrate_manual():
    """Manual calibration — record joint angles by typing them in.
    Use this if you don't have the leader arm connected."""
    
    print("\n" + "=" * 50)
    print("  🔧 NemesisTTT Board Calibration (Manual)")
    print("=" * 50)
    print("\nFor each position, enter 6 joint angles separated by commas.")
    print("Example: 0.0, -1.0, 1.0, 0.0, 0.0, 0.5\n")
    
    calibration = {"board": {}}
    
    for key, instruction in POSITIONS_TO_CALIBRATE:
        print(f"\n📍 {instruction}")
        values = input(f"   Joint angles for '{key}': ").strip()
        
        if not values:
            print("   ⏭️  Skipped (using placeholder)")
            angles = [0.0, 0.0, 0.0, 0.0, 0.0, 0.5]
        else:
            angles = [float(v.strip()) for v in values.split(",")]
        
        # Handle nested keys like "board.0,0" and "piece_tray.hover"
        if "." in key:
            parts = key.split(".", 1)
            parent = parts[0]
            child = parts[1]
            
            if parent == "board":
                if parent not in calibration:
                    calibration[parent] = {}
                if child not in calibration[parent]:
                    calibration[parent][child] = {}
                # For board positions, record both hover (z+5cm) and place
                calibration[parent][child] = {
                    "hover": [angles[0], angles[1], angles[2] + 0.3, angles[3], angles[4], angles[5]],
                    "place": angles,
                }
            elif parent == "piece_tray":
                if parent not in calibration:
                    calibration[parent] = {}
                calibration[parent][child] = angles
        else:
            calibration[key] = angles
    
    # Add gripper values
    calibration["gripper_open"] = [1.0]
    calibration["gripper_closed"] = [0.0]
    
    # Save
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(calibration, indent=2))
    print(f"\n✅ Calibration saved to {OUTPUT_PATH}")
    print(json.dumps(calibration, indent=2))


def calibrate_with_leader():
    """Calibration using leader-follower teleoperation.
    Reads joint angles from the follower arm's current position."""
    
    print("\n" + "=" * 50)
    print("  🔧 NemesisTTT Board Calibration (Leader Arm)")
    print("=" * 50)
    
    try:
        from lerobot.robots.so101_follower import SO101Follower, SO101FollowerConfig
    except ImportError:
        print("❌ LeRobot not installed. Use manual calibration instead.")
        print("   Running: calibrate_manual()")
        calibrate_manual()
        return
    
    port = os.getenv("ROBOT_PORT", "/dev/ttyUSB0")
    robot_id = os.getenv("ROBOT_ID", "ttt_arm")
    
    config = SO101FollowerConfig(port=port, id=robot_id)
    robot = SO101Follower(config)
    robot.connect()
    
    print(f"\n🤖 Connected to SO-101 on {port}")
    print("Use the leader arm to move the follower to each position.")
    print("Press Enter to record the current position.\n")
    
    calibration = {"board": {}}
    
    for key, instruction in POSITIONS_TO_CALIBRATE:
        print(f"\n📍 {instruction}")
        input("   Press Enter when arm is in position...")
        
        # Read current joint angles
        obs = robot.get_observation()
        angles = obs["observation.state"].tolist()
        print(f"   Recorded: {[round(a, 3) for a in angles]}")
        
        if "." in key:
            parts = key.split(".", 1)
            parent, child = parts[0], parts[1]
            
            if parent == "board":
                if parent not in calibration:
                    calibration[parent] = {}
                calibration[parent][child] = {
                    "hover": [angles[0], angles[1], angles[2] + 0.3, angles[3], angles[4], angles[5]],
                    "place": angles,
                }
            elif parent == "piece_tray":
                if parent not in calibration:
                    calibration[parent] = {}
                calibration[parent][child] = angles
        else:
            calibration[key] = angles
    
    calibration["gripper_open"] = [1.0]
    calibration["gripper_closed"] = [0.0]
    
    robot.disconnect()
    
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(calibration, indent=2))
    print(f"\n✅ Calibration saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    print("Choose calibration method:")
    print("  1. Manual (type joint angles)")
    print("  2. Leader arm (teleoperation)")
    
    choice = input("\nChoice (1/2): ").strip()
    if choice == "2":
        calibrate_with_leader()
    else:
        calibrate_manual()
