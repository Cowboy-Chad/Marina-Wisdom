import asyncio
import base64
import json
import math
import mimetypes
import os
import subprocess

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
CHUNK_DURATION = int(os.environ.get("TRANSCRIPTION_CHUNK_SECONDS", "600"))  # 10 min chunks


async def _get_audio_duration(path: str) -> float:
    proc = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    out, _ = await proc.communicate()
    return float(out.decode().strip())


async def _split_audio(path: str, chunk_seconds: int, out_dir: str) -> list[str]:
    duration = await _get_audio_duration(path)
    chunks = math.ceil(duration / chunk_seconds)
    paths = []
    for i in range(chunks):
        start = i * chunk_seconds
        out_path = os.path.join(out_dir, f"chunk_{i:03d}.mp3")
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y",
            "-i", path,
            "-ss", str(start),
            "-t", str(chunk_seconds),
            "-ac", "1",
            "-b:a", "32k",
            out_path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        await proc.communicate()
        paths.append(out_path)
    return paths


async def _transcribe_chunk(audio_path: str) -> tuple[str, float]:
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
                    {"type": "input_audio", "input_audio": {"data": audio_b64, "format": "mp3"}},
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
        if resp.status_code != 200:
            raise RuntimeError(f"OpenRouter transcription failed ({resp.status_code}): {resp.text[:500]}")
        data = resp.json()
        text = data["choices"][0]["message"]["content"].strip()
        cost = data.get("usage", {}).get("cost", 0)
        return text, cost


async def transcribe_audio(audio_path: str) -> tuple[str, float]:
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not found in fabric .env or environment")

    tmpdir = os.path.dirname(audio_path)
    chunk_dir = os.path.join(tmpdir, "chunks")
    os.makedirs(chunk_dir, exist_ok=True)

    try:
        chunks = await _split_audio(audio_path, CHUNK_DURATION, chunk_dir)
        full_text = []
        total_cost = 0.0
        for path in chunks:
            text, cost = await _transcribe_chunk(path)
            full_text.append(text)
            total_cost += cost
        return "\n\n".join(full_text), total_cost
    finally:
        for f in os.listdir(chunk_dir):
            os.remove(os.path.join(chunk_dir, f))
        os.rmdir(chunk_dir)