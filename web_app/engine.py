"""
Local engine adapter: connects the web server to YOUR code (loader, cleaner, run_chat).
Replaces the old mock. It owns the runtime state of the (single) active dataset:

    _df        the pandas DataFrame
    _filename  what to show in the sidebar
    _memory    the analysis memory handed to / returned by run_chat

All of it lives in this process's RAM only, on the client's machine. Nothing is persisted.
A lock serializes every operation: pandas state and matplotlib's global figure are not
safe to touch from two requests at once.
"""

import csv
import json
import logging
import os
import re
import shutil
import tempfile
import threading
from pathlib import Path

import pandas as pd

from data.cleaner import clean_dataset
from data.loader import load_dataset
from intelligence.chatbot import ChatResult, run_chat

logger = logging.getLogger("engine")

MAX_TABLE_ROWS = 10  # rows sent to the browser for a table (the UI shows 10 anyway)
PARTIAL_NOTE = "Note: this request was only partially completed."


class LoadError(Exception):
    """A dataset could not be loaded. The message is safe to show to the user."""


_lock = threading.Lock()
_df: pd.DataFrame | None = None
_filename: str | None = None
_memory: list[str] = []
_last_result: pd.DataFrame | None = None


# --------------------------------------------------------------------------------------
# Dataset metadata (what the sidebar shows)
# --------------------------------------------------------------------------------------
def simple_dtype(dtype) -> str:
    """pandas dtype -> one of: bool, int, float, date, text, other."""
    if pd.api.types.is_bool_dtype(dtype):
        return "bool"
    if pd.api.types.is_integer_dtype(dtype):
        return "int"
    if pd.api.types.is_float_dtype(dtype):
        return "float"
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "date"
    if (
        isinstance(dtype, pd.CategoricalDtype)
        or pd.api.types.is_object_dtype(dtype)
        or pd.api.types.is_string_dtype(dtype)
    ):
        return "text"
    return "other"


def _metadata() -> dict | None:
    if _df is None:
        return None
    return {
        "filename": _filename,
        "rows": int(len(_df)),
        "columns": [{"name": str(c), "dtype": simple_dtype(t)} for c, t in _df.dtypes.items()],
    }


def metadata() -> dict | None:
    with _lock:
        return _metadata()


# --------------------------------------------------------------------------------------
# Dataset lifecycle
# --------------------------------------------------------------------------------------
def load(filename: str, fileobj) -> dict:
    """
    Load an uploaded file: write it to a temp file (your loader wants a path, and keeps the
    original extension), run load_dataset then clean_dataset (like the console does),
    delete the temp file. The previous dataset and memory are discarded as soon as this starts.
    """
    global _df, _filename, _memory, _last_result
    filename = Path(filename.replace("\\", "/")).name or "dataset"
    suffix = Path(filename).suffix.lower()

    with _lock:
        _df, _filename, _memory, _last_result = None, None, [], None

        fd, temp_path = tempfile.mkstemp(suffix=suffix)
        try:
            with os.fdopen(fd, "wb") as temp_file:
                shutil.copyfileobj(fileobj, temp_file)
            df = clean_dataset(load_dataset(temp_path))
            if not isinstance(df, pd.DataFrame):
                raise ValueError("The file did not produce a table.")
        except Exception as error:
            logger.warning("Could not load %s: %s", filename, type(error).__name__)
            raise LoadError(_load_message(filename, error)) from error
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

        _df, _filename = df, filename
        return _metadata()


def _load_message(filename: str, error: Exception) -> str:
    text = str(error).strip()
    first_line = text.splitlines()[0] if text else type(error).__name__
    return f"Could not read {filename}. {first_line}"


def clear() -> None:
    """Forget the dataset AND the analysis memory."""
    global _df, _filename, _memory, _last_result
    with _lock:
        _df, _filename, _memory, _last_result = None, None, [], None


def reset_conversation() -> None:
    """Forget the analysis memory only; the dataset stays."""
    global _memory, _last_result
    with _lock:
        _memory, _last_result = [], None


