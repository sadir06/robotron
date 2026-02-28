"""
Generate test board images from test_strategy scenarios.

Creates visual tic-tac-toe boards for testing the vision→strategy pipeline.

Usage:
  python scripts/generate_test_images.py
  python scripts/generate_test_images.py --output ./test_boards
"""
import os
import sys
import argparse
from pathlib import Path

# Try to use PIL (preferred), fall back to cv2
try:
    from PIL import Image, ImageDraw, ImageFont
    USE_PIL = True
except ImportError:
    import cv2
    import numpy as np
    USE_PIL = False

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test scenarios from test_strategy.py
SCENARIOS = [
    {
        "name": "empty_board_center",
        "filename": "01_empty_board_center.jpg",
        "description": "Empty board with X in center",
        "grid": [
            ["", "", ""],
            ["", "X", ""],
            ["", "", ""],
        ],
    },
    {
        "name": "ai_should_win",
        "filename": "02_ai_should_win.jpg",
        "description": "AI should WIN (complete top row)",
        "grid": [
            ["O", "O", ""],
            ["X", "X", ""],
            ["", "", ""],
        ],
    },
    {
        "name": "ai_should_block",
        "filename": "03_ai_should_block.jpg",
        "description": "AI should BLOCK X from winning",
        "grid": [
            ["X", "X", ""],
            ["O", "", ""],
            ["", "", ""],
        ],
    },
    {
        "name": "fork_setup",
        "filename": "04_fork_setup.jpg",
        "description": "Fork setup — create two winning paths",
        "grid": [
            ["O", "", "X"],
            ["", "X", ""],
            ["", "", "O"],
        ],
    },
    {
        "name": "late_game_one_move",
        "filename": "05_late_game_one_move.jpg",
        "description": "Late game — only one move left",
        "grid": [
            ["X", "O", "X"],
            ["X", "O", "O"],
            ["O", "X", ""],
        ],
    },
    {
        "name": "opening_corner",
        "filename": "06_opening_corner.jpg",
        "description": "Opening — X took corner",
        "grid": [
            ["X", "", ""],
            ["", "", ""],
            ["", "", ""],
        ],
    },
]


def create_board_image_pil(grid, output_path: str):
    """Create a board image using PIL."""
    # Image settings
    cell_size = 150
    border = 20
    img_size = cell_size * 3 + border * 2

    # Colors
    bg_color = (240, 240, 240)
    line_color = (0, 0, 0)
    x_color = (200, 50, 50)  # Red
    o_color = (50, 100, 200)  # Blue

    # Create image
    img = Image.new('RGB', (img_size, img_size), bg_color)
    draw = ImageDraw.Draw(img)

    # Try to use a nice font, fall back to default
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 100)
        small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
    except:
        font = ImageFont.load_default()
        small_font = font

    # Draw grid lines
    for i in range(1, 3):
        x = border + i * cell_size
        draw.line([(x, border), (x, img_size - border)], fill=line_color, width=3)
        draw.line([(border, x), (img_size - border, x)], fill=line_color, width=3)

    # Draw border
    draw.rectangle(
        [(border, border), (img_size - border, img_size - border)],
        outline=line_color,
        width=3
    )

    # Draw X's and O's
    for r in range(3):
        for c in range(3):
            cell = grid[r][c]
            x = border + c * cell_size + cell_size // 2
            y = border + r * cell_size + cell_size // 2

            if cell == "X":
                # Draw X
                offset = 40
                draw.line(
                    [(x - offset, y - offset), (x + offset, y + offset)],
                    fill=x_color,
                    width=8
                )
                draw.line(
                    [(x + offset, y - offset), (x - offset, y + offset)],
                    fill=x_color,
                    width=8
                )
            elif cell == "O":
                # Draw O
                radius = 50
                draw.ellipse(
                    [(x - radius, y - radius), (x + radius, y + radius)],
                    outline=o_color,
                    width=8
                )

    # Save
    img.save(output_path, 'JPEG', quality=95)
    print(f"  ✅ Created: {output_path}")


def create_board_image_cv2(grid, output_path: str):
    """Create a board image using OpenCV."""
    # Image settings
    cell_size = 150
    border = 20
    img_size = cell_size * 3 + border * 2

    # Colors (BGR)
    bg_color = (240, 240, 240)
    line_color = (0, 0, 0)
    x_color = (50, 50, 200)  # Red in BGR
    o_color = (200, 100, 50)  # Blue in BGR

    # Create blank image
    img = np.full((img_size, img_size, 3), bg_color, dtype=np.uint8)

    # Draw grid lines
    for i in range(1, 3):
        x = border + i * cell_size
        cv2.line(img, (x, border), (x, img_size - border), line_color, 3)
        cv2.line(img, (border, x), (img_size - border, x), line_color, 3)

    # Draw border
    cv2.rectangle(img, (border, border), (img_size - border, img_size - border), line_color, 3)

    # Draw X's and O's
    for r in range(3):
        for c in range(3):
            cell = grid[r][c]
            x = border + c * cell_size + cell_size // 2
            y = border + r * cell_size + cell_size // 2

            if cell == "X":
                # Draw X
                offset = 40
                cv2.line(img, (x - offset, y - offset), (x + offset, y + offset), x_color, 8)
                cv2.line(img, (x + offset, y - offset), (x - offset, y + offset), x_color, 8)
            elif cell == "O":
                # Draw O
                radius = 50
                cv2.circle(img, (x, y), radius, o_color, 8)

    # Save
    cv2.imwrite(output_path, img)
    print(f"  ✅ Created: {output_path}")


def generate_test_images(output_dir: str):
    """Generate all test board images."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 60)
    print("  🎨 Generating Test Board Images")
    print("=" * 60)

    for scenario in SCENARIOS:
        print(f"\n📋 {scenario['name']}")
        print(f"   Description: {scenario['description']}")

        file_path = output_path / scenario['filename']

        try:
            if USE_PIL:
                create_board_image_pil(scenario['grid'], str(file_path))
            else:
                create_board_image_cv2(scenario['grid'], str(file_path))
        except Exception as e:
            print(f"  ❌ Error creating image: {e}")

    print("\n" + "=" * 60)
    print(f"  ✅ All images saved to: {output_dir}")
    print("=" * 60)

    print(f"\nYou can now test with:")
    print(f"  python game/process_image.py {output_dir}/01_empty_board_center.jpg")


def main():
    parser = argparse.ArgumentParser(
        description="Generate test board images for vision→strategy testing"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="test_images",
        help="Output directory for generated images (default: test_images)",
    )

    args = parser.parse_args()

    try:
        generate_test_images(args.output)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
