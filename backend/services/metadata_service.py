import asyncio
import json
import subprocess


async def fetch_video_metadata(url: str) -> dict:
    proc = await asyncio.create_subprocess_exec(
        "yt-dlp",
        "--dump-json",
        url,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        return {}

    data = json.loads(stdout.decode().strip())

    metadata = {
        "title": data.get("title"),
        "channel": data.get("channel"),
        "channel_url": data.get("channel_url"),
        "channel_subscribers": data.get("channel_follower_count"),
        "view_count": data.get("view_count"),
        "upload_date": data.get("upload_date"),
        "duration_seconds": data.get("duration"),
        "webpage_url": data.get("webpage_url"),
    }

    # Format human-readable duration
    duration = data.get("duration")
    if duration:
        h, r = divmod(duration, 3600)
        m, s = divmod(r, 60)
        if h:
            metadata["duration_display"] = f"{h}:{m:02d}:{s:02d}"
        else:
            metadata["duration_display"] = f"{m}:{s:02d}"

    # Format upload date
    upload_date = data.get("upload_date")
    if upload_date and len(upload_date) == 8:
        import datetime
        dt = datetime.datetime.strptime(upload_date, "%Y%m%d")
        metadata["upload_date_display"] = dt.strftime("%Y-%m-%d")
        metadata["upload_date_relative"] = _relative_time(dt)

    return metadata


def _relative_time(dt):
    import datetime
    now = datetime.datetime.now(dt.tzinfo) if dt.tzinfo else datetime.datetime.now()
    diff = now - dt
    if diff.days >= 365:
        years = diff.days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"
    if diff.days >= 30:
        months = diff.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    if diff.seconds >= 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    return "today"