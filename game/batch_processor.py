"""
Batch processor — processes board images from a folder sequentially.
Useful for processing pre-recorded game sessions or streaming image sequences.

Usage:
  python game/batch_processor.py --folder /path/to/images --robot mock
  python game/batch_processor.py --folder /path/to/images --robot real
"""
import os
import json
import time
import argparse
from pathlib import Path
from typing import List, Tuple

from game.state import GameState
from game.vision import read_board
from game.strategy import decide_move


def get_image_files(folder_path: str) -> List[Path]:
    """Get all image files from a folder, sorted by name."""
    folder = Path(folder_path)
    if not folder.exists():
        raise ValueError(f"Folder does not exist: {folder_path}")

    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}
    images = sorted([
        f for f in folder.iterdir()
        if f.suffix.lower() in image_extensions
    ])

    if not images:
        raise ValueError(f"No image files found in {folder_path}")

    return images


def process_batch(
    folder_path: str,
    robot_type: str = "mock",
    skip_frames: int = 0,
    pause_between: float = 0.5
):
    """
    Process a batch of board images from a folder.

    Args:
        folder_path: Path to folder containing board images
        robot_type: "mock" or "real" (for production robot)
        skip_frames: Skip first N images (useful for warmup)
        pause_between: Seconds to pause between processing images
    """
    # Initialize
    game = GameState()
    robot = _get_robot(robot_type)
    robot.connect()

    images = get_image_files(folder_path)
    total_images = len(images)

    print("\n" + "=" * 60)
    print(f"🎮 NemesisTTT Batch Processor")
    print(f"📁 Folder: {folder_path}")
    print(f"🖼️  Total images: {total_images}")
    print(f"🤖 Robot: {robot_type}")
    print("=" * 60)

    if skip_frames > 0:
        print(f"\n⏭️  Skipping first {skip_frames} images (warmup)...")
        images = images[skip_frames:]

    move_count = 0
    last_board_state = None

    # Process each image
    for idx, image_path in enumerate(images, start=skip_frames + 1):
        print(f"\n{'─'*60}")
        print(f"📸 Image {idx}/{total_images}: {image_path.name}")
        print(f"{'─'*60}")

        try:
            # Read board from image
            with open(image_path, 'rb') as f:
                image_bytes = f.read()

            board_state = read_board(image_bytes)
            current_grid = board_state["grid"]

            # Detect what changed if we have a previous state
            if last_board_state:
                human_move = _detect_human_move(last_board_state, current_grid)
                if human_move:
                    row, col = human_move
                    print(f"🎯 Human placed X at [{row},{col}]")
                    game.apply_move(row, col, "X")
                    move_count += 1
                else:
                    print("ℹ️  No new X piece detected (same board state)")
            else:
                print("ℹ️  First image - initializing game state")
                # Sync game state to what we see
                for r in range(3):
                    for c in range(3):
                        if current_grid[r][c] == "X":
                            game.grid[r][c] = "X"
                        elif current_grid[r][c] == "O":
                            game.grid[r][c] = "O"

            # Check if it's AI's turn
            if game.current_player == "O" and not game.game_over:
                print("\n🧠 AI is thinking...")

                # Get AI move
                ai_response = decide_move(game.grid, move_count)

                if ai_response["move"] is None:
                    print("✅ Game is over (no valid moves)")
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

                # Execute move with robot
                print(f"\n🤖 Executing move: O at [{row},{col}]")
                robot.execute_move(row, col, "O")

                # Show AI's personality
                if ai_response.get("trash_talk"):
                    print(f"💬 AI says: \"{ai_response['trash_talk']}\"")

            # Display current board
            print(f"\n{'─'*20}")
            print(game.to_display())
            print(f"{'─'*20}")

            # Save state for next iteration
            last_board_state = [row[:] for row in current_grid]

            # Pause before next image
            if idx < total_images:
                print(f"⏸️  Waiting {pause_between}s before next image...")
                time.sleep(pause_between)

        except Exception as e:
            print(f"❌ Error processing {image_path.name}: {e}")
            import traceback
            traceback.print_exc()
            continue

    # Game over
    print("\n" + "=" * 60)
    if game.game_over:
        if game.winner == "X":
            print("🏆 HUMAN WINS!")
            robot.sulk()
        elif game.winner == "O":
            print("🤖 AI WINS!")
            robot.celebrate()
        else:
            print("🤝 IT'S A DRAW!")
    else:
        print("✅ Batch processing complete")
    print("=" * 60)

    robot.disconnect()


def _detect_human_move(
    previous_grid: List[List[str]],
    current_grid: List[List[str]]
) -> Tuple[int, int] | None:
    """
    Compare two board states to find where human placed their X piece.
    Returns (row, col) or None if no new X piece detected.
    """
    for r in range(3):
        for c in range(3):
            if previous_grid[r][c] == "" and current_grid[r][c] == "X":
                return (r, c)
    return None


def _get_robot(robot_type: str):
    """Get the appropriate robot (real or mock)."""
    if robot_type == "real":
        from robot.primitives import SO101Robot
        return SO101Robot()
    else:
        from robot.mock_robot import MockRobot
        return MockRobot()


def main():
    parser = argparse.ArgumentParser(
        description="Batch process tic-tac-toe board images"
    )
    parser.add_argument(
        "--folder",
        type=str,
        required=True,
        help="Path to folder containing board images",
    )
    parser.add_argument(
        "--robot",
        choices=["mock", "real"],
        default="mock",
        help="Use mock robot (simulation) or real SO-101 arm",
    )
    parser.add_argument(
        "--skip",
        type=int,
        default=0,
        help="Skip first N images for warmup",
    )
    parser.add_argument(
        "--pause",
        type=float,
        default=0.5,
        help="Seconds to pause between processing images",
    )

    args = parser.parse_args()

    from dotenv import load_dotenv
    load_dotenv()

    try:
        process_batch(
            folder_path=args.folder,
            robot_type=args.robot,
            skip_frames=args.skip,
            pause_between=args.pause,
        )
    except Exception as e:
        print(f"❌ Batch processing failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
