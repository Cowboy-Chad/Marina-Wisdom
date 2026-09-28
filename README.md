# CVE-OSINT-1

OSINT analysis app leveraging [Fabric](https://github.com/danielmiessler/fabric) AI patterns for automated analysis of multimedia content.

## Architecture

```
Browser ──▶ FastAPI (Python, :5173) ──▶ fabric CLI ──▶ OpenRouter API
                 │         │
                 │         └── serves the built React app
                 └── SQLite DB
```

The backend serves both the API and the built frontend on **one origin** —
http://localhost:5173. There is nothing else to start.

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- [Fabric CLI](https://github.com/danielmiessler/fabric) installed and configured
- OpenRouter API key (in `~/.config/fabric/.env`)
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

The server binds to loopback by default because the app has no authentication.
Set `HOST=0.0.0.0` if you need to reach it from another machine, and
`PORT=<n>` to move it off 5173.

### Frontend dev mode (optional)

For hot reload while editing the UI:

```bash
cd frontend && npm run dev     # http://localhost:5174
```

Vite runs on 5174 and proxies `/api` to the backend on 5173.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/youtube/analyze` | Start analysis of a YouTube video |
| POST | `/api/rumble/analyze` | Start analysis of a Rumble video |
| GET | `/api/jobs/{id}` | Poll job status |
| GET | `/api/{youtube,rumble}/check-result` | Look up an existing result |
| GET | `/api/history` | List past results |
| GET | `/api/patterns` | List Fabric patterns |
| GET | `/api/models` | List models + the default |
| GET | `/api/health` | Health check |

## Features

- **YouTube**: Fetch transcript → analyze with Fabric pattern
- **Rumble**: Download audio → transcribe via OpenRouter → analyze
- **History**: Browse past results, copy transcripts, export PDFs
- **Dedup**: Re-running the same URL + pattern + model returns the cached result

## Default model

`deepseek/deepseek-v4-flash`, set in `backend/services/fabric_service.py`. Override with the
`FABRIC_MODEL` environment variable. It is always passed to `fabric` explicitly, so Fabric's own
`DEFAULT_MODEL` from `~/.config/fabric/.env` is ignored.
