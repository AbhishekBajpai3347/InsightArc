"""
Passive chat archive.

Completed conversations are copied into chats/ as small JSON files. This module only
WRITES. Nothing in the application ever lists, reads, searches, or deletes these files;
they are permanent history that only the user removes by hand.

Safety by construction:
  * files are opened with mode "x" (create-only), so an existing file can never be overwritten;
  * file names are generated here, never taken from the request;
  * there is no code path that deletes anything.
"""

import json
from datetime import datetime
from itertools import count
from pathlib import Path
import sys

if getattr(sys, "frozen", False):
    ARCHIVE_DIR = Path(sys.executable).resolve().parent / "chats"
else:
    ARCHIVE_DIR = Path(__file__).resolve().parent.parent / "chats"

# Never archive anything heavy, even if a client sends it.
_DROPPED_MESSAGE_KEYS = {"image"}


def write_chat(created_at: str | None, dataset: dict | None, messages: list[dict]) -> str:
    """Write one conversation snapshot to a new chats/chat_YYYYMMDD_HHMMSS.json. Returns the file name."""
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    payload = {
        "created_at": created_at,
        "archived_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "dataset": dataset,  # lightweight metadata only: filename, rows, column names
        "messages": [
            {key: value for key, value in message.items() if key not in _DROPPED_MESSAGE_KEYS}
            for message in messages
        ],
    }

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    for attempt in count(1):
        name = f"chat_{stamp}.json" if attempt == 1 else f"chat_{stamp}_{attempt}.json"
        try:
            with open(ARCHIVE_DIR / name, "x", encoding="utf-8") as file:  # "x" = never overwrite
                json.dump(payload, file, ensure_ascii=False, indent=2)
            return name
        except FileExistsError:
            continue  # two archives in the same second: try the next suffix
