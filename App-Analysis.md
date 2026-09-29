# CVE-OSINT-1 — Application Analysis

> Rewritten 2026-09-28. Reflects the state after the File/Web/YouTube removal,
> the lock to a single Rumble channel, the addition of honor-system
> authentication, and the first real deployment (Docker on Render + Netlify).
> Supersedes the earlier versions, which described a `routers.py` / `job_manager.py`
> layout and four ingestion sources.

---

## 1. What This App Is

CVE-OSINT-1 is a **multi-user OSINT analysis workbench** for a single video source: Marina
Jacobi's Rumble channel. You paste a Rumble video URL, it obtains the *text* of that video (a
transcript), and then runs a chosen
**[Fabric](https://github.com/danielmiessler/fabric) pattern** against that text with an LLM. The
output is an analysis — a summary, extracted insights, quotes, etc. — which is stored, browsable,
copyable, and exportable as PDF.

It runs locally (loopback, SQLite) and is deployed as a Docker web service on Render with a Netlify
frontend. It is **gated by an honor-system login** and **locked to one Rumble channel** — both exist
to bound spend, since every new video is a transcription someone pays for.

Despite the `CVE-` prefix in its name there is **no CVE/NVD/vulnerability-database logic anywhere in
the codebase**. The name is a project label only. The actual domain is *media content analysis*.

**What it can do, concretely:**

| Capability | Input | How text is obtained |
|---|---|---|
| Rumble analysis | Rumble URL (Marina Jacobi's channel only) | Page scrape → find media URL → download → ffmpeg-compress → LLM audio transcription |
| History | — | Browse/search past jobs; copy result or transcript; export PDF |
| Reuse | — | Automatic dedup: re-requesting the same (source, URL, pattern, model) returns the cached result instead of re-running |
| Auth | username + email | Honor-system registration that doubles as sign-in; bearer-token sessions |

**Explicit non-features:** no passwords or email verification, no multi-tenancy, no job queue, no
job delete/retry, no tests, no CI. **File upload, web-page scraping and YouTube are not part of the
app** — File and Web were removed on 2026-09-28 (see §10), and YouTube was removed with the lock to
a single Rumble channel.

---

## 2. Architecture

**One process, one origin (locally).** The FastAPI backend serves the API *and* the built React app
on http://localhost:5173. There is no separate frontend server in normal operation. In the
deployment the two are split — Netlify serves the frontend and proxies `/api/*` to Render — but the
proxy keeps them same-origin from the browser's point of view (see §9).

```
┌───────────────────────────────────────────────────────────────────────┐
│  FastAPI  (uvicorn, 127.0.0.1:5173)                                   │
│                                                                        │
│   require_auth middleware  ──▶  /api/*  ──▶  routers/ ──▶ orchestrator │
│   (401 unless bearer token)          │            │                    │
│   /*      ──▶  frontend/dist  (static, SPA fallback to index.html)     │
└───────────────┬───────────────────────────────────┬───────────────────┘
                │                                   │
                ▼                                   ▼
     fabric CLI (subprocess)                SQLite cve_osint.db  (local)
                │                           Postgres            (deployed)
                ▼                                   │
        OpenRouter API  ◀──────────────────────────┘  (audio transcription,
        (LLM inference)                                  direct HTTP)
                            ▲
                            │
                 rumble.com/v<id>  (scraped; media download + ASR)
```

**Frontend dev mode** is the one exception: `npm run dev` starts Vite on **5174**, which proxies
`/api` to the backend on 5173. Because the proxy makes it same-origin, the frontend always calls a
relative `/api` and works identically in both modes.

**Key architectural facts:**

- **Two distinct LLM call paths.** Analysis text goes through the **`fabric` CLI as a subprocess**
  (`stdin` = transcript, `stdout` = result). Audio transcription **bypasses fabric entirely** and
  calls OpenRouter's `/chat/completions` directly with base64 `input_audio` via `httpx`.
- **One ingestion source, and it is gated twice.** Only Rumble remains. A submitted URL is first
  canonicalised (`rumble_url.normalize`) and then checked against Marina Jacobi's channel
  (`is_channel_video`) before any work starts; see §7.1.
- **Auth is a blanket middleware, not per-route.** `require_auth` in `main.py` rejects every
  `/api/*` request without a valid bearer token, except `/api/health` and `/api/auth/register`. It
  is registered *before* `CORSMiddleware` on purpose: Starlette makes the last-added middleware
  outermost, and CORS has to be outermost or a 401 reaches the browser without CORS headers and
  looks like an opaque CORS failure.
- **The database backend is chosen at import time.** `DATABASE_URL` (Postgres, deployed) wins;
  otherwise SQLite at the repo root. The URL is rewritten to `postgresql+asyncpg://` and `sslmode`
  is translated to an `ssl` connect arg, since asyncpg rejects it as a query parameter. Only the
  deployment uses Postgres — locally the app always runs on SQLite.
- **All long work is fire-and-forget `asyncio.Task`s.** The POST handler creates a DB row, spawns a
  task, and returns a `job_id` immediately. There is no queue, no worker pool, no concurrency cap,
  and no persistence of the task registry — see §10.
- **The task registry (`_jobs: dict[str, asyncio.Task]`) lives in the single orchestrator.** It
  holds a strong reference so the task isn't garbage-collected. There is no way to cancel or inspect
  it.
- **Serving order matters.** The three API routers (auth, rumble, shared) are included *before* the
  static mount and the SPA catch-all, so `/api/*` always wins; the catch-all explicitly 404s `api/`
  paths so unknown API routes return JSON rather than an HTML page.
- **Loopback by default.** `run.sh` binds `127.0.0.1`. The app now has auth, but the local bind is
  still the default. `HOST=0.0.0.0` and `PORT=<n>` override; the container image sets
  `HOST=0.0.0.0` because Render puts it behind its own edge.

---

## 3. Tech Stack

### Frontend (`frontend/`)

| Technology | Installed | Role |
|---|---|---|
| React | 19.2.8 | UI, function components + hooks only |
| React DOM | 19.2.8 | Renderer |
| React Router DOM | 7.18.3 | Client-side routing (`BrowserRouter`) |
| Vite | 8.2.2 | Dev server + bundler |
| `@vitejs/plugin-react` | 6.1.1 | JSX/HMR via Oxc |
| Tailwind CSS | 4.3.3 (`@tailwindcss/vite`) | Styling — v4 style, single `@import "tailwindcss"` in `index.css`, no config file |
| lucide-react | 1.43.0 | Icon set |
| jsPDF | 4.2.1 | Client-side PDF export (dynamically imported) |
| oxlint | 1.82.0 | Linter |

No TypeScript, no state-management library, no data-fetching library, no test framework.
All state is local `useState` + a `sessionStorage` hook.

### Backend (`backend/`)

| Technology | Installed | Role |
|---|---|---|
| Python | 3.14.7 (venv at repo **root** `.venv/`) | Runtime |
| FastAPI | 0.141.1 | Web framework |
| uvicorn | 0.52.4 | ASGI server |
| SQLAlchemy | 2.0.52 | ORM (async, `DeclarativeBase`) |
| aiosqlite | 0.22.1 | Async SQLite driver (local) |
| asyncpg | — | Async Postgres driver (deployed) |
| Pydantic | 2.13.5 | Request/response schemas |
| httpx | 0.28.1 | Async HTTP (OpenRouter) |
| tiktoken | 0.14.0 | Token counting for cost estimation |
| cloudscraper | 1.2.71 | Cloudflare-bypassing scraper (Rumble page + embed) |
| requests | 2.34.2 | Sync media download (Rumble) |

`youtube-transcript-api` was dropped along with the YouTube source; `python-multipart` was dropped
from `requirements.txt` along with file upload. The image additionally `pip install`s `yt-dlp`
(metadata) and ships the `fabric` binary (see §9).

The repo-root `.venv` above is the local development runtime. The **deployment image is
`python:3.12-slim`** (Dockerfile), so the deployed interpreter differs from the local one.

### External CLI tools (must exist on `PATH`)

| Tool | Found at | Used for |
|---|---|---|
| `fabric` | `~/.local/bin/fabric` locally (v1.4.473); `/usr/local/bin/fabric` in the image | Pattern listing + LLM analysis (subprocess, stdin/stdout) |
| `yt-dlp` | `/usr/bin/yt-dlp` locally; pip-installed in the image | Video metadata extraction (`--dump-json --impersonate Chrome-133`) |
| `ffmpeg` | `/usr/bin/ffmpeg` (apt in the image) | Audio compression to mono mp3; clip extraction; HLS (`m3u8`) demux |
| `ffprobe` | `/usr/bin/ffprobe` (apt in the image) | Audio duration (drives chunk count) |

### External services

| Service | Endpoint used | Purpose |
|---|---|---|
| OpenRouter | `openrouter.ai/api/v1/chat/completions` | Audio transcription (`openai/gpt-audio-mini` by default) |
| OpenRouter | `openrouter.ai/api/v1/models` | Live per-token pricing for cost estimation |
| rumble.com | direct scrape (`cloudscraper`) | Video-page channel check, embed ID + media URL discovery |
| rumble.com | `rumble.com/c/MarinaJacobi` | The only channel whose videos are accepted |

### Fabric configuration (outside the repo)

- Patterns live in `~/.config/fabric/patterns/` — **261 patterns** resolved at runtime. The same
  261 pattern directories are **vendored in the repo under `fabric-patterns/`** and copied into the
  image at `/root/.config/fabric/patterns/`, so a container never has to download them.
- Fabric's own default is `DEFAULT_MODEL=z-ai/glm-5.3` in `~/.config/fabric/.env`.
- **The app overrides this.** `fabric_service.DEFAULT_MODEL` is **`deepseek/deepseek-v4-flash`**
  (env-overridable via `FABRIC_MODEL`), and the app *always* passes `-m <model> -V OpenRouter`
  explicitly on every call. Fabric's `.env` default model never takes effect. `cost_service`
  imports that same constant rather than duplicating it, so there is one source of truth.
- `OPENROUTER_API_KEY` is resolved by `backend/config.py`: the **environment wins**, and only if it
  is unset does it fall back to parsing `~/.config/fabric/.env`. That fallback is what makes local
  development work without exporting anything; the container gets the key as an env var instead.

---

## 4. Backend Layout

```
backend/
├── main.py                      # FastAPI app, auth middleware, CORS, routers, static mount
├── config.py                    # shared config (fabric .env path, OpenRouter key resolution)
├── database.py                  # async engine/session; DATABASE_URL → Postgres, else SQLite
├── models.py                    # User, Session, AnalysisJob ORM models
├── schemas.py                   # Pydantic request/response models
├── requirements.txt             # Python dependencies
├── run.sh                       # launch script (host/port env-overridable)
├── routers/
│   ├── auth_router.py           # /api/auth — register, me, logout
│   ├── rumble_router.py         # /api/rumble — analyze, jobs/{id}, check-result
│   └── shared_router.py         # /api — health, jobs/{id}, history, patterns, models
└── services/
    ├── auth_service.py          # register/login, token hashing, per-user rate limit
    ├── dependencies.py          # FastAPI deps: bearer token, current user
    ├── rumble_orchestrator.py   # pipeline: validate → metadata → download+ASR → fabric → cost
    ├── rumble_url.py            # Rumble URL canonicalisation + channel membership check
    ├── database_helpers.py      # CRUD, dedup lookups
    ├── fabric_service.py        # fabric CLI subprocess wrapper (+ retry/timeout); owns DEFAULT_MODEL
    ├── openrouter_service.py    # audio chunking + transcription via OpenRouter
    ├── rumble_service.py        # scrape, JSON extraction, media download, transcode
    ├── metadata_service.py      # yt-dlp metadata + Rumble HTML/JSON-LD fallback
    └── cost_service.py          # tiktoken counting + live OpenRouter pricing
```

Repo root also carries the deployment definition: `Dockerfile`, `.dockerignore`, `render.yaml`,
`netlify.toml`, and the vendored `fabric-patterns/`.

**There is now a single orchestrator.** `rumble_orchestrator.py` owns the `_jobs` dict and an
`async def run_rumble_analysis(...)` + `async def _pipeline(...)`. It runs
`update_job_status(running)` → acquire text → `run_fabric` → `estimate_cost` →
`update_job_status(completed, ...)`, with a broad `except Exception` writing `status="failed"` and
`error=str(e)` — but it keeps the transcript on failure, since transcription is the paid step.

---

## 5. Data Model

**Three tables**, created idempotently by `Base.metadata.create_all` on startup, plus a small
additive migration (`_ADDED_COLUMNS` in `database.py`) because `create_all` never `ALTER`s an
existing table — that is how `analysis_jobs.username` was added to a local DB that already held
paid-for transcripts.

`users`:

| Column | Type | Notes |
|---|---|---|
| `id` | String PK | `uuid4()` |
| `username` | String, NOT NULL | as typed by the user |
| `username_lower` | String, NOT NULL, unique, indexed | uniqueness is enforced on the lowercased form |
| `email` | String, NOT NULL | no verification; it is what proves a returning identity |
| `created_at` / `last_seen_at` | DateTime | UTC |
| `rate_window_start` | DateTime, nullable | start of the current fixed rate-limit window |
| `rate_window_count` | Integer, NOT NULL | analyses charged in that window |

`sessions`:

| Column | Type | Notes |
|---|---|---|
| `token_hash` | String PK | sha256 of the bearer token — the token itself is never stored |
| `user_id` | String FK → `users.id`, indexed | |
| `created_at` | DateTime | UTC |

`analysis_jobs`:

| Column | Type | Notes |
|---|---|---|
| `id` | String PK | `str(uuid.uuid4())` — hyphenated |
| `source` | String, NOT NULL | `rumble` (legacy rows may hold `youtube` \| `file` \| `web`) |
| `url` | Text | the source URL, stored in canonical `https://rumble.com/<id>` form |
| `file_path` | Text | legacy — written only by the removed file feature; null for all current rows |
| `pattern` | String, NOT NULL | Fabric pattern name |
| `status` | String | `pending` \| `running` \| `completed` \| `failed` |
| `transcript` | Text | the full extracted/transcribed text (base input to fabric) |
| `result` | Text | the LLM output |
| `error` | Text | failure message |
| `metadata_json` | JSON | see below |
| `username` | String, nullable, indexed | **attribution only** — history stays shared/global |
| `created_at` / `updated_at` | DateTime | UTC |

`metadata_json` is a free-form dict assembled in the orchestrator. Keys actually written today:
`title`, `channel`, `channel_url`, `channel_subscribers`, `view_count`, `upload_date`,
`upload_date_display`, `upload_date_relative`, `duration_seconds`, `duration_display`,
`webpage_url`, `timestamp`, `original_transcript_cost` (rumble only), `fabric_pattern`, `model`,
`processing_time_seconds`, `input_tokens`, `output_tokens`, `prompt_price_per_token`,
`completion_price_per_token`, `estimated_cost`, `pricing_source`.

> `transcript_source` is rendered by the frontend (`MetadataDisplay`, `AnalysisRunner`,
> `HistoryPage`) but **is never written by any current backend code**. The 2026-09 rows that carried
> `"transcript_source": "cache (from history)"` — a leftover from the deleted `job_manager.py` —
> were removed in the purge below, so no surviving row has it. Those rows also lacked `model`/cost
> keys, which is why `find_existing_result` still keeps the `stored is None` fallback.

**Current DB contents** (`cve_osint.db`, ~9.5 MB): **3 jobs, all `rumble`/`completed`**. Every
off-channel row was purged on 2026-09-28 (161 → 3); see §10.

> Cleaned 2026-09-28, in two passes. First the 3 rows stuck in `running` since 2026-09-16 and the 2
> legacy `file`/`web` rows were deleted — all five were inert (no transcript, result, or metadata),
> so nothing was lost. Then the DB was purged of every row that was not a Marina Jacobi Rumble
> video, leaving the 3 above. A pre-cleanup copy is at `cve_osint-backup-20260928.db` (matched by
> the `*.db` ignore rule).

---

## 6. API Surface

Single origin: **`http://localhost:5173`** (locally). API routes under `/api`.

**Every `/api/*` route requires an `Authorization: Bearer <token>` header**, enforced by the
`require_auth` middleware in `main.py` rather than per-route, so a new endpoint is protected by
default. The only exceptions are `GET /api/health` and `POST /api/auth/register`.

### Auth (`auth_router.py`)

| Method | Path | Notes |
|---|---|---|
| POST | `/api/auth/register` | JSON `{username, email}` → `{token, username, email}`. Public. Doubles as sign-in. |
| GET | `/api/auth/me` | `{username, email}` for the current token |
| POST | `/api/auth/logout` | Revokes the presented token |

`register` is the whole identity system: there are no passwords and no verification. A username
that already exists with the same email is the same person and is let back in; the same username
with a **different** email returns **409** so nobody can take over an identity. Usernames are
matched case-insensitively (`username_lower`), 3–32 chars of `[A-Za-z0-9._-]`. Tokens are
`secrets.token_urlsafe(32)`, returned once and stored only as a sha256 hash in `sessions`.

**Rate limit** is a fixed window kept on the user row: `RATE_LIMIT_MAX_ANALYSES` (default 30) per
`RATE_LIMIT_WINDOW_SECONDS` (default 3600), returning **429** with a retry estimate when exceeded.
It is charged **after** the URL and channel are validated, so a typo or a rejected video does not
consume quota.

### Shared (`shared_router.py`)

| Method | Path | Notes |
|---|---|---|
| GET | `/api/health` | `{"status":"ok"}` — **public**, one of the two paths the auth middleware lets through |
| GET | `/api/jobs/{job_id}` | Canonical status poll used by the frontend |
| GET | `/api/history` | `?source=&pattern=&limit=50&offset=0`. The route takes plain query params with no clamping; the bounds (1–200) only exist on the unused `HistoryFilter` schema |
| GET | `/api/patterns` | Runs `fabric --listpatterns`; descriptions always `""` |
| GET | `/api/models` | Runs `fabric --listmodels`; returns `{models: [...], default: "deepseek/deepseek-v4-flash"}` |

### Rumble (`rumble_router.py`)

| Method | Path | Body / Params |
|---|---|---|
| POST | `/api/rumble/analyze` | JSON `{url, pattern, model?}` |
| GET | `/api/rumble/jobs/{job_id}` | same handler as shared, duplicated |
| GET | `/api/rumble/check-result` | `?url=&pattern=&model=` → `{found, job?}` |

The POST returns `{"job_id": ..., "status": "pending"}`. It canonicalises the URL, then either
skips the channel check (when the transcript is already cached) or calls `is_channel_video`, then
charges the rate limit, then starts the job — see §7.1. The per-source `jobs/{id}` route is a
byte-identical copy of `shared_router`'s handler — pure duplication.

### Static

| Path | Serves |
|---|---|
| `/assets/*` | Hashed Vite bundles |
| `/<anything else>` | The matching file from `frontend/dist`, else `index.html` (SPA deep links) |
| `/api/<unknown>` | JSON `{"detail":"Not found"}` 404 |
| `/docs`, `/redoc`, `/openapi.json` | FastAPI's generated docs |

A path-traversal guard resolves each candidate with `os.path.realpath` and requires it to stay
inside `frontend/dist`.

**Dedup semantics** (`find_existing_job_id`, called at the top of `run_rumble_analysis`): if a
`completed` job exists with the same `(source, url, pattern)` **and** the stored
`metadata_json.model` equals the requested model (or is absent while the request is for the app
default), that existing job's ID is returned and **no new work is done**.

---

## 7. The Pipelines in Detail

### 7.1 Rumble, and the channel gate (the most fragile path)

The router (`rumble_router.analyze_rumble`) runs the gate **before** any work is queued:

1. `rumble_url.normalize(url)` — extract the video id (`v` plus 4–12 alphanumerics) and rewrite to
   `https://rumble.com/<video_id>`. Any shape works: `/embed/<id>`, a title slug, query params,
   `www.`, trailing slash. `normalize` returns `None` for anything unrecognisable, which is a
   **rejection, not a pass-through** — a raw string would become a fresh cache key and pay for a
   second transcription of the same audio. Storing the canonical form is what makes the transcript
   cache and the dedup key stable across Rumble's retitled URLs.
2. **Channel membership** via `is_channel_video`:
   - If the transcript is already cached (`find_existing_transcript`), the check is **skipped
     entirely** — so a scrape outage can never lock the community out of videos it has already paid
     for.
   - Otherwise `cloudscraper` fetches the video's own page and looks for `/c/MarinaJacobi` in the
     HTML. A **6-hour** in-process cache (`_verified`) means a repeat submission does not re-fetch.
   - It **fails closed**: an unfetchable page or non-200 is refused with a "try again" message,
     because every distinct video accepted is a transcription we pay for.
   - **Why a per-video page check and not a scraped allowlist:** fetching the channel *listing* and
     building an allowlist was tried first and rejected. Rumble serves degraded pages mid-scrape and
     video ids vary in length (5–6 chars after the `v`), which silently dropped roughly 148 of ~402
     videos. A short allowlist would then refuse legitimate videos, so membership is decided by one
     page fetch per *new* video, which is cheaper and cannot go stale.
3. Only then is the rate limit charged, and the job started.
4. Metadata: `yt-dlp` first; on any failure fall back to `_fetch_rumble_metadata`, a
   `cloudscraper` HTML scrape using `og:*` meta tags, `application/ld+json` `VideoObject`, and a
   series of best-effort regexes for channel/views/date.
5. `find_existing_transcript("rumble", url)` — reuse a transcript from **any** prior completed job
   for the same URL, regardless of pattern. This is the main cost saver.
6. Otherwise, transcript via `download_and_transcribe` —
   - `cloudscraper` GET the page → regex `"video":"<id>"` or `embed/<id>` → embed ID.
   - GET `https://rumble.com/embed/<id>` → locate the `"ua"` (or `"u"`) JS object via a hand-written
     brace-matching scanner (`_extract_brace_block`, string/escape aware), `json.loads` it, then
     recursively walk it (`_find_urls`, depth ≤ 10) collecting every `url` key starting with `http`.
   - Rank candidates by container preference (audio formats 0 → mp4/webm 1 → m3u8 2 → tar 3), then
     by descending bitrate; pick the best.
   - Download (with `Referer: https://rumble.com/`); `m3u8` goes through ffmpeg instead; `tar` is
     explicitly rejected.
   - Non-mp3 results are transcoded to mono/32k mp3 before transcription.
7. `transcribe_audio` (below), then `run_fabric`.
8. Stores `original_transcript_cost` in metadata — the only place transcription cost is surfaced.

### 7.2 Audio transcription
`openrouter_service.transcribe_audio`:
- `ffprobe` gets duration → `ceil(duration / CHUNK_DURATION)` ranges (default **300 s**, was 600) →
  ffmpeg extracts each into its own mono `CHUNK_BITRATE` (**24 kbps**) mp3 in a `chunks/` subdir.
  Up to `MAX_CONCURRENT_CHUNKS` (**4**) are in flight at once, guarded by an `asyncio.Semaphore`;
  `asyncio.gather` preserves submission order so the transcript stays in sequence.
- Each clip is base64-encoded and POSTed to OpenRouter `/chat/completions` with model
  `openai/gpt-audio-mini` (env `TRANSCRIPTION_MODEL`) and an `input_audio` content part, asking for
  a verbatim transcript. Retried up to `TRANSCRIPTION_MAX_RETRIES` (3) on transient statuses
  (408, 409, 429, 5xx).
- On **HTTP 413** the clip is **halved recursively** (`_transcribe_range`) down to
  `MIN_CHUNK_SECONDS` (20 s) rather than failing, then the halves are joined. This is a safety net,
  not a fix for a live bug: no 413 has occurred since chunking was introduced, and the historical
  413s came from an older code path that uploaded a single ~104 MB file.
- Chunk texts are joined with `\n\n`; per-chunk `usage.cost` is summed.
- `finally:` deletes the chunk files and the directory. Chunking is a fixed grid, so words can be
  split at boundaries; there is no overlap or stitching logic.

### 7.3 Fabric invocation (`fabric_service.run_fabric`)
- Command: `fabric -p <pattern> -m <model> -V <vendor>`, transcript piped to stdin.
- Timeout: `FABRIC_TIMEOUT` (default **600 s**), enforced via `asyncio.wait_for`.
- Retry: up to `MAX_RETRIES` (3) attempts, but **only** when the exit code is 1 *and* `"429"`
  appears in stderr — retried with exponential backoff (`2 s, 4 s`). Any other non-zero exit raises
  immediately.

### 7.4 Cost estimation (`cost_service`)
- Pricing pulled live from OpenRouter `/models` and cached module-globally for 300 s.
- Token counts via `tiktoken`; `_get_model_for_tokenizer` maps everything to `cl100k_base`
  (the branching is dead code — every path returns the same value) with a `len(text)//4` fallback.
- Cost = `in_tokens * prompt_price + out_tokens * completion_price`, rounded to 6 dp.
- **Input tokens count the transcript, not the assembled fabric prompt** (the pattern body itself is
  never measured), so this is a lower bound. It also does not include the transcription cost —
  which is tracked separately as `original_transcript_cost`.

---

## 8. Frontend Structure

```
frontend/src/
├── main.jsx                     # StrictMode > BrowserRouter > App
├── App.jsx                      # auth gate; 2 routes + catch-all redirect
├── index.css                    # @import "tailwindcss"  (only global style)
├── App.css                      # ← unused Vite template leftover
├── api/client.js                # all fetch calls; token storage; 401 → auth:expired
├── hooks/usePersistedState.js   # useState mirroring into sessionStorage
├── components/
│   ├── Layout.jsx               # nav bar (Rumble / History), user name + sign-out, dark theme
│   ├── PatternSelector.jsx      # searchable pattern combobox
│   ├── AnalysisRunner.jsx       # 2 s polling loop + ResultDisplay
│   └── MetadataDisplay.jsx      # metadata table renderer (modal body)
└── pages/
    ├── LoginPage.jsx            # honor-system register/sign-in form
    ├── RumbleAnalysisPage.jsx
    └── HistoryPage.jsx
```

**Auth gating lives in `App.jsx`.** If there is no token it renders `<LoginPage>` instead of the
router, and `getMe()` validates a stored token on load (showing "Loading..." only when a token
exists). `client.js` keeps the token in `localStorage` under `cve_osint_token`, attaches
`Authorization: Bearer` to every request, and on any **401** clears the token and dispatches a
window event `auth:expired`, which `App` listens for — so an expired session lands on the login
form instead of a wall of failures.

**Routes:** `/` → redirect to `/analysis/rumble`; `/analysis/rumble`; `/history`;
`*` → redirect to `/analysis/rumble`. There is no YouTube route any more.

**`PatternSelector` behaviour** (the most intricate component):
- Loads all patterns once via `GET /api/patterns`, filters client-side by substring.
- Dual state: `search` (the text) and `confirmed` (the accepted pattern). The dropdown is visible
  **only while unconfirmed** — `showDropdown = !confirmed`.
- Confirmation is via **double-click** (two clicks on the same name within 400 ms) or **Enter** on
  the highlighted item. A single click only sets the pattern and *clears* confirmation.
- Arrow keys move a highlight through the filtered list with wraparound; `scrollIntoView` keeps it
  visible.
- Once confirmed, **Enter re-submits** the analysis (`onEnter`), which is how the input doubles as
  a form field and a submit trigger.
- Confirmation also fires `onConfirm` → `handleAutoCheck` → `checkRumbleResult`, which either loads
  a cached job into the runner or shows "No prior analysis found".
- `search` and `confirmed` are persisted to `sessionStorage` under `storageKey` (`rumble`), so tab
  state survives reloads.

**Persisted state keys:** `rumble-url`, `rumble-pattern`, `analysis-model`,
`pattern-search-rumble`, `pattern-confirmed-rumble`. All `sessionStorage`, so they are per-tab and
cleared when the tab closes.

**`AnalysisRunner`** polls `GET /api/jobs/{id}` every 2 s until `completed`/`failed`, with a
`cancelled` flag guarding against unmount races. `ResultDisplay` renders metadata lines + result as
one preformatted block, offers Copy (whole thing), Export PDF (jsPDF, dynamic import, filename
derived from the video title with filesystem-unsafe chars replaced), and a collapsible transcript.

**`HistoryPage`** fetches `GET /api/history` with no parameters (default limit 50, **no pagination
UI** — older jobs are unreachable from the UI) and does client-side full-text search across URL,
file path, pattern, source, status, username, error, result, transcript, and metadata
title/channel/URL. There is **no source filter** any more (there is only one source); the `source`
name is still shown per row. Each row expands inline to show result + transcript with copy buttons
and an "Open Original" link; a "Show Meta" button opens a modal (`Escape` closes it) rendering
`MetadataDisplay`.

**Metadata line rendering is triplicated** — the same 14-line assembly block appears in
`AnalysisRunner.jsx` and twice in `HistoryPage.jsx`, with a table version in `MetadataDisplay.jsx`.

**Dead assets:** `src/App.css`, `src/assets/hero.png`, `src/assets/react.svg`, `src/assets/vite.svg`,
and `public/icons.svg` are all unreferenced (Vite template leftovers).

---

## 9. Configuration & Runtime

### Ports & launch
- **One command:** `./backend/run.sh` → uvicorn on **127.0.0.1:5173**, serving the API and
  `frontend/dist`. Override with `HOST` / `PORT`.
- `run.sh` `cd`s to the repo root, sources `.venv` **there**, and **stays** there — `backend` is
  a package, so the repo root must be the working directory for `backend.main` to be importable.
  It warns if `frontend/dist/index.html` is missing and exits if `.venv` is absent.
- `run.sh` invokes `python3 -m uvicorn`, not the `uvicorn` console script — see issue 20 below.
- **`.venv` lives at the repo root.** Create it there, and do not move or rename the repo
  afterwards without recreating it (issue 20).
- **Frontend dev mode:** `npm run dev` → Vite on **5174** (strictPort), proxying `/api` to 5173.
- `frontend/dist/` is gitignored, so a fresh clone **must run `npm run build`** before `run.sh`
  serves anything at `/`.

### Environment variables read by the backend
| Variable | Default | Where |
|---|---|---|
| `DATABASE_URL` | *(unset → SQLite at repo root)* | `database.py` |
| `FABRIC_MODEL` | `deepseek/deepseek-v4-flash` | `fabric_service` (single source of truth) |
| `FABRIC_VENDOR` | `OpenRouter` | `fabric_service` |
| `FABRIC_TIMEOUT` | `600` | `fabric_service` |
| `FABRIC_MAX_RETRIES` | `3` | `fabric_service` |
| `FABRIC_RETRY_BASE_DELAY` | `2.0` | `fabric_service` |
| `TRANSCRIPTION_MODEL` | `openai/gpt-audio-mini` | `openrouter_service` |
| `TRANSCRIPTION_CHUNK_SECONDS` | `300` | `openrouter_service` |
| `TRANSCRIPTION_CHUNK_BITRATE` | `24k` | `openrouter_service` |
| `TRANSCRIPTION_MIN_CHUNK_SECONDS` | `20` | `openrouter_service` |
| `TRANSCRIPTION_CONCURRENCY` | `4` | `openrouter_service` |
| `TRANSCRIPTION_MAX_RETRIES` | `3` | `openrouter_service` |
| `OPENROUTER_API_BASE_URL` | `https://openrouter.ai/api/v1` | `openrouter_service` |
| `OPENROUTER_API_KEY` | *(unset)* | `config.py` — env first, else `~/.config/fabric/.env` |
| `ALLOWED_ORIGINS` | *(empty)* | `main.py` — extra CORS origins, comma-separated |
| `RATE_LIMIT_MAX_ANALYSES` | `30` | `auth_service` |
| `RATE_LIMIT_WINDOW_SECONDS` | `3600` | `auth_service` |
| `HOST` / `PORT` | `127.0.0.1` / `5173` | `run.sh` |
| `VITE_API_BASE` (frontend) | `/api` | `api/client.js` |

`OPENROUTER_API_KEY` **is** read from the environment first; the `~/.config/fabric/.env` fallback
exists only so local development works without exporting anything. Local CORS always allows
`localhost`/`127.0.0.1` on any port via `allow_origin_regex`; anything else must be listed in
`ALLOWED_ORIGINS`.

### Deployment (Docker on Render + Netlify)

- **`Dockerfile`** — `python:3.12-slim` with apt `ffmpeg`, `ca-certificates`, `curl`; the `fabric`
  binary is downloaded from GitHub releases (v1.4.473) and **verified against a pinned sha256**
  (`c74b4515…27076`) before being installed, so an unverified download cannot become arbitrary code
  execution in the deployment. It `pip install`s `backend/requirements.txt` plus `yt-dlp`, and
  copies the vendored `fabric-patterns/` to `/root/.config/fabric/patterns/` so a restart never
  depends on GitHub. It listens on `${PORT:-8000}` with `--reload` off.
- **The frontend is deliberately not built into the image.** Netlify builds it and proxies `/api/*`,
  so shipping it too would mean committing build output — Render builds from the repo.
- **`render.yaml`** — blueprint for a Docker web service plus a Postgres database. Health check is
  `/api/health`, which must stay public (a health check pointed at an authenticated route would 401
  and Render would mark a healthy service down). `DATABASE_URL` is injected from the database;
  `OPENROUTER_API_KEY` is a `sync: false` var set in the dashboard. Both the service and the
  database are pinned to `oregon`, because they talk over Render's private network and a
  cross-region pair would add latency to every query. Plans are spelled `0.5c-512mb` and
  `0.1c-256mb` — Render renamed instance types to compute plans in August 2026 and no longer
  accepts `starter`.
- **`netlify.toml`** — builds `frontend` with `NODE_VERSION = 22`, proxies `/api/*` to the Render
  host with `status = 200, force = true` (so the browser only ever talks to the Netlify origin and
  there is no CORS preflight), and finishes with the SPA fallback `/*` → `/index.html`, which must
  stay last. **The Render host is a `REPLACE-ME.onrender.com` placeholder and must be filled in.**
- **`.dockerignore`** keeps `.venv/`, `*.db`, `.git/`, `.claude/` and `.env` out of the image (the
  local DB holds paid-for transcripts) but deliberately does **not** exclude `*.md`, since every
  fabric pattern is a directory containing a `system.md`.

---

## 10. Known Issues and Gaps

Items marked ✅ were fixed on 2026-09-28.

**Security**
1. ✅ **Live OpenRouter API key in plaintext in `.claude/settings.local.json`.** That file is now
   gitignored (`.claude/`). The same key is still readable at `~/.config/fabric/.env`, which is
   unavoidable — the backend needs it there. **The key itself was not rotated**, and it remains
   worth rotating since it sat in a packageable location.
2. ✅ **Backend bound `0.0.0.0` with no auth.** `run.sh` now defaults to `127.0.0.1`; CORS was
   widened to any localhost origin so the dev server on 5174 works.
3. ✅ **Unrestricted file upload** — removed with the File feature.
4. ✅ **SSRF via `/api/web/scrape`** — removed with the Web feature.
5. **Auth is honor-system, not a security boundary.** There are no passwords or email verification:
   a username plus its matching email is enough to get a token. It gates a private community of
   volunteers, and the expensive resource behind it is the Rumble channel lock, so the rate limit is
   a runaway-loop guard rather than a cost control. The blanket middleware protects every `/api/*`
   route except `/api/health` and `/api/auth/register`, but it does not make the app safe to expose
   to the public internet.

**Correctness / reliability**

6. **`running` is a terminal state on restart.** Tasks are in-process `asyncio.Task`s; if uvicorn
   reloads or crashes mid-analysis the row is never updated. This is not hypothetical — it
   produced 3 Rumble jobs stuck in `running` from 2026-09-16, which had to be deleted by hand on
   2026-09-28. The underlying flaw is unchanged: **every restart can orphan new rows.** Since
   `--reload` is on by default locally, editing any backend file during a running analysis is enough
   to trigger it.
7. **No concurrency control.** Every request spawns an unbounded task; each Rumble job spawns its
   own `fabric` process (up to 600 s) plus ffmpeg. N parallel submissions = N LLM calls. The
   per-user rate limit bounds each *person*, not the process.
8. **Broad exception handling hides causes.** The orchestrator wraps metadata fetch in
   `except (asyncio.TimeoutError, Exception): meta = {}` — `asyncio.TimeoutError` is redundant since
   Python 3.11 and the catch is total. `_fetch_rumble_metadata` likewise returns `{}` on any error.
   The `error` column is the only diagnostic, and it's just `str(e)`.
9. **Fabric timeout leaks the process.** On `asyncio.TimeoutError` the code calls `proc.kill()`
   and then raises — it never awaits the process, so the child can linger as a zombie.
10. **Rumble URL discovery is regex/JSON-shape archaeology** against an undocumented page structure
    (`"ua"`, `"u"`, `"video":"<id>"`, brace-matching). It will silently break whenever Rumble
    changes its embed payload, and the channel check depends on the same scrape succeeding (it fails
    closed, so an outage blocks new videos rather than spending money).
11. ✅ **`find_existing_transcript` no longer requires `status='completed'`.** It now matches on
    `transcript IS NOT NULL` with no status filter, and the orchestrator saves the transcript on the
    failure path too — so a run that fails at the cheap fabric step no longer discards the
    transcription it already paid for.
12. **`estimate_cost` undercounts input tokens** (transcript only, not the pattern prompt) and
    ignores transcription cost entirely. The latter is tracked separately as
    `original_transcript_cost` on Rumble.
13. **Migrations are still mostly manual.** `create_all` only creates, so `_ADDED_COLUMNS` in
    `database.py` hand-runs the `ALTER TABLE` statements needed to add a column to an existing
    table. That covers additive columns only — a type change, a drop, or a backfill still needs
    manual work on both SQLite and Postgres. `file_path` remains a dead column, as does the `source`
    column's ability to hold `file`/`web`/`youtube`.
14. **`App.css` and `assets/` are dead**, and `public/icons.svg` is unreferenced. `frontend/dist/`
    is gitignored and must be rebuilt after any UI change.
15. **No tests and no CI** anywhere in the repo.

**Maintainability**

16. **One orchestrator, but still duplicated handlers.** The Rumble router's `jobs/{id}` handler is
    a byte-identical copy of `shared_router`'s, and the metadata-formatting block is repeated in
    `AnalysisRunner.jsx`, `HistoryPage.jsx` (twice) and `MetadataDisplay.jsx`.
17. ✅ **The row→schema mapping was deduplicated.** `get_job` and `list_jobs` now both call
    `database_helpers._job_to_response` instead of re-implementing it inline. That helper is still
    declared `async` despite performing no I/O, which is now pointless rather than harmful.
18. Imports are placed inside function bodies in several spots (`database_helpers`, `cost_service`,
    `metadata_service`, `shared_router`).
19. `schemas.PatternInfo.description` is always empty because `list_patterns` never populates it,
    yet the frontend has rendering paths for it.

**Tooling**

20. ✅ **A relocated venv silently runs the wrong interpreter and the wrong packages.** Console
    scripts in `.venv/bin` (`uvicorn`, `pip`, `fastapi`, …) get an **absolute** interpreter path
    baked into their shebang at install time. This repo was previously checked out at
    `/home/cowboy/000/cve-osint-1`, and `.venv` was moved here with it — so all nine scripts still
    began `#!/home/cowboy/000/cve-osint-1/.venv/bin/python3` and launched the *old* venv, whose
    `site-packages` happened to satisfy the imports. Nothing failed visibly; the app simply ran
    the previous checkout's dependency set, which also meant `pip install -r
    backend/requirements.txt` had no effect. Shebangs repaired and `run.sh` now uses `python3 -m
    uvicorn`, which cannot go stale. **The durable fix for any moved venv is to delete and
    recreate it:**

    ```bash
    rm -rf .venv && python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt
    ```

    This is worth doing for `cve-marina-all-1` if it and `cve-osint-1` are both still live — the
    two venvs are independent copies and will drift.

**Data & operations**

21. **The local DB was purged of off-channel rows, and the API key still has no spending cap.**
    `cve_osint.db` went from 161 jobs to 3 — everything that was not a Marina Jacobi Rumble video
    was deleted. Separately, the OpenRouter API key in `~/.config/fabric/.env` has **still not been
    rotated** (see issue 1), and it is the key that pays for every transcription. **Set a hard
    spending cap on that key at OpenRouter.** The channel lock bounds the number of distinct
    transcriptions but does not bound retries, fabric calls, or a bad deploy — a cap is the only
    thing that actually stops the bill.

---

## 11. Quick Reference

**Run it**
```bash
# one-time
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cd frontend && npm install && npm run build && cd ..

# every time
./backend/run.sh                 # → http://localhost:5173 serves UI + API
```

**Dev mode with hot reload**
```bash
./backend/run.sh                 # backend on 5173
cd frontend && npm run dev       # UI on 5174, /api proxied to 5173
```

**Smoke test**
```bash
# /api/health is public; everything else needs a token.
curl localhost:5173/api/health

# register (or sign back in) and keep the token
TOKEN=$(curl -s localhost:5173/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"tester","email":"tester@example.com"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')

curl localhost:5173/api/models -H "Authorization: Bearer $TOKEN" | head -c 200
curl localhost:5173/api/history -H "Authorization: Bearer $TOKEN"
```

**Inspect the database**
```bash
sqlite3 cve_osint.db \
  "select source,status,count(*) from analysis_jobs group by 1,2;"
```

**Glossary**
- **Fabric** — CLI tool that holds a library of reusable LLM prompt templates ("patterns") and
  pipes input through them to a provider.
- **Pattern** — a named prompt template (e.g. `summarize`, `extract_wisdom`). 261 are installed,
  and vendored in `fabric-patterns/`.
- **Transcript** — the text the pattern runs on. For video it is ASR output.
- **Job** — one `(source, url, pattern, model)` analysis run, tracked by a UUID and a row in
  `analysis_jobs`.
- **Dedup** — returning a prior completed job instead of re-running an identical request.
- **Channel gate** — the per-video check that a Rumble URL belongs to Marina Jacobi's channel;
  fails closed, skipped when the transcript is already cached.
