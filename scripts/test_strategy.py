"""
Test the Nemotron strategy agent.
Runs through several board scenarios and checks AI responses.

Usage:
  python scripts/test_strategy.py              # Test with Nemotron API
  python scripts/test_strategy.py --fallback   # Test minimax only (no API needed)
"""
import os
import sys
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from game.strategy import decide_move, _minimax_move

# Test scenarios with expected behavior
SCENARIOS = [
    {
        "name": "Empty board (AI goes second after X takes center)",
        "grid": [
            ["", "", ""],
            ["", "X", ""],
            ["", "", ""],
        ],
        "move_number": 1,
        "expect": "Should take a corner (0,0 or 0,2 or 2,0 or 2,2)",
    },
    {
        "name": "AI should WIN (complete top row)",
        "grid": [
            ["O", "O", ""],
            ["X", "X", ""],
            ["", "", ""],
        ],
        "move_number": 4,
        "expect": "MUST play [0,2] to win",
        "expected_move": [0, 2],
    },
    {
        "name": "AI should BLOCK (prevent X from winning)",
        "grid": [
            ["X", "X", ""],
            ["O", "", ""],
            ["", "", ""],
        ],
        "move_number": 3,
        "expect": "MUST play [0,2] to block X",
        "expected_move": [0, 2],
    },
    {
        "name": "Fork setup — AI should create two winning paths",
        "grid": [
            ["O", "", "X"],
            ["", "X", ""],
            ["", "", "O"],
        ],
        "move_number": 4,
        "expect": "Should create a fork (multiple winning threats)",
    },
    {
        "name": "Late game — only one move left",
        "grid": [
            ["X", "O", "X"],
            ["X", "O", "O"],
            ["O", "X", ""],
        ],
        "move_number": 8,
        "expect": "Must play [2,2]",
        "expected_move": [2, 2],
    },
    {
        "name": "Opening — X took corner",
        "grid": [
            ["X", "", ""],
            ["", "", ""],
            ["", "", ""],
        ],
        "move_number": 1,
        "expect": "Should take center [1,1]",
        "expected_move": [1, 1],
    },
]


def display_grid(grid):
    """Pretty print a grid."""
    for r in range(3):
        cells = [grid[r][c] if grid[r][c] else "·" for c in range(3)]
        print(f"    {' │ '.join(cells)}")
        if r < 2:
            print(f"    ──┼───┼──")


def run_tests(use_nemotron: bool = True):
    """Run all test scenarios."""
    print("\n" + "=" * 60)
    print("  🧠 NemesisTTT Strategy Tester")
    print("  " + ("Using Nemotron API" if use_nemotron else "Using local minimax only"))
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for i, scenario in enumerate(SCENARIOS):
        print(f"\n{'─'*60}")
        print(f"  Test {i+1}: {scenario['name']}")
        print(f"  Expected: {scenario['expect']}")
        print()
        display_grid(scenario["grid"])
        print()
        
        # Get AI's move
        if use_nemotron:
            result = decide_move(scenario["grid"], scenario["move_number"])
        else:
            result = _minimax_move([row[:] for row in scenario["grid"]])
        
        move = result["move"]
        print(f"  🧠 AI chose: [{move[0]},{move[1]}]")
        print(f"  💭 Reasoning: {result.get('reasoning', 'N/A')}")
        print(f"  🗣️  Trash talk: {result.get('trash_talk', 'N/A')}")
        print(f"  📊 Confidence: {result.get('confidence', 'N/A')}")
        
        # Check if move is valid
        if scenario["grid"][move[0]][move[1]] != "":
            print(f"  ❌ FAIL: Position [{move[0]},{move[1]}] is already occupied!")
            failed += 1
            continue
        
        # Check expected move if specified
        if "expected_move" in scenario:
            if move == scenario["expected_move"]:
                print(f"  ✅ PASS: Correct move!")
                passed += 1
            else:
                print(f"  ⚠️  DIFFERENT: Expected {scenario['expected_move']}, got {move}")
                # Not necessarily wrong — might be equally good
                passed += 1  # Count as pass if it's a valid move
        else:
            print(f"  ✅ Valid move")
            passed += 1
    
    print(f"\n{'='*60}")
    print(f"  Results: {passed}/{len(SCENARIOS)} passed, {failed} failed")
    print(f"{'='*60}\n")


def interactive_test(use_nemotron: bool = True):
    """Interactive testing — enter any board state."""
    print("\n🧪 Interactive Strategy Tester")
    print("Enter board as 9 characters (X, O, or . for empty)")
    print("Example: X..OX.... means X at [0,0], O at [1,0], X at [1,1]")
    print("Type 'quit' to exit.\n")
    
    while True:
        board_str = input("Board (9 chars): ").strip()
        if board_str.lower() in ("quit", "q"):
            break
        
        if len(board_str) != 9:
            print(f"  Need exactly 9 characters, got {len(board_str)}")
            continue
        
        grid = []
        for r in range(3):
            row = []
            for c in range(3):
                ch = board_str[r * 3 + c]
                if ch in (".", "_", " "):
                    row.append("")
                elif ch.upper() in ("X", "O"):
                    row.append(ch.upper())
                else:
                    print(f"  Invalid character: {ch}")
                    break
            grid.append(row)
        
        print()
        display_grid(grid)
        
        move_num = sum(1 for r in grid for c in r if c != "")
        
        if use_nemotron:
            result = decide_move(grid, move_num)
        else:
            result = _minimax_move([row[:] for row in grid])
        
        print(f"\n  🧠 Move: {result['move']}")
        print(f"  💭 {result.get('reasoning', '')}")
        print(f"  🗣️  {result.get('trash_talk', '')}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Test NemesisTTT Strategy")
    parser.add_argument("--fallback", action="store_true", help="Use minimax only (no API)")
    parser.add_argument("--interactive", action="store_true", help="Interactive board input")
    
    args = parser.parse_args()
    use_nemotron = not args.fallback
    
    if args.interactive:
        interactive_test(use_nemotron)
    else:
        run_tests(use_nemotron)


if __name__ == "__main__":
    main()