# --------------------------------------------------------------------------------------
# Chat
# --------------------------------------------------------------------------------------
def query(message: str) -> dict:
    """Run one question through run_chat and return a reply dict for the frontend."""
    global _df, _memory, _last_result
    with _lock:
        if _df is None:
            return {"type": "error", "message": "No dataset is loaded. Upload a dataset and try again."}

        try:
            result = run_chat(message, _df, _memory, last_result=_last_result, show_progress=False)
        except Exception:
            logger.exception("run_chat failed")
            return {"type": "error", "message": "Something went wrong while processing your request."}

        _df, _memory, _last_result = result.dataframe, result.memory, result.last_result
        return build_reply(result, _metadata())


def build_reply(result: ChatResult, dataset: dict | None) -> dict:
    """
    ChatResult -> reply for the frontend. The LAST tool call of the turn decides what is shown
    next to the LLM's text:

        modifying tool        -> type "modification" (the sidebar updates)
        plot                  -> type "image"
        DataFrame / Series    -> type "table"
        CSV text that parses  -> type "table"
        anything else         -> type "final" (text only)
        last tool failed after an earlier success -> text + a note, no table / chart
        no usable answer      -> type "error"

    If the dataset changed during the turn, the reply always carries the new metadata,
    so the sidebar can never go stale.
    """
    reply = {"type": "final", "message": result.answer}

    if result.status == "error":
        reply["type"] = "error"
    elif result.status == "partial":
        reply["message"] = f"{result.answer}\n\n{PARTIAL_NOTE}"
    elif result.last_tool:
        reply.update(_output_for(result.last_tool))

    if result.dataset_changed or reply["type"] == "modification":
        reply["dataset"] = dataset
    return reply


def _output_for(tool: dict) -> dict:
    if tool["modifies_dataset"]:
        return {"type": "modification"}

    image_b64 = tool.get("figure_png")
    if not image_b64 and isinstance(tool.get("result"), dict):
        image_b64 = tool["result"].get("image_base64")

    if image_b64:
        name = tool["name"].replace("plot_", "").replace("_", " ")
        return {"type": "image", "image": image_b64, "alt": f"Chart: {name}"}

    result = tool.get("result")
    if isinstance(result, pd.Series):
        result = result.reset_index()
    if isinstance(result, pd.DataFrame):
        return {"type": "table", **dataframe_to_table(result)}
    if isinstance(result, str):
        table = csv_text_to_table(result)
        if table:
            return {"type": "table", **table}
    return {}


# --------------------------------------------------------------------------------------
# Tables
# --------------------------------------------------------------------------------------
def dataframe_to_table(df: pd.DataFrame) -> dict:
    """First MAX_TABLE_ROWS rows as JSON-safe values (NaN -> null, dates -> ISO text)."""
    head = df.head(MAX_TABLE_ROWS)
    payload = json.loads(head.to_json(orient="split", date_format="iso"))
    return {
        "columns": [str(c) for c in head.columns],
        "rows": payload["data"],
        "total_rows": int(len(df)),
    }


_NUMBER = re.compile(r"^-?(0|[1-9]\d*)(\.\d+)?$")


def _coerce(value: str):
    """'12' -> 12, '0.63' -> 0.63, '' -> None, anything else stays text (so '007' is kept)."""
    if value == "":
        return None
    if _NUMBER.match(value) and len(value) <= 15:
        return float(value) if "." in value else int(value)
    return value


def csv_text_to_table(text: str) -> dict | None:
    """
    Turn CSV text into a table, or return None.

    Strict on purpose: some tools join values with commas WITHOUT quoting, so a value like
    "Braund, Mr. Owen" would shift the columns. A table is only produced when the text has
    a header and at least one row, no blank lines, and EVERY line has the same number of
    fields. Otherwise the reply stays plain text instead of showing a misaligned table.
    """
    lines = text.strip().splitlines()
    if len(lines) < 2 or any(not line.strip() for line in lines):
        return None
    try:
        parsed = list(csv.reader(lines))
    except csv.Error:
        return None

    header, body = parsed[0], parsed[1:]
    if len(header) < 2 or any(not name.strip() for name in header):
        return None
    if any(len(row) != len(header) for row in body):
        return None

    return {
        "columns": header,
        "rows": [[_coerce(value) for value in row] for row in body[:MAX_TABLE_ROWS]],
        "total_rows": len(body),
    }
