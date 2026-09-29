# Deploy image for Render.
#
# A Dockerfile is required rather than Render's native Python runtime: this app
# shells out to fabric (a Go binary), yt-dlp, ffmpeg and ffprobe, none of which
# the native runtime provides.
FROM python:3.12-slim

# ffmpeg/ffprobe do the audio extraction; ca-certificates and curl are needed to
# fetch the fabric binary below.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

# fabric is a single static Go binary. Pinned by version *and* checksum: an
# unverified download here would be arbitrary code execution in the deployment.
ARG FABRIC_VERSION=1.4.473
ARG FABRIC_SHA256=c74b451557cdd5d00dc4b14c7adcc1e4c87455f543d84ce1e69c76922fb27076
RUN curl -fsSL -o /tmp/fabric.tar.gz \
        "https://github.com/danielmiessler/fabric/releases/download/v${FABRIC_VERSION}/fabric_Linux_x86_64.tar.gz" \
    && echo "${FABRIC_SHA256}  /tmp/fabric.tar.gz" | sha256sum -c - \
    && tar -xzf /tmp/fabric.tar.gz -C /usr/local/bin fabric \
    && chmod +x /usr/local/bin/fabric \
    && rm /tmp/fabric.tar.gz \
    && fabric --version

WORKDIR /app

# Dependencies first: this layer only rebuilds when requirements.txt changes.
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt yt-dlp

# fabric loads patterns from ~/.config/fabric/patterns, and the app lists them at
# runtime for the pattern picker. Vendored rather than downloaded at boot so a
# restart never depends on GitHub being reachable.
COPY fabric-patterns/ /root/.config/fabric/patterns/

# fabric 1.4.473 exits 1 on every invocation when ~/.config/fabric/.env is
# missing, including --listpatterns and --listmodels, which need no credentials:
# it prints "error loading .env file" and stops. Without this file /api/patterns
# and /api/models returned 500 and no analysis could run at all. The file only
# has to exist — the API key arrives at runtime as OPENROUTER_API_KEY, which
# fabric reads from the environment (verified: an invalid value is sent to
# OpenRouter and rejected as 401, not reported as missing).
#
# Deliberately empty. No credential is ever baked into the image.
RUN touch /root/.config/fabric/.env

COPY backend/ /app/backend/

# No database lives in this image. Deployed, DATABASE_URL points at Render
# Postgres; locally, the app falls back to a SQLite file in the repo root. The
# only thing written inside the container is temporary audio, under /tmp.

# The frontend is deliberately not built or copied here. Netlify builds it and
# proxies /api/* to this service, so the browser only ever talks to the Netlify
# origin and no cross-origin request happens. Shipping it in the image as well
# would mean committing build output to git, since Render builds from the repo.

ENV HOST=0.0.0.0 \
    PYTHONUNBUFFERED=1

# Render injects PORT and expects the app to listen on it. No --reload here: that
# is a development convenience that watches the filesystem for changes.
CMD ["sh", "-c", "python3 -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
