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
_FALLBACK_PROMPT = "Is this item FAULTY or GOOD? Reply with one word."

# Cached client — created once, reused across calls
_client: OpenAI | None = None
_model: str | None = None


def reset_client():
    """Force re-selection of API client (call after changing .env at runtime)."""
    global _client, _model
    _client = None
    _model = None


def _get_client() -> tuple[OpenAI, str]:
    """Get (or create) the best available client. vLLM > NVIDIA NIM > OpenRouter."""
    global _client, _model
    if _client is not None:
        return _client, _model

    # 1. vLLM (local, fastest)
    vllm_url = os.getenv("VLLM_BASE_URL", "").strip()
    if vllm_url:
        _client = OpenAI(base_url=vllm_url.rstrip("/") + "/v1", api_key="not-needed")
        _model = os.getenv("VLLM_MODEL", "llava")
        return _client, _model

    # 2. NVIDIA NIM
    nv_key = os.getenv("NVIDIA_API_KEY", "")
    if nv_key and "xxxx" not in nv_key.lower():
        _client = OpenAI(
            base_url=os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
            api_key=nv_key,
        )
        _model = os.getenv("VISION_MODEL", "nvidia/nemotron-nano-12b-v2-vl")
        return _client, _model

    # 3. OpenRouter (free tier, vision models)
    or_key = os.getenv("OPENROUTER_API_KEY", "")
    if or_key and "xxxx" not in or_key.lower():
        _client = OpenAI(
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            api_key=or_key,
        )
        _model = os.getenv("OPENROUTER_VISION_MODEL", "google/gemini-2.0-flash-exp:free")
        return _client, _model

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


def _load_prompt() -> str:
    """Read prompt from disk each call — allows hot-reload without server restart."""
    if _PROMPT_PATH.exists():
        return _PROMPT_PATH.read_text()
    return _FALLBACK_PROMPT


def _parse_label(raw: str) -> str:
    """
    Extract the classification label from the VLM response.

    The prompt asks for a description line then a single label word on the last line.
    Parse the last non-empty line rather than searching the full text, so words in
    the description (e.g. "not faulty") cannot accidentally match a label.
    """
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    last = lines[-1].upper() if lines else ""
    if "NOTHING" in last:
        return "NOTHING"
    if "FAULTY" in last:
        return "FAULTY"
    if "GOOD" in last:
        return "GOOD"
    # Fallback: search full text (model didn't follow format)
    upper = raw.upper()
    if "NOTHING" in upper:
        return "NOTHING"
    if "FAULTY" in upper:
        return "FAULTY"
    return "GOOD"


def classify_item(image_bytes: bytes) -> tuple[str, float, str]:
    """
    Classify item from image bytes. Returns (label, latency_sec, raw_response).
    Label is one of: GOOD, FAULTY, NOTHING.
    """
    t0 = time.perf_counter()
    client, model = _get_client()
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    resp = client.chat.completions.create(
        model=model,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                {"type": "text", "text": _load_prompt()},
            ],
        }],
        max_tokens=128,
        temperature=0,
    )
    raw = (resp.choices[0].message.content or "").strip()
    return _parse_label(raw), time.perf_counter() - t0, raw
