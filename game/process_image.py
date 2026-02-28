"""
Single image processor — reads one board image and returns the next AI move.

Usage:
  python game/process_image.py /path/to/board.jpg
  python game/process_image.py --image /path/to/board.jpg
"""
import argparse
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.vision import read_board
from game.strategy import decide_move


def process_single_image(image_path: str) -> dict:
    """
    Process a single board image and return the AI's next move.

    Args:
        image_path: Path to board image file

    Returns:
        {
            "board_state": [["X", "O", ""], ...],
            "move": [row, col],
            "reasoning": "why this move",
            "trash_talk": "witty comment",
            "confidence": 0.95,
        }
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    print(f"\n📸 Processing: {image_path}")
    print(f"{'─'*50}")

    # Read the board from image using VLM
    with open(image_path, 'rb') as f:
        image_bytes = f.read()

    board_state = read_board(image_bytes)
    grid = board_state["grid"]

    # Count moves to determine move number
    move_count = sum(1 for r in grid for c in r if c != "")

    print(f"\n🎯 Current board state:")
    _display_board(grid)
    print(f"   Moves so far: {move_count}")

    # Get AI's next move
    print(f"\n🧠 AI is thinking about the next move...")
    ai_response = decide_move(grid, move_count)

    if ai_response["move"] is None:
        print("\n✅ Game is over (no valid moves)")
        return {
            "board_state": grid,
            "move": None,
            "game_over": True,
            "reasoning": "No valid moves available",
        }

    row, col = ai_response["move"]

    print(f"\n{'='*50}")
    print(f"📍 NEXT MOVE: O at [{row},{col}]")
    print(f"{'='*50}")
    print(f"💭 Reasoning: {ai_response.get('reasoning', 'N/A')}")
    print(f"🗣️  Trash talk: {ai_response.get('trash_talk', 'N/A')}")
    print(f"📊 Confidence: {ai_response.get('confidence', 0.0):.2f}")

    return {
        "board_state": grid,
        "move": ai_response["move"],
        "reasoning": ai_response.get("reasoning", ""),
        "trash_talk": ai_response.get("trash_talk", ""),
        "confidence": ai_response.get("confidence", 0.0),
        "game_over": False,
    }


def _display_board(grid):
    """Pretty print the board."""
    for r in range(3):
        cells = [grid[r][c] if grid[r][c] else "·" for c in range(3)]
        print(f"   {' │ '.join(cells)}")
        if r < 2:
            print(f"   ──┼───┼──")


def main():
    parser = argparse.ArgumentParser(
        description="Process a single board image and get the AI's next move",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python game/process_image.py board.jpg
  python game/process_image.py --image /path/to/board.jpg
  python game/process_image.py --image board.jpg --json
        """
    )
    parser.add_argument(
        "image",
        nargs="?",
        default=None,
        help="Path to board image file",
    )
    parser.add_argument(
        "--image",
        dest="image_arg",
        help="Alternative way to specify image path",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON",
    )

    args = parser.parse_args()

    # Get image path from either positional or --image arg
    image_path = args.image or args.image_arg

    if not image_path:
        parser.print_help()
        print("\n❌ Please provide an image path")
        sys.exit(1)

    from dotenv import load_dotenv
    load_dotenv()

    try:
        result = process_single_image(image_path)

        if args.json:
            print(f"\n{json.dumps(result, indent=2)}")

        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
