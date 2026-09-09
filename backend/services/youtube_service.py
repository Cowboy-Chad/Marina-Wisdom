from youtube_transcript_api import YouTubeTranscriptApi


def _extract_video_id(url: str) -> str | None:
    import re
    patterns = [
        r"(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})",
        r"(?:embed/)([a-zA-Z0-9_-]{11})",
        r"(?:shorts/)([a-zA-Z0-9_-]{11})",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None


async def fetch_transcript(url: str) -> str:
    video_id = _extract_video_id(url)
    if not video_id:
        raise ValueError(f"Could not extract YouTube video ID from URL: {url} (does not look like a valid YouTube URL)")

    yt = YouTubeTranscriptApi()
    fetched = yt.fetch(video_id)
    return " ".join(s.text for s in fetched.snippets)