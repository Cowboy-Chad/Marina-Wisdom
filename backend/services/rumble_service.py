import asyncio
import json
import os
import re
import subprocess
import tempfile

import cloudscraper
import requests
from backend.services.openrouter_service import transcribe_audio

_SCRAPER = None


def _get_scraper():
    global _SCRAPER
    if _SCRAPER is None:
        _SCRAPER = cloudscraper.create_scraper()
    return _SCRAPER


def _extract_brace_block(text: str, start: int) -> str | None:
    pos = text.index("{", start)
    depth = 0
    in_string = False
    escape = False
    for i in range(pos, len(text)):
        c = text[i]
        if escape:
            escape = False
            continue
        if c == "\\":
            escape = True
            continue
        if c == '"' and not escape:
            in_string = not in_string
        if not in_string:
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return text[pos : i + 1]
    return None


def _extract_embed_id(html: str) -> str | None:
    m = re.search(r'"video":"([a-z0-9]+)"', html)
    if m:
        return m.group(1)
    m = re.search(r'embed/([a-z0-9]+)', html)
    if m:
        return m.group(1)
    return None


FORMAT_PRIORITY = {"aac": 0, "mp3": 0, "m4a": 0, "ogg": 0, "wav": 0, "flac": 0,
                   "mp4": 1, "webm": 1,
                   "m3u8": 2,
                   "tar": 3}


def _format_score(url: str) -> int:
    ext = url.rsplit(".", 1)[-1].split("?")[0].lower()
    return FORMAT_PRIORITY.get(ext, 99)


def _find_urls(data: object, depth: int = 0) -> list[tuple[str, int, int]]:
    if depth > 10:
        return []
    results = []
    if isinstance(data, dict):
        url = data.get("url")
        if isinstance(url, str) and url.startswith("http"):
            meta = data.get("meta", {})
            bitrate = meta.get("bitrate", 0) if isinstance(meta, dict) else 0
            results.append((url, _format_score(url), bitrate))
        for v in data.values():
            results.extend(_find_urls(v, depth + 1))
    elif isinstance(data, list):
        for v in data:
            results.extend(_find_urls(v, depth + 1))
    return results


def _pick_best_url(candidates: list[tuple[str, int, int]]) -> str | None:
    if not candidates:
        return None
    candidates.sort(key=lambda x: (x[1], -x[2]))
    return candidates[0][0]


def _get_best_video_url(html: str) -> str | None:
    idx = html.find('"ua"')
    if idx >= 0:
        ua_block = _extract_brace_block(html, idx + 4)
        if ua_block:
            ua = json.loads(ua_block)
            candidates = _find_urls(ua)
            best = _pick_best_url(candidates)
            if best:
                return best
    idx = html.find('"u"')
    if idx >= 0:
        u_block = _extract_brace_block(html, idx + 2)
        if u_block:
            u = json.loads(u_block)
            candidates = _find_urls(u)
            best = _pick_best_url(candidates)
            if best:
                return best
    return None


async def download_and_transcribe(url: str) -> tuple[str, float]:
    tmpdir = tempfile.mkdtemp()
    try:
        scraper = _get_scraper()

        resp = await asyncio.to_thread(scraper.get, url, timeout=30)
        resp.raise_for_status()

        embed_id = _extract_embed_id(resp.text)
        if not embed_id:
            raise RuntimeError("Could not find embed ID on Rumble page")

        embed_url = f"https://rumble.com/embed/{embed_id}"
        resp = await asyncio.to_thread(scraper.get, embed_url, timeout=30)
        resp.raise_for_status()

        video_url = _get_best_video_url(resp.text)
        if not video_url:
            raise RuntimeError("Could not find any playable URL in Rumble embed data")

        ext = video_url.rsplit(".", 1)[-1].split("?")[0].lower()
        audio_path = os.path.join(tmpdir, f"audio.{ext}")

        def _download():
            r = requests.get(
                video_url,
                headers={"Referer": "https://rumble.com/"},
                timeout=600,
            )
            r.raise_for_status()
            with open(audio_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        if ext == "m3u8":
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-y",
                "-headers", "Referer: https://rumble.com/\r\n",
                "-i", video_url,
                "-ac", "1",
                "-b:a", "32k",
                os.path.join(tmpdir, "audio.mp3"),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            await proc.communicate()
            if proc.returncode != 0:
                raise RuntimeError("ffmpeg failed to download HLS stream")
            audio_path = os.path.join(tmpdir, "audio.mp3")
        elif ext == "tar":
            raise RuntimeError("Cannot play .tar container format")
        else:
            await asyncio.to_thread(_download)

        compressed = audio_path
        if ext != "mp3":
            base, _ = os.path.splitext(audio_path)
            compressed_path = f"{base}_compressed.mp3"
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-y",
                "-i", audio_path,
                "-ac", "1",
                "-b:a", "32k",
                compressed_path,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            await proc.communicate()
            if proc.returncode == 0:
                compressed = compressed_path

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