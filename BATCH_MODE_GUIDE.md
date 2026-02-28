# Batch Processing Guide

## What It Does

The batch processor reads a folder of board images (from a stream/recording) and:

1. **Reads each board image** using Nemotron VLM (vision model)
2. **Detects human moves** by comparing consecutive board states
3. **Decides AI moves** using Nemotron strategy
4. **Executes moves** with the robot (mock or real)

## Usage

### Basic Usage (Mock Robot)
```bash
python game/main.py --mode batch --folder /path/to/images
```

### With Real Robot
```bash
python game/main.py --mode batch --folder /path/to/images --robot real
```

### Advanced Options

```bash
# Skip first 10 images (camera warmup)
python game/main.py --mode batch --folder /path/to/images --skip 10

# Pause 2 seconds between processing each image
python game/main.py --mode batch --folder /path/to/images --pause 2.0

# All options together
python game/main.py --mode batch \
  --folder /path/to/images \
  --robot mock \
  --skip 5 \
  --pause 1.5
```

## Folder Structure

Your image folder should have board images in any of these formats:
- `.jpg` / `.jpeg`
- `.png`
- `.bmp`
- `.gif`

Images will be processed **alphabetically** by filename, so name them:
```
frame_001.jpg
frame_002.jpg
frame_003.jpg
...
frame_100.jpg
```

## What Happens

For each image:

1. 📸 **Vision Phase**: Nemotron VLM reads the board state
2. 🎯 **Detect Human Move**: Compares to previous board state
3. 🧠 **AI Thinks**: Nemotron decides its move
4. 🤖 **Execute**: Robot picks and places the O piece
5. 📊 **Display**: Shows current board state

## Example Output

```
════════════════════════════════════════════════════════════
🎮 NemesisTTT Batch Processor
📁 Folder: /path/to/images
🖼️  Total images: 50
🤖 Robot: mock
════════════════════════════════════════════════════════════

────────────────────────────────────────────────────────────
📸 Image 1/50: frame_001.jpg
────────────────────────────────────────────────────────────
👁️  Nemotron VLM analyzing board...
👁️  Board state: [["X", "", ""], ["", "", ""], ["", "", ""]]

🧠 Nemotron thinking about strategy...
🧠 AI chooses: [1,1]
💬 Reasoning: Taking center control

🤖 Executing move: O at [1,1]
════════════════════════════════════════════════════════════
🤖 EXECUTING MOVE: O → [1,1]
════════════════════════════════════════════════════════════
🤖 ARM: Moving to piece tray...
🤖 ARM: Picking up O piece
🤖 ARM: Lifting piece
🤖 ARM: Moving to board position [1,1] (middle-center)
🤖 ARM: Lowering piece to board
🤖 ARM: Releasing piece at [1,1]
🤖 ARM: Piece placed! ✓
🤖 ARM: Returning to home position
════════════════════════════════════════════════════════════

────────────────────────────────────────────────────────────
 X │   │
───┼───┼───
   │ O │
───┼───┼───
   │   │
────────────────────────────────────────────────────────────

⏸️  Waiting 0.5s before next image...
```

## For Live Streams

If you have a live stream generating frames:

1. **Save frames to a folder** as they're received
2. **Run the batch processor** pointing to that folder
3. It processes images **alphabetically in order**

Option: Use `--skip N` to skip initial warmup frames

## Integration with Streaming

You can use this with:
- OpenCV video capture (save every nth frame)
- GStreamer pipelines
- HTTP live streaming (HLS) downloads
- Pre-recorded video files (frame extraction)

Example: Extract frames from video
```bash
ffmpeg -i video.mp4 frames/frame_%03d.jpg
python game/main.py --mode batch --folder frames
```
