"""
Local application server: serves the static frontend and the small JSON API.

Run from the project root (the folder that contains web_app/ and chats/):

    uvicorn web_app.main:app --reload

then open http://127.0.0.1:8000
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .archive import ARCHIVE_DIR
from .routes import router

STATIC_DIR = Path(__file__).resolve().parent / "static"

ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)  # make sure chats/ exists; nothing in it is ever touched here

app = FastAPI(title="Insight Arc (local)")
app.include_router(router)

# Mounted last so /api/* and /docs are matched first. html=True serves index.html at "/".
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
