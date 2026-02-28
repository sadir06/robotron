"""
NemesisTTT — Main Game Loop

Modes:
  keyboard  — Type moves manually, no camera needed (for testing AI)
  camera    — Use camera + VLM to read board (no robot)
  full      — Camera + VLM + Robot (hackathon demo mode)

Usage:
  python game/main.py --mode keyboard
  python game/main.py --mode camera
  python game/main.py --mode full
  python game/main.py --mode keyboard --image tests/sample_board.jpg
"""
import os
import sys
import json
import argparse
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.state import GameState
from game.strategy import decide_move

# Optional imports based on mode
try:
    from game.vision import read_board
except ImportError:
    read_board = None

try:
    from game.camera import capture_board
except ImportError:
    capture_board = None


def get_robot(mode: str):
    """Get the appropriate robot (real or mock)."""
    if mode == "full" and os.getenv("ROBOT_ENABLED", "false").lower() == "true":
        from robot.primitives import SO101Robot
        robot = SO101Robot()
        robot.connect()
        return robot
    else:
        from robot.mock_robot import MockRobot
        robot = MockRobot()
        robot.connect()
        return robot


def get_human_move_keyboard(game: GameState) -> tuple[int, int]:
    """Get human move via keyboard input."""
    while True:
        print("\nBoard positions:")
        print("  0,0 │ 0,1 │ 0,2")
        print("  ────┼─────┼────")
        print("  1,0 │ 1,1 │ 1,2")
        print("  ────┼─────┼────")
        print("  2,0 │ 2,1 │ 2,2")
        
        move_str = input("\n🎮 Your move (row,col): ").strip()
        
        try:
            parts = move_str.replace(" ", "").split(",")
            row, col = int(parts[0]), int(parts[1])
            
            if not (0 <= row <= 2 and 0 <= col <= 2):
                print("❌ Position must be 0-2 for both row and col")
                continue
            
            if game.grid[row][col] != "":
                print(f"❌ Position [{row},{col}] is already taken by {game.grid[row][col]}")
                continue
            
            return row, col
        except (ValueError, IndexError):
            print("❌ Invalid format. Use: row,col (e.g., 1,1 for center)")


def get_human_move_camera(game: GameState) -> tuple[int, int]:
    """Get human move by taking a photo and comparing to previous state."""
    input("\n🎮 Place your X piece and press Enter...")
    
    image = capture_board()
    new_board = read_board(image)
    new_grid = new_board["grid"]
    
    # Find what changed
    for r in range(3):
        for c in range(3):
            if game.grid[r][c] == "" and new_grid[r][c] == "X":
                return r, c
    
    # If no change detected, ask again
    print("⚠️  Couldn't detect your move. Let me look again...")
    return get_human_move_camera(game)


def display_board(game: GameState):
    """Display the current board."""
    print(f"\n{'─'*20}")
    print(game.to_display())
    print(f"{'─'*20}")


def run_game(mode: str = "keyboard", image_path: str = None):
    """Main game loop."""
    print("\n" + "=" * 50)
    print("  🎮 NemesisTTT — You vs Nemotron")
    print("  You are X. AI is O. You go first.")
    print("=" * 50)
    
    game = GameState()
    robot = get_robot(mode)
    move_count = 0
    
    # WebSocket broadcast (if server is running)
    try:
        from api.server import broadcast_sync
        broadcast = broadcast_sync
    except ImportError:
        broadcast = lambda data: None
    
    while not game.game_over:
        display_board(game)
        
        # === HUMAN TURN (X) ===
        if game.current_player == "X":
            if mode == "keyboard":
                row, col = get_human_move_keyboard(game)
            elif mode in ("camera", "full"):
                row, col = get_human_move_camera(game)
            else:
                row, col = get_human_move_keyboard(game)
            
            game.apply_move(row, col, "X")
            move_count += 1
            
            broadcast({"event": "human_move", "move": [row, col], **game.to_dict()})
            
            if game.game_over:
                break
        
        # === AI TURN (O) ===
        if game.current_player == "O" and not game.game_over:
            print("\n🧠 AI is thinking...\n")
            
            # Get AI move from Nemotron
            start = time.time()
            ai_response = decide_move(game.grid, move_count)
            elapsed = time.time() - start
            
            if ai_response["move"] is None:
                break
            
            row, col = ai_response["move"]
            
            # Apply move
            game.apply_move(
                row, col, "O",
                reasoning=ai_response.get("reasoning", ""),
                trash_talk=ai_response.get("trash_talk", ""),
                confidence=ai_response.get("confidence", 0.0),
            )
            move_count += 1
            
            # Physical move
            robot.execute_move(row, col, "O")
            
            # Show AI's personality
            if ai_response.get("trash_talk"):
                print(f"\n💬 AI says: \"{ai_response['trash_talk']}\"")
            
            print(f"⏱️  AI thought for {elapsed:.1f}s")
            
            broadcast({
                "event": "ai_move",
                "move": [row, col],
                "reasoning": ai_response.get("reasoning", ""),
                "trash_talk": ai_response.get("trash_talk", ""),
                "confidence": ai_response.get("confidence", 0),
                **game.to_dict(),
            })
    
    # === GAME OVER ===
    display_board(game)
    print("\n" + "=" * 50)
    
    if game.winner == "X":
        print("  🏆 YOU WIN! (wait... that shouldn't happen)")
        robot.sulk()
        broadcast({"event": "game_over", "winner": "human", **game.to_dict()})
    elif game.winner == "O":
        print("  🤖 AI WINS! Better luck next time, human.")
        robot.celebrate()
        broadcast({"event": "game_over", "winner": "ai", **game.to_dict()})
    else:
        print("  🤝 IT'S A DRAW! You're not bad... for a human.")
        broadcast({"event": "game_over", "winner": "draw", **game.to_dict()})
    
    print("=" * 50)
    
    # Play again?
    again = input("\n🔄 Play again? (y/n): ").strip().lower()
    if again == "y":
        game.reset()
        run_game(mode, image_path)
    else:
        robot.disconnect()
        print("👋 Thanks for playing NemesisTTT!")


def main():
    parser = argparse.ArgumentParser(description="NemesisTTT — AI Tic-Tac-Toe")
    parser.add_argument(
        "--mode",
        choices=["keyboard", "camera", "full"],
        default="keyboard",
        help="keyboard=manual input, camera=VLM reads board, full=camera+robot",
    )
    parser.add_argument(
        "--image",
        type=str,
        default=None,
        help="Path to board image (for testing vision without camera)",
    )
    
    args = parser.parse_args()
    
    from dotenv import load_dotenv
    load_dotenv()
    
    run_game(args.mode, args.image)


if __name__ == "__main__":
    main()
