"""
Supply chain QC API. WebSocket for real-time pipeline updates.

Run:
  uvicorn api.server:app --host 0.0.0.0 --port 8080

With vLLM (recommended for latency):
  vllm serve llava-hf/llava-1.5-7b-hf --port 8000
  # Then set VLLM_BASE_URL=http://localhost:8000 in .env
"""
import os
from dotenv import load_dotenv
load_dotenv()
import asyncio
import threading

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from data.event_store import get_events, get_session_stats, get_training_export, current_session

app = FastAPI(title="Supply Chain QC", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

connected: list[WebSocket] = []
_pipeline_thread: threading.Thread | None = None
_stop_event = threading.Event()
_loop: asyncio.AbstractEventLoop | None = None


async def broadcast(data: dict):
    dead = []
    for ws in connected:
        try:
            await ws.send_json(data)
        except Exception:
            dead.append(ws)
    for ws in dead:
        connected.remove(ws)


def _broadcast_sync(data: dict):
    if _loop:
        asyncio.run_coroutine_threadsafe(broadcast(data), _loop)


@app.on_event("startup")
async def startup():
    global _loop, _pipeline_thread
    _loop = asyncio.get_running_loop()
    if os.getenv("PIPELINE_AUTO_START", "true").lower() in ("true", "1", "yes"):
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from vision import check_api_configured
        if check_api_configured():
            from pipeline import run_pipeline
            _stop_event.clear()
            _pipeline_thread = threading.Thread(
                target=run_pipeline,
                args=(_broadcast_sync, _stop_event),
                daemon=True,
            )
            _pipeline_thread.start()
            print("📹 Pipeline started: camera → VLM → robot")
        else:
            print("⚠️  Pipeline not started: set NVIDIA_API_KEY or OPENROUTER_API_KEY in .env")


@app.on_event("shutdown")
async def shutdown():
    global _pipeline_thread
    _stop_event.set()
    if _pipeline_thread and _pipeline_thread.is_alive():
        _pipeline_thread.join(timeout=5)


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    connected.append(ws)
    await ws.send_json({"event": "connected"})
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        connected.remove(ws)


@app.get("/")
def root():
    return {"name": "Supply Chain QC", "status": "running"}


# ── Data / Training endpoints ──

@app.get("/api/events")
def api_events(
    session_id: str | None = Query(None),
    label: str | None = Query(None),
    limit: int = Query(100, ge=1, le=10000),
):
    """Query logged QC events with optional filters."""
    return get_events(session_id=session_id, label=label, limit=limit)


@app.get("/api/stats")
def api_stats(session_id: str | None = Query(None)):
    """Aggregated stats for a session."""
    return get_session_stats(session_id=session_id)


@app.get("/api/export/training")
def api_training_export(
    session_id: str | None = Query(None),
    label: str | None = Query(None),
):
    """Export logged data in LeRobot-compatible format for policy training."""
    data = get_training_export(session_id=session_id, label=label)
    return {
        "session_id": session_id or current_session(),
        "count": len(data),
        "format": "lerobot_compatible",
        "records": data,
    }


# ── Agent endpoints ──

class AgentRequest(BaseModel):
    prompt: str = (
        "Analyze all QC pipeline data, assess data quality, and generate "
        "a LeRobot-compatible training policy for autonomous sorting."
    )


@app.post("/api/agent/run")
async def run_agent_endpoint(req: AgentRequest):
    """Run the agentic optimizer. Returns a Server-Sent Events stream."""
    from agent.optimizer import run_agent

    async def event_stream():
        async for event in run_agent(user_request=req.prompt):
            yield f"data: {json.dumps(event, default=str)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/agent/policies")
def list_policies():
    """List previously generated training policies."""
    policies_dir = Path(__file__).resolve().parent.parent / "config" / "policies"
    if not policies_dir.exists():
        return {"policies": []}
    policies = []
    for f in sorted(policies_dir.glob("*.json"), reverse=True):
        policies.append(json.loads(f.read_text()))
    return {"policies": policies}


@app.get("/watch", response_class=HTMLResponse)
def watch():
    return """
<!DOCTYPE html>
<html><head><title>Supply Chain QC</title>
<style>body{font-family:system-ui;background:#111;color:#eee;padding:1rem}</style>
</head><body>
<h1>Supply Chain QC — Live</h1>
<pre id="log"></pre>
<script>
const ws=new WebSocket(`ws://${location.host}/ws`);
const log=document.getElementById('log');
ws.onmessage=e=>{
  const d=JSON.parse(e.data);
  const t=new Date().toLocaleTimeString();
  log.textContent+=`[${t}] ${d.event}: ${JSON.stringify(d)}\n`;
  log.scrollTop=log.scrollHeight;
};
</script></body></html>
"""
