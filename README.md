# 🎮 NemesisTTT

**AI-powered tic-tac-toe with a robotic arm — sees the board, thinks like a grandmaster, moves like a human.**

Built for UCL AI Festival Hackathon 2026.

## How It Works

```
Camera 📷 → Nemotron VLM 👁️ → Nemotron Nano 🧠 → SO-101 Arm 🤖
                                                        ↓
                                              Dashboard 📊
```

1. Human places **X** on a physical 3x3 board
2. Overhead camera captures the board
3. **Nemotron VLM** (12B) reads the board state from the photo
4. **Nemotron Nano** (30B) reasons about strategy, picks the optimal move
5. **SO-101 robotic arm** picks up an O piece and places it
6. **Dashboard** shows AI reasoning, trash talk, and game stats

## Quick Start (No Robot Needed)

```bash
# 1. Clone and install
git clone <repo-url>
cd nemesis-ttt
pip install -r requirements.txt

# 2. Set up API keys
cp .env.example .env
# Edit .env with your NVIDIA API key

# 3. Test vision with a photo
python scripts/test_vision.py --image tests/sample_board.jpg

# 4. Test strategy
python scripts/test_strategy.py

# 5. Run full game loop (keyboard mode, no robot)
python game/main.py --mode keyboard

# 6. Run with dashboard
python api/server.py  # Terminal 1
cd dashboard && npm run dev  # Terminal 2
```

## Project Structure

```
nemesis-ttt/
├── game/                   # Core game logic
│   ├── main.py             # Main game loop
│   ├── camera.py           # Board image capture
│   ├── vision.py           # Nemotron VLM → board state
│   ├── strategy.py         # Nemotron Nano → best move
│   └── state.py            # Game state management
│
├── robot/                  # SO-101 arm control
│   ├── primitives.py       # pick(), place(), home()
│   ├── calibration.json    # Board square → arm coordinates
│   └── mock_robot.py       # Fake robot for testing without hardware
│
├── prompts/                # Nemotron prompt templates
│   ├── vision.txt          # Board reading prompt
│   └── strategy.txt        # Strategy + trash talk prompt
│
├── api/                    # Backend server
│   └── server.py           # FastAPI + WebSocket
│
├── dashboard/              # React frontend (Lovable)
│   └── src/
│
├── scripts/                # Dev & test utilities
│   ├── test_vision.py      # Test VLM on sample images
│   ├── test_strategy.py    # Test strategy agent
│   └── calibrate_board.py  # Map board positions to arm coords
│
├── tests/                  # Sample board images for testing
├── requirements.txt
├── .env.example
└── README.md
```

## Models

| Model | NIM ID | Role | Fallback |
|-------|--------|------|----------|
| Nemotron VLM | `nvidia/nemotron-nano-12b-v2-vl` | Board vision | `nvidia/llama-3.1-nemotron-nano-vl-8b-v1` |
| Nemotron Nano | `nvidia/nemotron-3-nano-30b-a3b` | Strategy + codegen | OpenRouter free tier |

## Bounties

- **NVIDIA**: Multiple Nemotron models in pipeline (VLM + reasoning)
- **Encord**: Full multimodal loop (camera → AI → physical action → dashboard)
- **Lovable**: Polished real-time game dashboard

## Team

| Role | Owns |
|------|------|
| 🤖 Robot Wrangler | SO-101 setup, calibration, arm reliability |
| 🧠 AI Architect | Nemotron prompts, vision accuracy, strategy |
| 🎨 Frontend + Pitch | Dashboard, pitch deck, demo flow |
| 🔗 Integrator | Game loop, API, error handling, testing |
