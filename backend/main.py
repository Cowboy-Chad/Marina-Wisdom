import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.database import init_db
from backend.routers.youtube_router import router as youtube_router
from backend.routers.rumble_router import router as rumble_router
from backend.routers.web_router import router as web_router
from backend.routers.file_router import router as file_router
from backend.routers.shared_router import router as shared_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="CVE-OSINT-1", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(youtube_router)
app.include_router(rumble_router)
app.include_router(web_router)
app.include_router(file_router)
app.include_router(shared_router)