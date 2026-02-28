"""
Nemotron API client with automatic fallback.
Tries: NIM hosted → OpenRouter → Self-hosted Brev
"""
import os
import json
import base64
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


def get_client(model_type: str = "text") -> tuple[OpenAI, str]:
    """
    Get the best available client + model ID.
    Tries NIM first, falls back to OpenRouter, then Brev.
    
    Args:
        model_type: "vision" or "text"
    
    Returns:
        (client, model_id) tuple
    """
    if model_type == "vision":
        model_id = os.getenv("VISION_MODEL", "nvidia/nemotron-nano-12b-v2-vl")
    else:
        model_id = os.getenv("STRATEGY_MODEL", "nvidia/nemotron-3-nano-30b-a3b")
    
    # Try 1: NVIDIA NIM hosted endpoint
    nvidia_key = os.getenv("NVIDIA_API_KEY")
    if nvidia_key and nvidia_key != "nvapi-xxxxxxxxxxxx":
        client = OpenAI(
            base_url=os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
            api_key=nvidia_key,
        )
        print(f"[NemotronClient] Using NIM hosted endpoint for {model_id}")
        return client, model_id
    
    # Try 2: OpenRouter (free tier available)
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key and openrouter_key != "sk-or-xxxxxxxxxxxx":
        client = OpenAI(
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            api_key=openrouter_key,
        )
        # OpenRouter model IDs may differ
        if model_type == "vision":
            # OpenRouter may not have VLM — fall through
            print(f"[NemotronClient] Using OpenRouter for {model_id}")
        else:
            model_id = "nvidia/nemotron-3-nano-30b-a3b:free"
            print(f"[NemotronClient] Using OpenRouter free tier for {model_id}")
        return client, model_id
    
    # Try 3: Self-hosted on Brev GPU
    brev_url = os.getenv("BREV_BASE_URL")
    if brev_url:
        client = OpenAI(
            base_url=brev_url,
            api_key="not-needed",
        )
        print(f"[NemotronClient] Using Brev self-hosted for {model_id}")
        return client, model_id
    
    raise RuntimeError(
        "No API endpoint configured! Set NVIDIA_API_KEY, OPENROUTER_API_KEY, "
        "or BREV_BASE_URL in your .env file."
    )


def chat_completion(
    messages: list[dict],
    model_type: str = "text",
    max_tokens: int = 500,
    temperature: float = 0.7,
) -> str:
    """
    Send a chat completion request to Nemotron.

    Args:
        messages: OpenAI-format messages
        model_type: "vision" or "text"
        max_tokens: Max response tokens
        temperature: Sampling temperature

    Returns:
        Response text content
    """
    client, model_id = get_client(model_type)

    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        content = response.choices[0].message.content
        if content is None:
            raise ValueError("API returned None for message content")
        return content
    except Exception as e:
        print(f"[NemotronClient] Error in chat_completion: {type(e).__name__}: {e}")
        raise


def vision_completion(image_bytes: bytes, prompt: str, max_tokens: int = 500) -> str:
    """
    Send an image + text prompt to Nemotron VLM.
    
    Args:
        image_bytes: JPEG image bytes
        prompt: Text prompt about the image
        max_tokens: Max response tokens
    
    Returns:
        Response text content
    """
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                },
                {
                    "type": "text",
                    "text": prompt,
                },
            ],
        }
    ]
    
    return chat_completion(messages, model_type="vision", max_tokens=max_tokens)
