import asyncio
import os
import subprocess
import tempfile

from backend.services.openrouter_service import transcribe_audio


async def _compress_audio(input_path: str) -> str:
    base, ext = os.path.splitext(input_path)
    output_path = f"{base}_compressed{ext}"
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y",
        "-i", input_path,
        "-ac", "1",
        "-b:a", "32k",
        output_path,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    await proc.communicate()
    if proc.returncode != 0:
        return input_path
    return output_path


async def download_and_transcribe(url: str) -> tuple[str, float]:
    tmpdir = tempfile.mkdtemp()
    output_template = os.path.join(tmpdir, "%(title)s.%(ext)s")
    try:
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp",
            "--impersonate", "Chrome-133",
            "-x", "--audio-format", "mp3",
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            "--add-header", "Referer:https://rumble.com/",
            "-o", output_template,
            url,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"yt-dlp failed: {stderr.decode()}")

        files = os.listdir(tmpdir)
        if not files:
            raise RuntimeError("yt-dlp produced no output files")
        audio_path = os.path.join(tmpdir, files[0])

        compressed = await _compress_audio(audio_path)
        try:
            transcript, cost = await transcribe_audio(compressed)
        finally:
            if compressed != audio_path and os.path.exists(compressed):
                os.remove(compressed)

        return transcript, cost
    finally:
        for f in os.listdir(tmpdir):
            os.remove(os.path.join(tmpdir, f))
        os.rmdir(tmpdir)