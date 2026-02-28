"""
NemesisTTT API Server.
Provides REST endpoints + WebSocket for real-time dashboard updates.

Run: uvicorn api.server:app --host 0.0.0.0 --port 8080 --reload
"""
import os
import sys
import json
import asyncio
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from game.state import GameState
from game.strategy import decide_move

app = FastAPI(title="NemesisTTT", version="1.0.0")

# Allow dashboard to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
game = GameState()
connected_clients: list[WebSocket] = []


# === WebSocket ===

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connected_clients.append(ws)
    print(f"📡 Dashboard connected ({len(connected_clients)} clients)")
    
    # Send current state
    await ws.send_json({"event": "state", **game.to_dict()})
    
    try:
        while True:
            data = await ws.receive_json()
            
            if data.get("action") == "human_move":
                row, col = data["row"], data["col"]
                if not game.game_over and game.grid[row][col] == "":
                    game.apply_move(row, col, "X")
                    await broadcast({"event": "human_move", "move": [row, col], **game.to_dict()})
                    
                    if not game.game_over:
                        # AI responds
                        ai_response = decide_move(game.grid, len(game.moves))
                        if ai_response["move"]:
                            r, c = ai_response["move"]
                            game.apply_move(
                                r, c, "O",
                                reasoning=ai_response.get("reasoning", ""),
                                trash_talk=ai_response.get("trash_talk", ""),
                                confidence=ai_response.get("confidence", 0),
                            )
                            await broadcast({
                                "event": "ai_move",
                                "move": [r, c],
                                "reasoning": ai_response.get("reasoning", ""),
                                "trash_talk": ai_response.get("trash_talk", ""),
                                "confidence": ai_response.get("confidence", 0),
                                **game.to_dict(),
                            })
                    
                    if game.game_over:
                        winner = "human" if game.winner == "X" else ("ai" if game.winner == "O" else "draw")
                        await broadcast({"event": "game_over", "winner": winner, **game.to_dict()})
            
            elif data.get("action") == "reset":
                game.reset()
                await broadcast({"event": "reset", **game.to_dict()})
            
            elif data.get("action") == "get_state":
                await ws.send_json({"event": "state", **game.to_dict()})
    
    except WebSocketDisconnect:
        connected_clients.remove(ws)
        print(f"📡 Dashboard disconnected ({len(connected_clients)} clients)")


async def broadcast(data: dict):
    """Send data to all connected WebSocket clients."""
    disconnected = []
    for client in connected_clients:
        try:
            await client.send_json(data)
        except Exception:
            disconnected.append(client)
    for client in disconnected:
        connected_clients.remove(client)


def broadcast_sync(data: dict):
    """Sync wrapper for broadcasting from game loop."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(broadcast(data))
        else:
            loop.run_until_complete(broadcast(data))
    except Exception:
        pass  # No event loop available (running standalone)


# === REST Endpoints ===

class MoveRequest(BaseModel):
    row: int
    col: int


@app.get("/")
def root():
    return {"name": "NemesisTTT", "status": "running"}


@app.get("/game")
def get_game():
    return game.to_dict()


@app.post("/move")
def make_move(move: MoveRequest):
    """Human makes a move, AI responds."""
    if game.game_over:
        return {"error": "Game is over. POST /reset to start a new game."}
    
    if game.grid[move.row][move.col] != "":
        return {"error": f"Position [{move.row},{move.col}] is occupied."}
    
    # Human move
    game.apply_move(move.row, move.col, "X")
    
    result = {"human_move": [move.row, move.col], "game": game.to_dict()}
    
    if game.game_over:
        return result
    
    # AI move
    ai_response = decide_move(game.grid, len(game.moves))
    if ai_response["move"]:
        r, c = ai_response["move"]
        game.apply_move(
            r, c, "O",
            reasoning=ai_response.get("reasoning", ""),
            trash_talk=ai_response.get("trash_talk", ""),
            confidence=ai_response.get("confidence", 0),
        )
        result["ai_move"] = ai_response
        result["game"] = game.to_dict()
    
    return result


@app.post("/reset")
def reset_game():
    game.reset()
    return {"status": "reset", "game": game.to_dict()}


@app.post("/vision")
async def analyze_board():
    """Capture and analyze board via camera + VLM."""
    from game.camera import capture_board_auto
    from game.vision import read_board
    
    image = capture_board_auto()
    board_state = read_board(image)
    return board_state


if __name__ == "__main__":
    import uvicorn
    from dotenv import load_dotenv
    load_dotenv()
    
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8080"))
    uvicorn.run(app, host=host, port=port)
