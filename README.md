# Supply Chain QC — VLM + SO-101 Robot

**Continuous video → VLM fault detection → robotic arm sorting**

3rd-person camera watches items on a conveyor. NVIDIA Nemotron (or vLLM) classifies each as **FAULTY** or **GOOD**. The SO-101 arm moves faulty items left, good items right.

## Architecture

```
Camera (continuous) → Frame → VLM (vLLM/NIM) → FAULTY | GOOD
                                              ↓
                                    Robot: move_left() | move_right()
                                              ↓
                                    WebSocket broadcast
```

## Quick Start

### 1. OpenRouter (free, no GPU)

```bash
cp .env.example .env
# Add: OPENROUTER_API_KEY=your-key  (from openrouter.ai)
python run.py
```

### 2. NVIDIA NIM

```bash
cp .env.example .env
# Add: NVIDIA_API_KEY=your-key
python run.py
```

### 3. vLLM (fastest, needs GPU)

```bash
vllm serve llava-hf/llava-1.5-7b-hf --port 8000
# In .env: VLLM_BASE_URL=http://localhost:8000
python run.py
```

### 4. External USB Camera

```bash
python scripts/list_cameras.py   # Find your camera index
# In .env: CAMERA_INDEX=1       # Use 1, 2, 3... for USB cameras
```

### 5. With API + WebSocket

```bash
python -m uvicorn api.server:app --host 0.0.0.0 --port 8080
# Open http://localhost:8080/watch for live events
```

## Project Structure

```
├── camera.py         # Continuous frame capture
├── vision.py         # VLM client (vLLM primary, NIM fallback)
├── pipeline.py       # Main loop: frame → classify → robot
├── run.py            # Standalone runner
├── robot/
│   ├── primitives.py # move_to_left_pile(), move_to_right_pile() — placeholders
│   └── mock_robot.py # No hardware
├── prompts/
│   └── fault_detection.txt
├── api/
│   └── server.py     # FastAPI + WebSocket
└── .env
```

## Robot Scripts (Placeholders)

Replace in `robot/primitives.py`:

- `move_to_left_pile()` — move item to faulty pile
- `move_to_right_pile()` — move item to good pile

Set `ROBOT_ENABLED=true` when hardware is ready.

## WebSocket Events

| Event           | Payload                                   |
|-----------------|-------------------------------------------|
| `item_processed`| `item_id`, `label`, `latency_ms`, `action`|
| `started`       | Pipeline running                          |
| `error`         | `message`                                 |
