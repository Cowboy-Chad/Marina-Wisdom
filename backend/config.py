"""Runtime configuration shared across the backend."""
import os

# The fabric CLI keeps its own config here, including the OpenRouter key.
FABRIC_ENV_PATH = os.path.expanduser("~/.config/fabric/.env")


def _read_fabric_env(name: str) -> str | None:
    """Read a single NAME=value pair out of fabric's .env file."""
    if not os.path.exists(FABRIC_ENV_PATH):
        return None
    with open(FABRIC_ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip("\"'")
    return None


def get_openrouter_api_key() -> str | None:
    """Resolve the OpenRouter API key.

    The environment wins, so a deployed instance can be configured with a plain
    env var and without fabric's config file, which does not exist in a
    container. Locally the key is not in the environment, so this falls back to
    the file the fabric CLI already uses.
    """
    return os.environ.get("OPENROUTER_API_KEY") or _read_fabric_env("OPENROUTER_API_KEY")
