import asyncio
import subprocess


async def run_fabric(pattern: str, input_text: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "fabric",
        "-p", pattern,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(input=input_text.encode()), timeout=300)
    except asyncio.TimeoutError:
        proc.kill()
        raise RuntimeError(f"fabric analysis timed out after 300s for pattern '{pattern}'")
    if proc.returncode != 0:
        raise RuntimeError(f"fabric exited code {proc.returncode}: {stderr.decode()}")
    return stdout.decode().strip()


async def list_patterns() -> list[dict]:
    proc = await asyncio.create_subprocess_exec(
        "fabric",
        "--listpatterns",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"fabric --listpatterns failed: {stderr.decode()}")
    names = [line.strip() for line in stdout.decode().splitlines() if line.strip()]
    return [{"name": n, "description": ""} for n in names]


async def read_pattern(pattern: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "fabric",
        "--readpattern", pattern,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"fabric --readpattern failed: {stderr.decode()}")
    return stdout.decode()