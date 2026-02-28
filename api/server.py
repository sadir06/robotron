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

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

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
