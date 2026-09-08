import base64
import os

import httpx

OPENROUTER_API_KEY = None
_env_path = os.path.expanduser("~/.config/fabric/.env")
if os.path.exists(_env_path):
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("OPENROUTER_API_KEY="):
                OPENROUTER_API_KEY = line.split("=", 1)[1].strip("\"'")

OPENROUTER_BASE = os.environ.get("OPENROUTER_API_BASE_URL", "https://openrouter.ai/api/v1")
TRANSCRIPTION_MODEL = os.environ.get("TRANSCRIPTION_MODEL", "openai/gpt-audio-mini")


async def transcribe_audio(audio_path: str) -> str:
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not found in fabric .env or environment")

    with open(audio_path, "rb") as f:
        audio_data = f.read()
    audio_b64 = base64.b64encode(audio_data).decode()

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": TRANSCRIPTION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Transcribe this audio verbatim. Return only the transcribed text."},
                    {"type": "audio_url", "audio_url": {"url": f"data:audio/mpeg;base64,{audio_b64}"}},
                ],
            }
        ],
    }

    async with httpx.AsyncClient(timeout=300) as client:
        resp = await client.post(
            f"{OPENROUTER_BASE}/chat/completions",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()