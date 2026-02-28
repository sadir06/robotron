# Single Image Processing Guide

## Overview

Process one board image and get the AI's next move based on:
1. **VLM Reading** - Nemotron reads the board state from the image
2. **Strategy** - Nemotron decides the best move
3. **Output** - Returns the next move with reasoning

## Quick Start

### Generate Test Images
```bash
python scripts/generate_test_images.py --output test_images
```

This creates 6 test scenarios based on test_strategy.py:
- 01_empty_board_center.jpg - X in center, AI should take corner
- 02_ai_should_win.jpg - AI should complete top row to win
- 03_ai_should_block.jpg - AI must block X from winning
- 04_fork_setup.jpg - AI should create two winning threats
- 05_late_game_one_move.jpg - Only one move left
- 06_opening_corner.jpg - X took corner, AI should take center

### Process a Single Image
```bash
python game/process_image.py test_images/02_ai_should_win.jpg
```

Output:
```
📸 Processing: test_images/02_ai_should_win.jpg
────────────────────────────────────────────────

👁️  Nemotron VLM analyzing board...
👁️  Board state: [['O', 'O', ''], ['X', 'X', ''], ['', '', '']]

🎯 Current board state:
   O │ O │ ·
   ──┼───┼──
   X │ X │ ·
   ──┼───┼──
   · │ · │ ·
   Moves so far: 4

🧠 AI is thinking about the next move...

==================================================
📍 NEXT MOVE: O at [0,2]
==================================================
💭 Reasoning: I complete the top row to win instantly.
🗣️  Trash talk: Your X's can't stop my O's, try again.
📊 Confidence: 0.99
```

## Alternative Syntax
```bash
python game/process_image.py --image test_images/01_empty_board_center.jpg
```

## JSON Output
Get structured JSON output:
```bash
python game/process_image.py test_images/02_ai_should_win.jpg --json
```

Output:
```json
{
  "board_state": [
    ["O", "O", ""],
    ["X", "X", ""],
    ["", "", ""]
  ],
  "move": [0, 2],
  "reasoning": "I complete the top row to win instantly.",
  "trash_talk": "Your X's can't stop my O's, try again.",
  "confidence": 0.99,
  "game_over": false
}
```

## Workflow

### For Real Images From Camera/Stream
1. When you capture a frame from livestream/camera, save it as JPEG
2. Run `python game/process_image.py /path/to/frame.jpg`
3. Get back the AI's move
4. Send move to robot: `robot.execute_move(row, col, "O")`

### For Custom Board States
1. Create your own test images
2. Process them: `python game/process_image.py your_image.jpg`
3. Verify the AI makes the right decision

## Why This Pipeline

```
Image → VLM reads state → Strategy decides move → JSON output
  ↓           ↓                   ↓
JPEG      Board grid        Move [row,col]
          validated          + reasoning
```

**Your image can be from:**
- Webcam capture
- Live stream frame
- Recorded video (extract frames with ffmpeg)
- Any photo of a tic-tac-toe board

**The system will:**
1. Use Nemotron VLM (12B) to read what's on the board
2. Use Nemotron strategy (30B) to decide the move
3. Return the best next move with AI personality
