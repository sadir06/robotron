"""
VLM client for fault detection.

Priority: vLLM (local) > NVIDIA NIM > OpenRouter (free tier)
"""
import os
import base64
import time
from pathlib import Path
from openai import OpenAI

_PROMPT_PATH = Path(__file__).parent / "prompts" / "fault_detection.txt"
PROMPT = _PROMPT_PATH.read_text() if _PROMPT_PATH.exists() else "Is this item FAULTY or GOOD? Reply with one word."


def _get_client() -> tuple[OpenAI, str]:
    """Get best available client. vLLM > NVIDIA NIM > OpenRouter."""
    # 1. vLLM (local, fastest)
    vllm_url = os.getenv("VLLM_BASE_URL", "").strip()
    if vllm_url:
        model = os.getenv("VLLM_MODEL", "llava")
        return (
            OpenAI(base_url=vllm_url.rstrip("/") + "/v1", api_key="not-needed"),
            model,
        )
    # 2. NVIDIA NIM
    nv_key = os.getenv("NVIDIA_API_KEY", "")
    if nv_key and "xxxx" not in nv_key.lower():
        return (
            OpenAI(
                base_url=os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
                api_key=nv_key,
            ),
            os.getenv("VISION_MODEL", "nvidia/nemotron-nano-12b-v2-vl"),
        )
    # 3. OpenRouter (free tier, vision models)
    or_key = os.getenv("OPENROUTER_API_KEY", "")
    if or_key and "xxxx" not in or_key.lower():
        model = os.getenv("OPENROUTER_VISION_MODEL", "google/gemini-2.0-flash-exp:free")
        return (
            OpenAI(
                base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
                api_key=or_key,
            ),
            model,
        )
    raise RuntimeError(
        "No VLM API configured. Add to .env:\n"
        "  • NVIDIA_API_KEY=your-key  (get from build.nvidia.com)\n"
        "  • OPENROUTER_API_KEY=your-key  (get from openrouter.ai, free tier)\n"
        "  • VLLM_BASE_URL=http://localhost:8000  (if running vLLM locally)"
    )


def check_api_configured() -> bool:
    """Return True if at least one API is configured."""
    try:
        _get_client()
        return True
    except RuntimeError:
        return False


def classify_item(image_bytes: bytes) -> tuple[str, float, str]:
    """
    Classify item. Returns (label, latency_sec, raw_response).
    Label: FAULTY, GOOD, or NOTHING.
    """
    t0 = time.perf_counter()
    client, model = _get_client()
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                {"type": "text", "text": PROMPT},
            ],
        }
    ]
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=128,
        temperature=0,
    )
    raw = (resp.choices[0].message.content or "").strip()
    text_upper = raw.upper()
    latency = time.perf_counter() - t0
    if "FAULTY" in text_upper:
        return "FAULTY", latency, raw
    if "NOTHING" in text_upper:
        return "NOTHING", latency, raw
    return "GOOD", latency, raw
