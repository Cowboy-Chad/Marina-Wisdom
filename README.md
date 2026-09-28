# CVE-OSINT-1

OSINT analysis app leveraging [Fabric](https://github.com/danielmiessler/fabric) AI patterns for automated analysis of multimedia content.

It analyzes videos from **one channel only** — Marina Jacobi's official Rumble
channel, [rumble.com/c/MarinaJacobi](https://rumble.com/c/MarinaJacobi). There is
no open URL or channel search. Each distinct video is transcribed once and the
transcript is shared and reused, which is what keeps the running cost bounded.

## Architecture

```
Browser ──▶ FastAPI ──▶ fabric CLI ──▶ OpenRouter API
                │  │
                │  └── yt-dlp / ffmpeg (audio) ──▶ OpenRouter (transcription)
                └── Postgres (Render) or SQLite (local)
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
| `DATABASE_URL` | SQLite in the repo root | Postgres URL in deployment |
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

## Deploying

- **Render** runs the `Dockerfile` (see `render.yaml`). A container is required
  rather than the native Python runtime because the app shells out to `fabric`,
  `yt-dlp` and `ffmpeg`. The fabric binary is pinned by version **and** sha256.
- **Netlify** builds `frontend/` (see `netlify.toml`) and proxies `/api/*` to Render.

**Before the first deploy**, replace `REPLACE-ME.onrender.com` in `netlify.toml`
with the real Render service URL, and set `OPENROUTER_API_KEY` on Render. Until
the hostname is replaced, every API call from the deployed site fails.
