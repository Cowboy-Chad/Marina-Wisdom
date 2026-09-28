import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.database import init_db
from backend.routers.auth_router import router as auth_router
from backend.routers.rumble_router import router as rumble_router
from backend.routers.shared_router import router as shared_router
from backend.services.auth_service import resolve_token
from backend.services.dependencies import get_bearer_token

# The built frontend is served from the same origin as the API (http://localhost:5173),
# so the browser reaches /api without a cross-origin request. CORS below covers the
# Vite dev server, which runs on a different port.
DIST_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="CVE-OSINT-1", lifespan=lifespan)

# Everything under /api requires a bearer token, except these. Anything outside
# /api is the built frontend, which has to be reachable to show the login form.
_PUBLIC_API_PATHS = {"/api/health", "/api/auth/register"}


async def require_auth(request: Request, call_next):
    """Reject unauthenticated API calls before they reach a route.

    Done here rather than per-route so a new endpoint is protected by default;
    forgetting a dependency on one handler would silently open it up.
    """
    # rstrip("/") so a trailing slash on a public path does not 401 before
    # FastAPI's own redirect can normalize it.
    path = request.url.path.rstrip("/") or "/"
    if request.method == "OPTIONS" or not path.startswith("/api/") or path in _PUBLIC_API_PATHS:
        return await call_next(request)

    user = await resolve_token(get_bearer_token(request))
    if user is None:
        return JSONResponse({"detail": "Not signed in."}, status_code=401)

    request.state.user = user
    return await call_next(request)


# Registered before CORSMiddleware on purpose. Starlette builds the stack so the
# middleware added last is the outermost one, and CORS has to be outermost:
# otherwise a 401 from this middleware reaches the browser without CORS headers
# and shows up as an opaque CORS failure instead of "please sign in".
app.middleware("http")(require_auth)

# Browser origins allowed to call the API.
#
# localhost on any port is always allowed, so the Vite dev server works without
# configuration. Deployed origins are listed in ALLOWED_ORIGINS as a
# comma-separated list, e.g.
#   ALLOWED_ORIGINS=https://cve-osint.netlify.app,https://osint.qmn.example
# Without it a deployed frontend cannot reach this API at all.
_extra_origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_extra_origins,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
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
