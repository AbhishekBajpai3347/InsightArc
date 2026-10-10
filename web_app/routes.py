"""
HTTP API of the LOCAL server (runs on the client's machine). Deliberately thin.

Endpoints
    GET  /api/health              liveness check
    GET  /api/dataset             metadata of the active dataset, or null
    POST /api/dataset/load        multipart upload of a dataset file
    POST /api/dataset/clear       forget the dataset AND the analysis memory
    POST /api/conversation/clear  forget the analysis memory only
    POST /api/chat                ask a question, get a reply
    POST /api/archive             write a completed conversation to chats/

Handlers are plain `def` (not `async def`) on purpose: FastAPI runs them in a worker
thread, so slow pandas work and the call to the hosted server never block the server.
"""

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field, field_validator

from . import archive, engine

router = APIRouter(prefix="/api")


class ChatRequest(BaseModel):
    message: str = Field(max_length=4000)
    request_id: str | None = Field(default=None, max_length=100)

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:  # the browser already checks this; the server checks again
            raise ValueError("Message must not be empty.")
        return value


class ArchiveRequest(BaseModel):
    created_at: str | None = Field(default=None, max_length=64)
    dataset: dict | None = None
    messages: list[dict] = Field(max_length=500)


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/dataset")
def get_dataset():
    return {"dataset": engine.metadata()}


@router.post("/dataset/load")
def load_dataset_file(file: UploadFile = File(...)):
    try:
        return {"dataset": engine.load(file.filename or "dataset", file.file)}
    except engine.LoadError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.post("/dataset/clear")
def clear_dataset():
    engine.clear()
    return {"ok": True}


@router.post("/conversation/clear")
def clear_conversation():
    engine.reset_conversation()
    return {"ok": True}


@router.post("/chat")
def chat(request: ChatRequest):
    # Failures inside the engine come back as a normal 200 with {"type": "error"}.
    # HTTP errors (422 etc.) are reserved for malformed requests.
    reply = engine.query(request.message)
    return {**reply, "request_id": request.request_id}


@router.post("/archive", status_code=201)
def archive_conversation(request: ArchiveRequest):
    if not request.messages:
        raise HTTPException(status_code=400, detail="Nothing to archive.")
    name = archive.write_chat(request.created_at, request.dataset, request.messages)
    return {"file": name}
