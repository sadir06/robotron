"""
Strategy module — Nemotron reasoning agent picks the best move.
Also includes a local minimax fallback for guaranteed optimal play.
"""
import json
from pathlib import Path
from game.nemotron_client import chat_completion

STRATEGY_PROMPT = Path(__file__).parent.parent / "prompts" / "strategy.txt"


def decide_move(grid: list[list[str]], move_number: int = 0) -> dict:
    """
    Ask Nemotron to pick the best move and generate trash talk.
    Falls back to minimax if Nemotron fails.
    
    Args:
        grid: Current 3x3 board state
        move_number: How many total moves have been made
    
    Returns:
        {
            "move": [row, col],
            "reasoning": "why this move",
            "trash_talk": "witty comment",
            "is_winning_move": bool,
            "confidence": float
        }
    """
    empty = _get_empty(grid)
    
    if not empty:
        return {
            "move": None,
            "reasoning": "No moves available",
            "trash_talk": "Looks like we're all tied up. Rematch?",
            "is_winning_move": False,
            "confidence": 1.0,
        }
    
    # Build prompt
    prompt_template = STRATEGY_PROMPT.read_text()
    prompt = prompt_template.format(
        board_state=json.dumps(grid),
        empty_positions=json.dumps(empty),
        move_number=move_number,
    )
    
    print("🧠 Nemotron thinking about strategy...")
    
    try:
        raw = chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model_type="text",
            max_tokens=2048,
            temperature=0.8,
        )
        
        result = _parse_json(raw)
        
        # Validate the move is actually empty
        move = result.get("move")
        if move and grid[move[0]][move[1]] == "":
            print(f"🧠 AI chooses: [{move[0]},{move[1]}]")
            print(f"💬 Reasoning: {result.get('reasoning', '')}")
            print(f"🗣️  Trash talk: {result.get('trash_talk', '')}")
            return result
        else:
            print(f"⚠️  Nemotron picked invalid move {move}, falling back to minimax")
    except Exception as e:
        print(f"⚠️  Nemotron strategy failed: {e}, falling back to minimax")
    
    # Fallback: local minimax (guaranteed optimal)
    return _minimax_move(grid)


def _minimax_move(grid: list[list[str]]) -> dict:
    """Local minimax — guaranteed optimal play. Used as fallback."""
    best_score = -float("inf")
    best_move = None
    
    for r in range(3):
        for c in range(3):
            if grid[r][c] == "":
                grid[r][c] = "O"
                score = _minimax(grid, False)
                grid[r][c] = ""
                if score > best_score:
                    best_score = score
                    best_move = [r, c]
    
    is_winning = _check_winner_after(grid, best_move, "O") if best_move else False
    
    return {
        "move": best_move,
        "reasoning": f"Minimax fallback selected [{best_move[0]},{best_move[1]}]",
        "trash_talk": "My backup brain is still smarter than you. 🤖",
        "is_winning_move": is_winning,
        "confidence": 1.0,
    }


def _minimax(grid: list[list[str]], is_maximizing: bool) -> int:
    """Minimax algorithm. O is maximizing, X is minimizing."""
    winner = _check_winner(grid)
    if winner == "O":
        return 1
    if winner == "X":
        return -1
    if all(grid[r][c] != "" for r in range(3) for c in range(3)):
        return 0
    
    if is_maximizing:
        best = -float("inf")
        for r in range(3):
            for c in range(3):
                if grid[r][c] == "":
                    grid[r][c] = "O"
                    best = max(best, _minimax(grid, False))
                    grid[r][c] = ""
        return best
    else:
        best = float("inf")
        for r in range(3):
            for c in range(3):
                if grid[r][c] == "":
                    grid[r][c] = "X"
                    best = min(best, _minimax(grid, True))
                    grid[r][c] = ""
        return best


def _check_winner(grid: list[list[str]]) -> str | None:
    """Check for winner."""
    for r in range(3):
        if grid[r][0] == grid[r][1] == grid[r][2] != "":
            return grid[r][0]
    for c in range(3):
        if grid[0][c] == grid[1][c] == grid[2][c] != "":
            return grid[0][c]
    if grid[0][0] == grid[1][1] == grid[2][2] != "":
        return grid[0][0]
    if grid[0][2] == grid[1][1] == grid[2][0] != "":
        return grid[0][2]
    return None


def _check_winner_after(grid, move, player) -> bool:
    """Check if placing player at move would win."""
    grid[move[0]][move[1]] = player
    won = _check_winner(grid) == player
    grid[move[0]][move[1]] = ""
    return won


def _get_empty(grid: list[list[str]]) -> list[list[int]]:
    """Get empty positions."""
    return [[r, c] for r in range(3) for c in range(3) if grid[r][c] == ""]


def _parse_json(text: str) -> dict:
    """Extract JSON from response."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(text[start:end])
        raise
