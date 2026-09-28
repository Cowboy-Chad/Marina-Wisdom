import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.database import init_db
from backend.routers.youtube_router import router as youtube_router
from backend.routers.rumble_router import router as rumble_router
from backend.routers.shared_router import router as shared_router

# The built frontend is served from the same origin as the API (http://localhost:5173),
# so the browser reaches /api without a cross-origin request. CORS below covers the
# Vite dev server, which runs on a different port.
DIST_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="CVE-OSINT-1", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    # Any localhost origin, on any port: covers the Vite dev server and any
    # port it falls back to. Not reachable from other hosts.
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(youtube_router)
app.include_router(rumble_router)
app.include_router(shared_router)


def _mount_frontend() -> None:
    """Serve frontend/dist at / so the whole app lives on one port.

    Registered after the API routers, so /api/* still wins. Any other path
    returns index.html so React Router can handle deep links on reload.
    """
    if not os.path.isdir(DIST_DIR):
        print(f"[warn] frontend build not found at {DIST_DIR}")
        print("[warn] run: cd frontend && npm install && npm run build")
        return

    assets_dir = os.path.join(DIST_DIR, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    index_html = os.path.join(DIST_DIR, "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        if full_path:
            candidate = os.path.realpath(os.path.join(DIST_DIR, full_path))
            # Never serve anything outside the build directory.
            if candidate.startswith(os.path.realpath(DIST_DIR) + os.sep) and os.path.isfile(candidate):
                return FileResponse(candidate)
        return FileResponse(index_html)


_mount_frontend()
