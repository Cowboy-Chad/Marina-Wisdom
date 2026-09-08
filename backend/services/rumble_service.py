import asyncio
import os
import subprocess
import tempfile

from backend.services.openrouter_service import transcribe_audio


async def download_and_transcribe(url: str) -> str:
    tmpdir = tempfile.mkdtemp()
    output_template = os.path.join(tmpdir, "%(title)s.%(ext)s")
    try:
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp",
            "-x", "--audio-format", "mp3",
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

        transcript = await transcribe_audio(audio_path)
        return transcript
    finally:
        for f in os.listdir(tmpdir):
            os.remove(os.path.join(tmpdir, f))
        os.rmdir(tmpdir)