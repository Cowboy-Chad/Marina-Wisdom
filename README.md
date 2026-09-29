# CVE-OSINT-1

OSINT analysis app leveraging [Fabric](https://github.com/danielmiessler/fabric) AI patterns for automated analysis of multimedia content.

Free software under the [GPL-3.0](LICENSE), by [Cowboy-Chad](https://github.com/Cowboy-Chad).

It analyzes videos from **one channel only** — Marina Jacobi's official Rumble
channel, [rumble.com/c/MarinaJacobi](https://rumble.com/c/MarinaJacobi). There is
no open URL or channel search. Each distinct video is transcribed once and the
transcript is shared and reused, which is what keeps the running cost bounded.

## Architecture

```
Browser ──▶ FastAPI ──▶ fabric CLI ──▶ OpenRouter API
                │  │
                │  └── yt-dlp / ffmpeg (audio) ──▶ OpenRouter (transcription)
                └── SQLite (repo root locally, Render disk when deployed)
```

Deployed, the frontend is served by Netlify and the API by Render. Netlify
proxies `/api/*` to Render, so the browser only ever makes same-origin requests
and no CORS configuration is needed.

Locally the backend serves both the API and the built frontend on one origin
(http://localhost:5173). There is nothing else to start.

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20.19+ (Vite 8 requires it)
- [Fabric CLI](https://github.com/danielmiessler/fabric) installed and configured
- OpenRouter API key (in `~/.config/fabric/.env`, or as `OPENROUTER_API_KEY`)
- `yt-dlp`, `ffmpeg`, `ffprobe` on `PATH`

### Install

`deploy/install-native.sh` does all of the below for you (ffmpeg/ffprobe, the
venv, the fabric binary, the patterns and the frontend build). It is safe to
re-run and skips whatever is already present, so it doubles as a check that your
machine is set up correctly. To do it by hand instead:

```bash
# from the repo root
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

cd frontend && npm install && npm run build && cd ..
```

### Run

```bash
./backend/run.sh
```

Open http://localhost:5173 in your browser.

The server binds to loopback by default. Set `HOST=0.0.0.0` to reach it from
another machine, and `PORT=<n>` to move it off 5173.

> If you ever move or rename `.venv`, recreate it. The `uvicorn`/`pip` console
> scripts bake an absolute interpreter path into their shebang at install time
> and will silently keep using the old one.

### Frontend dev mode (optional)

For hot reload while editing the UI:

```bash
cd frontend && npm run dev     # http://localhost:5174
```

Vite runs on 5174 and proxies `/api` to the backend on 5173.

## Signing in

Registration is honor-system: pick any username and give an email. There is no
password and no email verification. Returning with the same username **and** the
same email gets you back into the same account; the same username with a
different email is refused. Usernames are matched case-insensitively.

Every `/api/*` route except `/api/health` and `/api/auth/register` requires the
issued token as `Authorization: Bearer <token>`.

Each user gets a fixed allowance of analyses per hour (default 30, see
`RATE_LIMIT_MAX_ANALYSES` / `RATE_LIMIT_WINDOW_SECONDS`), charged only once the
request is otherwise valid — a bad URL or a video outside the channel does not
count against it.

## API Endpoints

All paths below except `/api/health` and `/api/auth/register` require a bearer token.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/register` | Register or sign in; returns a token |
| GET | `/api/auth/me` | The signed-in user |
| POST | `/api/auth/logout` | Revoke the current token |
| POST | `/api/rumble/analyze` | Start analysis of a Rumble video |
| GET | `/api/jobs/{id}` | Poll job status |
| GET | `/api/rumble/check-result` | Look up an existing result |
| GET | `/api/history` | List past results (shared across all users) |
| GET | `/api/patterns` | List Fabric patterns |
| GET | `/api/models` | List models + the default |
| GET | `/api/health` | Health check |

## Features

- **Rumble**: Download audio → transcribe via OpenRouter → analyze with a Fabric pattern
- **Channel lock**: only videos on Marina Jacobi's channel are accepted
- **History**: Browse past results, copy transcripts, export PDFs
- **Dedup**: Re-running the same URL + pattern + model returns the cached result
- **Cheap re-runs**: the transcript is cached per video, so a new pattern on an
  already-transcribed video costs only the (small) fabric call

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | SQLite in the repo root | Set to the disk path on Render |
| `OPENROUTER_API_KEY` | from `~/.config/fabric/.env` | Checked first, so Render needs no fabric config file |
| `ALLOWED_ORIGINS` | localhost only | Comma-separated extra CORS origins |
| `HOST` / `PORT` | `127.0.0.1` / `5173` | Bind address |
| `RATE_LIMIT_MAX_ANALYSES` | `30` | Analyses per user per window |
| `RATE_LIMIT_WINDOW_SECONDS` | `3600` | Length of that window |
| `TRANSCRIPTION_CHUNK_SECONDS` | `300` | Audio chunk length |
| `TRANSCRIPTION_CONCURRENCY` | `4` | Parallel chunks |
| `FABRIC_MODEL` | `deepseek/deepseek-v4-flash` | Set in `backend/services/fabric_service.py` |

## Default model

`deepseek/deepseek-v4-flash`, set in `backend/services/fabric_service.py`. Override with the
`FABRIC_MODEL` environment variable. It is always passed to `fabric` explicitly, so Fabric's own
`DEFAULT_MODEL` from `~/.config/fabric/.env` is ignored.

## Deploying (Netlify + Render)

Both services build from a git repository, so the repo has to be pushed to
GitHub/GitLab before either can deploy.

- **Render** runs the `Dockerfile` (see `render.yaml`). The container carries
  `ffmpeg`, `ffprobe`, `yt-dlp` and the `fabric` binary, none of which Render's
  native Python runtime provides. The fabric binary is pinned by version **and**
  sha256.
- **Netlify** builds `frontend/` (see `netlify.toml`) and proxies `/api/*` to
  Render, so the browser only ever makes same-origin requests.

**Database.** SQLite, at `/var/data/cve_osint.db` on a 1GB Render disk. The disk
is what makes this safe — without it the file is wiped on every deploy and you
would lose every account and every transcript you had paid for. `DATABASE_URL`
in `render.yaml` points at it.

**Three things to set before the first deploy:**

1. Replace `REPLACE-ME.onrender.com` in `netlify.toml` with the real Render
   service URL. Until you do, every API call from the deployed site fails.
2. Set `OPENROUTER_API_KEY` in the Render dashboard.
3. Set a hard spending cap on that OpenRouter key. This is the one control that
   holds if the URL is ever shared beyond the people you intended.

If transcriptions get killed for memory, the Render instance is the cause —
Starter is 512MB. The pipeline streams audio to disk rather than buffering it,
so it may well fit, but Standard (2GB) is the fix if it does not.

## License

GPL-3.0 — see [LICENSE](LICENSE).

Copyright (C) 2026 Cowboy-Chad, the original developer.

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but **without
any warranty**; without even the implied warranty of merchantability or fitness
for a particular purpose. See the GNU General Public License for more details.

Anyone who distributes this program or a modified version of it must pass on
the same freedoms and must make the source available. That is the point of the
share-alike term: this stays open.

**Third-party content.** `fabric-patterns/` is vendored from
[danielmiessler/fabric](https://github.com/danielmiessler/fabric), which is MIT
licensed. Those patterns remain under MIT and their copyright stays with their
authors; everything else in this repository is GPL-3.0. The two are compatible
— MIT permits inclusion in a GPL work.
