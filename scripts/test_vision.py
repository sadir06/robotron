"""
Test the Nemotron VLM board reading.

Usage:
  python scripts/test_vision.py --image path/to/board_photo.jpg
  python scripts/test_vision.py --interactive  # drag & drop images
"""
import os
import sys
import argparse
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


def test_with_image(image_path: str):
    """Test VLM on a single image."""
    from game.vision import read_board
    
    print(f"\n{'='*50}")
    print(f"Testing VLM on: {image_path}")
    print(f"{'='*50}\n")
    
    image_bytes = Path(image_path).read_bytes()
    
    try:
        result = read_board(image_bytes)
        
        print("\n✅ Board state detected:")
        grid = result["grid"]
        for r in range(3):
            cells = []
            for c in range(3):
                val = grid[r][c]
                cells.append(val if val else "·")
            print(f"  {' │ '.join(cells)}")
            if r < 2:
                print(f"  ──┼───┼──")
        
        x_count = sum(row.count("X") for row in grid)
        o_count = sum(row.count("O") for row in grid)
        empty = sum(row.count("") for row in grid)
        print(f"\n  X: {x_count} | O: {o_count} | Empty: {empty}")
        
        return result
    except Exception as e:
        print(f"\n❌ Vision failed: {e}")
        return None


def test_interactive():
    """Interactive mode — keep testing images."""
    print("\n🔬 NemesisTTT Vision Tester")
    print("Enter image paths to test. Type 'quit' to exit.\n")
    
    while True:
        path = input("📁 Image path: ").strip().strip("'\"")
        if path.lower() in ("quit", "q", "exit"):
            break
        if not Path(path).exists():
            print(f"  ❌ File not found: {path}")
            continue
        test_with_image(path)
        print()


def test_without_vlm():
    """Test the board state logic without calling the VLM."""
    from game.state import GameState
    
    print("\n🧪 Testing game state logic (no VLM needed):\n")
    
    game = GameState()
    
    # Simulate a game
    moves = [
        (1, 1, "X"),  # X takes center
        (0, 0, "O"),  # O takes corner
        (0, 2, "X"),  # X takes corner
        (2, 0, "O"),  # O takes corner
        (1, 0, "X"),  # X takes edge
    ]
    
    for row, col, player in moves:
        game.apply_move(row, col, player)
        print(f"  {player} plays [{row},{col}]")
        print(f"  {game.to_display()}\n")
    
    print(f"  Winner: {game.winner}")
    print(f"  Game over: {game.game_over}")
    print("  ✅ State logic works!")


def main():
    parser = argparse.ArgumentParser(description="Test NemesisTTT Vision")
    parser.add_argument("--image", type=str, help="Path to board image")
    parser.add_argument("--interactive", action="store_true", help="Interactive testing mode")
    parser.add_argument("--no-vlm", action="store_true", help="Test state logic only (no API needed)")
    
    args = parser.parse_args()
    
    if args.no_vlm:
        test_without_vlm()
    elif args.image:
        test_with_image(args.image)
    elif args.interactive:
        test_interactive()
    else:
        # Default: test state logic then try interactive
        test_without_vlm()
        print("\n" + "─" * 50)
        print("To test VLM, run with --image or --interactive")
        print("Example: python scripts/test_vision.py --image photo.jpg")


if __name__ == "__main__":
    main()
