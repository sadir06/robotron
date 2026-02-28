"""
Game state management for tic-tac-toe.
"""
from dataclasses import dataclass, field
from typing import Optional
import json
import time


@dataclass
class Move:
    player: str  # "X" or "O"
    position: list[int]  # [row, col]
    reasoning: str = ""
    trash_talk: str = ""
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class GameState:
    grid: list[list[str]] = field(default_factory=lambda: [["", "", ""], ["", "", ""], ["", "", ""]])
    current_player: str = "X"  # Human is X, AI is O
    moves: list[Move] = field(default_factory=list)
    winner: Optional[str] = None
    is_draw: bool = False
    game_over: bool = False
    game_id: str = field(default_factory=lambda: str(int(time.time())))
    
    def apply_move(self, row: int, col: int, player: str, reasoning: str = "", trash_talk: str = "", confidence: float = 0.0):
        """Apply a move to the board."""
        if self.grid[row][col] != "":
            raise ValueError(f"Position [{row},{col}] is already occupied by {self.grid[row][col]}")
        if self.game_over:
            raise ValueError("Game is already over")
        
        self.grid[row][col] = player
        self.moves.append(Move(
            player=player,
            position=[row, col],
            reasoning=reasoning,
            trash_talk=trash_talk,
            confidence=confidence,
        ))
        
        # Check for winner
        self.winner = self._check_winner()
        if self.winner:
            self.game_over = True
        elif self._is_full():
            self.is_draw = True
            self.game_over = True
        else:
            self.current_player = "O" if player == "X" else "X"
    
    def get_empty_positions(self) -> list[list[int]]:
        """Get all empty board positions."""
        positions = []
        for r in range(3):
            for c in range(3):
                if self.grid[r][c] == "":
                    positions.append([r, c])
        return positions
    
    def _check_winner(self) -> Optional[str]:
        """Check if there's a winner. Returns 'X', 'O', or None."""
        g = self.grid
        
        # Rows
        for r in range(3):
            if g[r][0] == g[r][1] == g[r][2] != "":
                return g[r][0]
        
        # Columns
        for c in range(3):
            if g[0][c] == g[1][c] == g[2][c] != "":
                return g[0][c]
        
        # Diagonals
        if g[0][0] == g[1][1] == g[2][2] != "":
            return g[0][0]
        if g[0][2] == g[1][1] == g[2][0] != "":
            return g[0][2]
        
        return None
    
    def _is_full(self) -> bool:
        """Check if all squares are filled."""
        return all(self.grid[r][c] != "" for r in range(3) for c in range(3))
    
    def to_display(self) -> str:
        """Pretty print the board."""
        rows = []
        for r in range(3):
            cells = []
            for c in range(3):
                val = self.grid[r][c]
                cells.append(val if val else "·")
            rows.append(" │ ".join(cells))
        separator = "──┼───┼──"
        return f"\n{separator}\n".join(rows)
    
    def to_dict(self) -> dict:
        """Serialize for WebSocket / dashboard."""
        return {
            "game_id": self.game_id,
            "grid": self.grid,
            "current_player": self.current_player,
            "winner": self.winner,
            "is_draw": self.is_draw,
            "game_over": self.game_over,
            "moves": [
                {
                    "player": m.player,
                    "position": m.position,
                    "reasoning": m.reasoning,
                    "trash_talk": m.trash_talk,
                    "confidence": m.confidence,
                }
                for m in self.moves
            ],
            "move_count": len(self.moves),
        }
    
    def reset(self):
        """Start a new game."""
        self.grid = [["", "", ""], ["", "", ""], ["", "", ""]]
        self.current_player = "X"
        self.moves = []
        self.winner = None
        self.is_draw = False
        self.game_over = False
        self.game_id = str(int(time.time()))
