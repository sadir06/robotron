"""
Mock robot — simulates SO-101 arm for testing without hardware.
Prints what the arm would do instead of actually moving.
"""
import time


class MockRobot:
    """Simulates SO-101 arm movements."""
    
    def __init__(self):
        self.connected = False
        self.position = "home"
        print("🤖 MockRobot initialized (no physical arm)")
    
    def connect(self):
        self.connected = True
        print("🤖 MockRobot connected (simulated)")
    
    def disconnect(self):
        self.connected = False
        print("🤖 MockRobot disconnected")
    
    def pick_piece(self, piece_type: str = "O"):
        """Simulate picking up a piece from the tray."""
        print(f"🤖 ARM: Moving to piece tray...")
        time.sleep(0.3)
        print(f"🤖 ARM: Picking up {piece_type} piece")
        time.sleep(0.2)
        print(f"🤖 ARM: Lifting piece")
        self.position = "holding_piece"
    
    def place_piece(self, row: int, col: int):
        """Simulate placing a piece on the board."""
        square_name = _square_name(row, col)
        print(f"🤖 ARM: Moving to board position [{row},{col}] ({square_name})")
        time.sleep(0.3)
        print(f"🤖 ARM: Lowering piece to board")
        time.sleep(0.2)
        print(f"🤖 ARM: Releasing piece at [{row},{col}]")
        time.sleep(0.1)
        print(f"🤖 ARM: Piece placed! ✓")
        self.position = "above_board"
    
    def home(self):
        """Return to home position."""
        print(f"🤖 ARM: Returning to home position")
        time.sleep(0.2)
        self.position = "home"
    
    def celebrate(self):
        """Victory dance!"""
        print("🤖 ARM: 🎉 Victory dance! (arm waves around)")
        time.sleep(0.5)
    
    def sulk(self):
        """Lost the game..."""
        print("🤖 ARM: 😞 Arm droops dejectedly...")
        time.sleep(0.3)
    
    def execute_move(self, row: int, col: int, piece_type: str = "O"):
        """Full move sequence: pick up piece → place on board → return home."""
        print(f"\n{'='*40}")
        print(f"🤖 EXECUTING MOVE: {piece_type} → [{row},{col}]")
        print(f"{'='*40}")
        self.pick_piece(piece_type)
        self.place_piece(row, col)
        self.home()
        print(f"{'='*40}\n")


def _square_name(row: int, col: int) -> str:
    """Human-readable square name."""
    rows = ["top", "middle", "bottom"]
    cols = ["left", "center", "right"]
    return f"{rows[row]}-{cols[col]}"
