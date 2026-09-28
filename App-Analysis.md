# CVE-OSINT-1 — Application Analysis

> Rewritten 2026-09-28. Reflects the state after the File/Web removal and the
> move to a single origin on port 5173.
> Supersedes the earlier versions, which described a `routers.py` / `job_manager.py`
> layout and four ingestion sources.

---

## 1. What This App Is

CVE-OSINT-1 is a **single-user, locally-run OSINT analysis workbench**. You point it at a video,
it obtains the *text* of that video (a transcript), and then runs a chosen
**[Fabric](https://github.com/danielmiessler/fabric) pattern** against that text with an LLM. The
output is an analysis — a summary, extracted insights, quotes, etc. — which is stored, browsable,
copyable, and exportable as PDF.

Despite the `CVE-` prefix in its name there is **no CVE/NVD/vulnerability-database logic anywhere in
the codebase**. The name is a project label only. The actual domain is *media content analysis*.

**What it can do, concretely:**

| Capability | Input | How text is obtained |
|---|---|---|
| YouTube analysis | YouTube URL | Existing subtitles via `youtube-transcript-api` (no audio download) |
| Rumble analysis | Rumble URL | Page scrape → find media URL → download → ffmpeg-compress → LLM audio transcription |
| History | — | Browse/search/filter past jobs; copy result or transcript; export PDF |
| Reuse | — | Automatic dedup: re-requesting the same (source, URL, pattern, model) returns the cached result instead of re-running |

**Explicit non-features:** no authentication, no user accounts, no multi-tenancy, no job queue, no
rate limiting, no job delete/retry, no tests, no CI. **File upload and web-page scraping are not
part of the app** — both were removed on 2026-09-28 (see §10).

---

## 2. Architecture

**One process, one origin.** The FastAPI backend serves the API *and* the built React app on
http://localhost:5173. There is no separate frontend server in normal operation.

```
┌───────────────────────────────────────────────────────────────────────┐
│  FastAPI  (uvicorn, 127.0.0.1:5173)                                   │
│                                                                        │
│   /api/*  ──▶  routers/ ──▶ orchestrators/ ──▶ services/               │
│   /*      ──▶  frontend/dist  (static, SPA fallback to index.html)     │
└───────────────┬───────────────────────────────────┬───────────────────┘
                │                                   │
                ▼                                   ▼
     fabric CLI (subprocess)                SQLite cve_osint.db
                │                            (aiosqlite, async)
                ▼                                   │
        OpenRouter API  ◀──────────────────────────┘  (audio transcription,
        (LLM inference)                                  direct HTTP)
                            ▲
                            │
                 rumble.com / YouTube (scraped, captions)
```

**Frontend dev mode** is the one exception: `npm run dev` starts Vite on **5174**, which proxies
`/api` to the backend on 5173. Because the proxy makes it same-origin, the frontend always calls a
relative `/api` and works identically in both modes.

**Key architectural facts:**

- **Two distinct LLM call paths.** Analysis text goes through the **`fabric` CLI as a subprocess**
  (`stdin` = transcript, `stdout` = result). Audio transcription **bypasses fabric entirely** and
  calls OpenRouter's `/chat/completions` directly with base64 `input_audio` via `httpx`.
- **All long work is fire-and-forget `asyncio.Task`s.** The POST handler creates a DB row, spawns a
  task, and returns a `job_id` immediately. There is no queue, no worker pool, no concurrency cap,
  and no persistence of the task registry — see §10.
- **The task registry (`_jobs: dict[str, asyncio.Task]`) exists separately in each orchestrator.**
  It holds a strong reference so the task isn't garbage-collected. There is no way to cancel or
  inspect it.
- **Serving order matters.** The two API routers are included *before* the static mount and the SPA
  catch-all, so `/api/*` always wins; the catch-all explicitly 404s `api/` paths so unknown API
  routes return JSON rather than an HTML page.
- **Loopback by default.** `run.sh` binds `127.0.0.1` because the app has no auth. `HOST=0.0.0.0`
  and `PORT=<n>` override.

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
| aiosqlite | 0.22.1 | Async SQLite driver |
| Pydantic | 2.13.5 | Request/response schemas |
| httpx | 0.28.1 | Async HTTP (OpenRouter) |
| tiktoken | 0.14.0 | Token counting for cost estimation |
| youtube-transcript-api | 1.2.4 | YouTube caption fetching |
| cloudscraper | 1.2.71 | Cloudflare-bypassing scraper (Rumble) |
| requests | 2.34.2 | Sync media download (Rumble) |

`python-multipart` was dropped from `requirements.txt` along with file upload.

### External CLI tools (must exist on `PATH`)

| Tool | Found at | Used for |
|---|---|---|
| `fabric` | `~/.local/bin/fabric` (v1.4.473) | Pattern listing + LLM analysis (subprocess, stdin/stdout) |
| `yt-dlp` | `/usr/bin/yt-dlp` | Video metadata extraction (`--dump-json --impersonate Chrome-133`) |
| `ffmpeg` | `/usr/bin/ffmpeg` | Audio compression to mono 32k mp3; HLS (`m3u8`) demux |
| `ffprobe` | `/usr/bin/ffprobe` | Audio duration (drives chunk count) |

### External services

| Service | Endpoint used | Purpose |
|---|---|---|
| OpenRouter | `openrouter.ai/api/v1/chat/completions` | Audio transcription (`openai/gpt-audio-mini` by default) |
| OpenRouter | `openrouter.ai/api/v1/models` | Live per-token pricing for cost estimation |
| rumble.com | direct scrape | Embed ID + media URL discovery |

### Fabric configuration (outside the repo)

- Patterns live in `~/.config/fabric/patterns/` — **261 patterns** resolved at runtime.
- Fabric's own default is `DEFAULT_MODEL=z-ai/glm-5.3` in `~/.config/fabric/.env`.
- **The app overrides this.** `fabric_service.DEFAULT_MODEL` is **`deepseek/deepseek-v4-flash`**
  (env-overridable via `FABRIC_MODEL`), and the app *always* passes `-m <model> -V OpenRouter`
  explicitly on every call. Fabric's `.env` default model never takes effect. `cost_service`
  imports that same constant rather than duplicating it, so there is one source of truth.
- `OPENROUTER_API_KEY` is read by the backend **by manually parsing `~/.config/fabric/.env`** in
  `openrouter_service.py`, at import time.

---

## 4. Backend Layout

```
backend/
├── main.py                      # FastAPI app, CORS, lifespan(init_db), routers, static mount
├── database.py                  # async engine/session; DB at <repo root>/cve_osint.db
├── models.py                    # AnalysisJob ORM model
├── schemas.py                   # Pydantic request/response models
├── requirements.txt             # Python dependencies
├── run.sh                       # launch script (host/port env-overridable)
├── routers/
│   ├── youtube_router.py        # /api/youtube — analyze, jobs/{id}, check-result
│   ├── rumble_router.py         # /api/rumble  — analyze, jobs/{id}, check-result
│   └── shared_router.py         # /api — health, jobs/{id}, history, patterns, models
└── services/
    ├── youtube_orchestrator.py  # pipeline: validate → metadata → transcript → fabric → cost
    ├── rumble_orchestrator.py   # pipeline: validate → metadata → download+ASR → fabric → cost
    ├── database_helpers.py      # CRUD, dedup lookups
    ├── fabric_service.py        # fabric CLI subprocess wrapper (+ retry/timeout); owns DEFAULT_MODEL
    ├── openrouter_service.py    # audio chunking + transcription via OpenRouter
    ├── youtube_service.py       # video-ID regex + transcript fetch
    ├── rumble_service.py        # scrape, JSON extraction, media download, transcode
    └── metadata_service.py      # yt-dlp metadata + Rumble HTML/JSON-LD fallback
    └── cost_service.py          # tiktoken counting + live OpenRouter pricing
```

**The two orchestrators are near-identical.** Each defines its own `_jobs` dict and an
`async def run_X_analysis(...)` + `async def _pipeline(...)`. Only the text-acquisition step
differs (`fetch_transcript` vs `download_and_transcribe`). Both share the same shape:
`update_job_status(running)` → acquire text → `run_fabric` → `estimate_cost` →
`update_job_status(completed, ...)`, with a broad `except Exception` writing `status="failed"` and
`error=str(e)`. This remains the clearest refactoring target in the codebase.

---

## 5. Data Model

Single table, created idempotently by `Base.metadata.create_all` on startup (no migrations —
schema changes require manual DB work).

`analysis_jobs`:

| Column | Type | Notes |
|---|---|---|
| `id` | String PK | `uuid4()` hex |
| `source` | String, NOT NULL | `youtube` \| `rumble` (legacy rows may hold `file` \| `web`) |
| `url` | Text | the source URL |
| `file_path` | Text | legacy — written only by the removed file feature; null for all current rows |
| `pattern` | String, NOT NULL | Fabric pattern name |
| `status` | String | `pending` \| `running` \| `completed` \| `failed` |
| `transcript` | Text | the full extracted/transcribed text (base input to fabric) |
| `result` | Text | the LLM output |
| `error` | Text | failure message |
| `metadata_json` | JSON | see below |
| `created_at` / `updated_at` | DateTime | UTC |

`metadata_json` is a free-form dict assembled in the orchestrator. Keys actually written today:
`title`, `channel`, `channel_url`, `channel_subscribers`, `view_count`, `upload_date`,
`upload_date_display`, `upload_date_relative`, `duration_seconds`, `duration_display`,
`webpage_url`, `timestamp`, `original_transcript_cost` (rumble only), `fabric_pattern`, `model`,
`processing_time_seconds`, `input_tokens`, `output_tokens`, `prompt_price_per_token`,
`completion_price_per_token`, `estimated_cost`, `pricing_source`.

> `transcript_source` is rendered by the frontend (`MetadataDisplay`, `AnalysisRunner`,
> `HistoryPage`) but **is never written by any current backend code**. Rows in the live DB from
> 2026-09 carry `"transcript_source": "cache (from history)"` — a leftover from the deleted
> `job_manager.py`. Those same rows also lack `model`/cost keys, which is why
> `find_existing_result` has the `stored is None` fallback.

**Current DB contents** (`cve_osint.db`, ~9.5 MB): 166 jobs —
118 youtube/completed, 14 youtube/failed, 15 rumble/completed, 14 rumble/failed, **3 rumble stuck
in `running`**, 1 file/failed, 1 web/failed. Rows with `source` of `file` or `web` are historical
only. Most-used patterns: `summarize` (64), `extract_wisdom` (27), `extract_insights` (26),
`youtube_summary` (18).

---

## 6. API Surface

Single origin: **`http://localhost:5173`**. API routes under `/api`. No auth on any route.

### Shared (`shared_router.py`)

| Method | Path | Notes |
|---|---|---|
| GET | `/api/health` | `{"status":"ok"}` |
| GET | `/api/jobs/{job_id}` | Canonical status poll used by the frontend |
| GET | `/api/history` | `?source=&pattern=&limit=50&offset=0` (limit 1–200) |
| GET | `/api/patterns` | Runs `fabric --listpatterns`; descriptions always `""` |
| GET | `/api/models` | Runs `fabric --listmodels`; returns `{models: [...], default: "deepseek/deepseek-v4-flash"}` |

### Per-source

| Method | Path | Body / Params |
|---|---|---|
| POST | `/api/youtube/analyze` | JSON `{url, pattern, model?}` |
| POST | `/api/rumble/analyze` | JSON `{url, pattern, model?}` |
| GET | `/api/{youtube,rumble}/jobs/{job_id}` | same handler as shared, duplicated |
| GET | `/api/{youtube,rumble}/check-result` | `?url=&pattern=&model=` → `{found, job?}` |

Both POSTs return `{"job_id": ..., "status": "pending"}`. The per-source `jobs/{id}` routes are
byte-identical copies of each other and of `shared_router`'s handler; likewise the two
`check-result` routes are identical — pure duplication.

### Static

| Path | Serves |
|---|---|
| `/assets/*` | Hashed Vite bundles |
| `/<anything else>` | The matching file from `frontend/dist`, else `index.html` (SPA deep links) |
| `/api/<unknown>` | JSON `{"detail":"Not found"}` 404 |
| `/docs`, `/redoc`, `/openapi.json` | FastAPI's generated docs |

A path-traversal guard resolves each candidate with `os.path.realpath` and requires it to stay
inside `frontend/dist`.

**Dedup semantics** (`find_existing_job_id`, called at the top of `run_*_analysis`): if a
`completed` job exists with the same `(source, url, pattern)` **and** the stored
`metadata_json.model` equals the requested model (or is absent while the request is for the app
default), that existing job's ID is returned and **no new work is done**.

---

## 7. The Pipelines in Detail

### 7.1 YouTube
1. Validate URL matches `youtube\.com|youtu\.be`.
2. `fetch_video_metadata` (10 s cap) — `yt-dlp --dump-json --impersonate Chrome-133`. Failure is
   swallowed to `{}`.
3. `find_existing_transcript("youtube", url)` — reuse a transcript from **any** prior completed job
   for the same URL, regardless of pattern. This is the main cost saver.
4. Otherwise `youtube-transcript-api` fetches captions. Video ID extracted via three regexes
   (`v=|/v/|youtu.be/`, `embed/`, `shorts/`). **No audio fallback** — a video without captions
   fails outright.
5. `run_fabric(pattern, transcript, model)`.

### 7.2 Rumble (the most fragile path)
1. Validate URL contains `rumble\.com`.
2. Metadata: `yt-dlp` first; on any failure fall back to `_fetch_rumble_metadata`, a
   `cloudscraper` HTML scrape using `og:*` meta tags, `application/ld+json` `VideoObject`, and a
   series of best-effort regexes for channel/views/date.
3. Transcript: `download_and_transcribe` —
   - `cloudscraper` GET the page → regex `"video":"<id>"` or `embed/<id>` → embed ID.
   - GET `https://rumble.com/embed/<id>` → locate the `"ua"` (or `"u"`) JS object via a hand-written
     brace-matching scanner (`_extract_brace_block`, string/escape aware), `json.loads` it, then
     recursively walk it (`_find_urls`, depth ≤ 10) collecting every `url` key starting with `http`.
   - Rank candidates by container preference (audio formats 0 → mp4/webm 1 → m3u8 2 → tar 3), then
     by descending bitrate; pick the best.
   - Download (with `Referer: https://rumble.com/`); `m3u8` goes through ffmpeg instead; `tar` is
     explicitly rejected.
   - Non-mp3 results are transcoded to mono/32k mp3 before transcription.
4. `transcribe_audio` (below), then `run_fabric`.
5. Stores `original_transcript_cost` in metadata — the only place transcription cost is surfaced.

### 7.3 Audio transcription
`openrouter_service.transcribe_audio`:
- `ffprobe` gets duration → `ceil(duration / 600)` chunks → ffmpeg slices each into
  `chunk_NNN.mp3` (mono, 32 kbps) in a `chunks/` subdir.
- Each chunk is base64-encoded and POSTed to OpenRouter `/chat/completions` with model
  `openai/gpt-audio-mini` (env `TRANSCRIPTION_MODEL`) and an `input_audio` content part, asking for
  a verbatim transcript.
- Chunk texts are joined with `\n\n`; per-chunk `usage.cost` is summed.
- `finally:` deletes the chunk files and the directory. (Chunking means a fixed 10-minute grid, so
  words can be split at boundaries; there is no overlap or stitching logic.)

### 7.4 Fabric invocation (`fabric_service.run_fabric`)
- Command: `fabric -p <pattern> -m <model> -V <vendor>`, transcript piped to stdin.
- Timeout: `FABRIC_TIMEOUT` (default **600 s**), enforced via `asyncio.wait_for`.
- Retry: up to `MAX_RETRIES` (3) attempts, but **only** when the exit code is 1 *and* `"429"`
  appears in stderr — retried with exponential backoff (`2 s, 4 s`). Any other non-zero exit raises
  immediately.

### 7.5 Cost estimation (`cost_service`)
- Pricing pulled live from OpenRouter `/models` and cached module-globally for 300 s.
- Token counts via `tiktoken`; `_get_model_for_tokenizer` maps everything to `cl100k_base`
  (the branching is dead code — every path returns the same value) with a `len(text)//4` fallback.
- Cost = `in_tokens * prompt_price + out_tokens * completion_price`, rounded to 6 dp.
- **Input tokens count the transcript, not the assembled fabric prompt** (the pattern body itself is
  never measured), so this is a lower bound. It also does not include the transcription cost except
  on Rumble.

---

## 8. Frontend Structure

```
frontend/src/
├── main.jsx                     # StrictMode > BrowserRouter > App
├── App.jsx                      # 3 routes + catch-all redirect, all wrapped in <Layout>
├── index.css                    # @import "tailwindcss"  (only global style)
├── App.css                      # ← unused Vite template leftover
├── api/client.js                # all fetch calls; API_BASE = VITE_API_BASE || '/api'
├── hooks/usePersistedState.js   # useState mirroring into sessionStorage
├── components/
│   ├── Layout.jsx               # nav bar (YouTube / Rumble / History), dark theme
│   ├── PatternSelector.jsx      # searchable pattern combobox
│   ├── AnalysisRunner.jsx       # 2 s polling loop + ResultDisplay
│   └── MetadataDisplay.jsx      # metadata table renderer (modal body)
└── pages/
    ├── YouTubeAnalysisPage.jsx
    ├── RumbleAnalysisPage.jsx
    └── HistoryPage.jsx
```

**Routes:** `/` → redirect to `/analysis/youtube`; `/analysis/youtube`; `/analysis/rumble`;
`/history`; `*` → redirect to `/analysis/youtube`.

**The two analysis pages are ~95 % identical** — same model `<select>`, same URL input, same
`PatternSelector` wiring, same submit button, same error/`not_found`/`submitting` blocks, same
`<AnalysisRunner>`. They differ only in heading text, placeholder, icon, default pattern, and the
API function called.

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
- Confirmation also fires `onConfirm` → `handleAutoCheck` → `check-*-result`, which either loads a
  cached job into the runner or shows "No prior analysis found".
- `search` and `confirmed` are persisted to `sessionStorage` per `storageKey`
  (`youtube`/`rumble`), so tab state survives reloads.

**Persisted state keys:** `yt-url`, `yt-pattern`, `rumble-url`, `rumble-pattern`,
`analysis-model` (shared across both tabs), `pattern-search-<key>`, `pattern-confirmed-<key>`.
All `sessionStorage`, so they are per-tab and cleared when the tab closes.

**`AnalysisRunner`** polls `GET /api/jobs/{id}` every 2 s until `completed`/`failed`, with a
`cancelled` flag guarding against unmount races. `ResultDisplay` renders metadata lines + result as
one preformatted block, offers Copy (whole thing), Export PDF (jsPDF, dynamic import, filename
derived from the video title with filesystem-unsafe chars replaced), and a collapsible transcript.

**`HistoryPage`** fetches `GET /api/history` (default limit 50, **no pagination UI** — older jobs
are unreachable from the UI), filters by source with buttons (`All` / `Youtube` / `Rumble`), and
does client-side full-text search across URL, pattern, status, error, result, transcript, and
metadata title/channel. Each row expands inline to show result + transcript with copy buttons and
an "Open Original" link; a "Show Meta" button opens a modal (`Escape` closes it) rendering
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
- `run.sh` `cd`s to the repo root, sources `.venv` **there**, then `cd`s back to `backend/`. It
  warns if `frontend/dist/index.html` is missing.
- **`.venv` lives at the repo root.** Create it there.
- **Frontend dev mode:** `npm run dev` → Vite on **5174** (strictPort), proxying `/api` to 5173.
- `frontend/dist/` is gitignored, so a fresh clone **must run `npm run build`** before `run.sh`
  serves anything at `/`.

### Environment variables read by the backend
| Variable | Default | Where |
|---|---|---|
| `FABRIC_MODEL` | `deepseek/deepseek-v4-flash` | `fabric_service` (single source of truth) |
| `FABRIC_VENDOR` | `OpenRouter` | `fabric_service` |
| `FABRIC_TIMEOUT` | `600` | `fabric_service` |
| `FABRIC_MAX_RETRIES` | `3` | `fabric_service` |
| `FABRIC_RETRY_BASE_DELAY` | `2.0` | `fabric_service` |
| `TRANSCRIPTION_MODEL` | `openai/gpt-audio-mini` | `openrouter_service` |
| `TRANSCRIPTION_CHUNK_SECONDS` | `600` | `openrouter_service` |
| `OPENROUTER_API_BASE_URL` | `https://openrouter.ai/api/v1` | `openrouter_service` |
| `HOST` / `PORT` | `127.0.0.1` / `5173` | `run.sh` |
| `VITE_API_BASE` (frontend) | `/api` | `api/client.js` |

`OPENROUTER_API_KEY` is **not** read from the environment — it is parsed out of
`~/.config/fabric/.env` at import time by `openrouter_service.py`.

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
5. **No authentication anywhere.** Still true, and now mitigated only by the loopback bind. Do not
   set `HOST=0.0.0.0` on an untrusted network.

**Correctness / reliability**

6. **`running` is a terminal state on restart.** Tasks are in-process `asyncio.Task`s; if uvicorn
   reloads or crashes mid-analysis the row is never updated. The live DB already has **3 Rumble
   jobs stuck in `running` since 2026-09-16** — a visible symptom, not a hypothetical.
7. **No concurrency control.** Every request spawns an unbounded task; each Rumble job spawns its
   own `fabric` process (up to 600 s) plus ffmpeg. N parallel submissions = N LLM calls.
8. **Broad exception handling hides causes.** Every orchestrator wraps metadata fetch in
   `except (asyncio.TimeoutError, Exception): meta = {}` — `asyncio.TimeoutError` is redundant since
   Python 3.11 and the catch is total. `_fetch_rumble_metadata` likewise returns `{}` on any error.
   The `error` column is the only diagnostic, and it's just `str(e)`.
9. **Fabric timeout leaks the process.** On `asyncio.TimeoutError` the code calls `proc.kill()`
   and then raises — it never awaits the process, so the child can linger as a zombie.
10. **Rumble URL discovery is regex/JSON-shape archaeology** against an undocumented page structure
    (`"ua"`, `"u"`, `"video":"<id>"`, brace-matching). It will silently break whenever Rumble
    changes its embed payload. The 14 Rumble failures in the DB against 15 successes reflect this.
11. **`find_existing_transcript` requires `status='completed'`**, so a transcript obtained during a
    run that later failed at the fabric step is thrown away and re-fetched/re-transcribed next time
    — the most expensive possible caching rule.
12. **`estimate_cost` undercounts input tokens** (transcript only, not the pattern prompt) and
    ignores transcription cost entirely.
13. **No schema migrations.** `create_all` only creates; any column change needs manual SQLite work.
    `file_path` and the `file`/`web` `source` values are now legacy columns/rows.
14. **`App.css` and `assets/` are dead**, and `public/icons.svg` is unreferenced. `frontend/dist/`
    is gitignored and must be rebuilt after any UI change.
15. **No tests and no CI** anywhere in the repo.

**Maintainability**

16. **Two near-identical orchestrators**, two near-identical pages, two duplicated status handlers,
    two duplicated `check-result` handlers, and the metadata-formatting block repeated in four
    places.
17. `database_helpers._job_to_response` is declared `async` but performs no I/O; `get_job` and
    `list_jobs` each re-implement it inline instead of calling it. Three copies of the same
    13-field row→schema mapping.
18. Imports are placed inside function bodies in several spots (`database_helpers`, `cost_service`,
    `metadata_service`, `shared_router`).
19. `schemas.PatternInfo.description` is always empty because `list_patterns` never populates it,
    yet the frontend has rendering paths for it.

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
curl localhost:5173/api/health
curl localhost:5173/api/models | head -c 200
curl localhost:5173/api/history
```

**Inspect the database**
```bash
sqlite3 cve_osint.db \
  "select source,status,count(*) from analysis_jobs group by 1,2;"
```

**Glossary**
- **Fabric** — CLI tool that holds a library of reusable LLM prompt templates ("patterns") and
  pipes input through them to a provider.
- **Pattern** — a named prompt template (e.g. `summarize`, `extract_wisdom`). 261 are installed.
- **Transcript** — the text the pattern runs on. For video it is ASR or caption output.
- **Job** — one `(source, url, pattern, model)` analysis run, tracked by a UUID and a row in
  `analysis_jobs`.
- **Dedup** — returning a prior completed job instead of re-running an identical request.
