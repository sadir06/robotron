"""
Run the supply chain QC pipeline.

Standalone (no API):
  python run.py

With API + WebSocket:
  python -m uvicorn api.server:app --host 0.0.0.0 --port 8080
"""
import os
import sys
from dotenv import load_dotenv
load_dotenv()

if __name__ == "__main__":
    from vision import check_api_configured

    print("Supply chain QC — camera → VLM → robot")
    print("Press Ctrl+C to stop\n")

    if not check_api_configured():
        print("ERROR: No VLM API configured. Add to your .env file:\n")
        print("  NVIDIA_API_KEY=your-key")
        print("    → Get from https://build.nvidia.com\n")
        print("  OPENROUTER_API_KEY=your-key")
        print("    → Get from https://openrouter.ai (free tier)\n")
        sys.exit(1)

    from pipeline import run_pipeline

    def on_event(data: dict):
        ev = data.get("event", "")
        if "raw_response" in data:
            print(f"  👁️  VLM says: \"{data['raw_response']}\"")
        if ev == "item_processed":
            print(f"  → {data.get('label')} → robot to {data.get('action')} pile")
        elif ev == "item_nothing":
            print(f"  → NOTHING in view (no robot action)")
        print(data)

    try:
        run_pipeline(broadcast=on_event)
    except KeyboardInterrupt:
        print("\nStopped")
