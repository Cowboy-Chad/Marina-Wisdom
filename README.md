# CVE-OSINT-1

OSINT analysis app leveraging [Fabric](https://github.com/danielmiessler/fabric) AI patterns for automated analysis of multimedia content.

## Architecture

```
React (Vite)  ←→  FastAPI (Python)  ←→  fabric CLI  ←→  OpenRouter API
                                    ↕
                               SQLite DB
```

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- [Fabric CLI](https://github.com/danielmiessler/fabric) installed and configured
- OpenRouter API key (in `~/.config/fabric/.env`)

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./run.sh
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/analyze` | Start analysis (YouTube, Rumble, Web) |
| POST | `/api/analyze/file` | Upload file for analysis |
| GET | `/api/jobs/{id}` | Poll job status |
| GET | `/api/history` | List past results |
| GET | `/api/patterns` | List Fabric patterns |
| GET | `/api/health` | Health check |

## Features

- **YouTube**: Fetch transcript → analyze with Fabric pattern
- **Rumble**: Download audio → transcribe via OpenRouter → analyze
- **File Upload**: Upload audio/video → transcribe → analyze
- **Web Scraping**: Scrape URL → analyze with Fabric pattern
- **History**: Browse past results, copy transcripts, export PDFs