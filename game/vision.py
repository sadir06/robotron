"""
Vision module — sends board image to Nemotron VLM, returns board state.
"""
import json
from pathlib import Path
from game.nemotron_client import vision_completion, chat_completion

VISION_PROMPT = Path(__file__).parent.parent / "prompts" / "vision.txt"


def read_board(image_bytes: bytes) -> dict:
    """
    Send board image to Nemotron VLM and parse the board state.
    
    Args:
        image_bytes: JPEG image of the board
    
    Returns:
        {"grid": [["X","","O"], ["","X",""], ["","",""]]}
    """
    prompt = VISION_PROMPT.read_text()
    
    print("👁️  Nemotron VLM analyzing board...")
    raw_response = vision_completion(image_bytes, prompt, max_tokens=300)
    
    # Parse JSON from response (handle markdown code blocks)
    board_state = _parse_json(raw_response)
    
    # Validate
    _validate_board(board_state)
    
    print(f"👁️  Board state: {board_state['grid']}")
    return board_state


def read_board_simulated(grid: list[list[str]]) -> dict:
    """
    Skip vision — directly provide a board state for testing without camera.
    
    Args:
        grid: 3x3 grid like [["X","",""], ["","O",""], ["","",""]]
    
    Returns:
        Same format as read_board()
    """
    return {"grid": grid}


def _parse_json(text: str) -> dict:
    """Extract JSON from response, handling markdown code blocks."""
    text = text.strip()
    
    # Remove markdown code blocks if present
    if text.startswith("```"):
        # Remove first line (```json or ```)
        lines = text.split("\n")
        lines = lines[1:]  # remove opening ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]  # remove closing ```
        text = "\n".join(lines)
    
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        # Try to find JSON object in the text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        raise ValueError(f"Failed to parse VLM response as JSON: {e}\nRaw: {text}")


def _validate_board(board_state: dict):
    """Validate the board state structure."""
    if "grid" not in board_state:
        raise ValueError(f"Missing 'grid' key in board state: {board_state}")
    
    grid = board_state["grid"]
    if len(grid) != 3:
        raise ValueError(f"Grid must have 3 rows, got {len(grid)}")
    
    for i, row in enumerate(grid):
        if len(row) != 3:
            raise ValueError(f"Row {i} must have 3 columns, got {len(row)}")
        for j, cell in enumerate(row):
            if cell not in ("X", "O", ""):
                raise ValueError(f"Invalid cell value at [{i},{j}]: '{cell}'. Must be 'X', 'O', or ''")
    
    # Count pieces — sanity check
    x_count = sum(row.count("X") for row in grid)
    o_count = sum(row.count("O") for row in grid)
    
    if x_count < o_count:
        print(f"⚠️  Warning: X has fewer pieces ({x_count}) than O ({o_count}). X goes first.")
    if x_count > o_count + 1:
        print(f"⚠️  Warning: X has {x_count} pieces, O has {o_count}. Seems off.")
