import asyncio
import os
import subprocess

DEFAULT_MODEL = os.environ.get("FABRIC_MODEL", "deepseek/deepseek-v4-flash")
DEFAULT_VENDOR = os.environ.get("FABRIC_VENDOR", "OpenRouter")
FABRIC_TIMEOUT = int(os.environ.get("FABRIC_TIMEOUT", "300"))


async def run_fabric(pattern: str, input_text: str, model: str | None = None, vendor: str | None = None) -> str:
    cmd = ["fabric", "-p", pattern]
    cmd.extend(["-m", model or DEFAULT_MODEL])
    if vendor or DEFAULT_VENDOR:
        cmd.extend(["-V", vendor or DEFAULT_VENDOR])

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(input=input_text.encode()), timeout=FABRIC_TIMEOUT)
    except asyncio.TimeoutError:
        proc.kill()
        raise RuntimeError(f"fabric analysis timed out after {FABRIC_TIMEOUT}s for pattern '{pattern}'")
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


async def list_models() -> list[str]:
    proc = await asyncio.create_subprocess_exec(
        "fabric",
        "--listmodels",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"fabric --listmodels failed: {stderr.decode()}")
    models = []
    for line in stdout.decode().splitlines():
        line = line.strip()
        if "|" in line:
            parts = line.split("|")
            if len(parts) >= 2:
                models.append(parts[1].strip())
    return models


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