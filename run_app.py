# -*- coding: utf-8 -*-
"""
Insight-Arc Desktop Application Launcher
Starts the local FastAPI server and opens the browser interface.
"""

import multiprocessing
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path
from dotenv import load_dotenv

# Ensure multiprocessing support for frozen PyInstaller executable on Windows
multiprocessing.freeze_support()

# Locate application directory and load .env from next to the executable
if getattr(sys, "frozen", False):
    app_dir = Path(sys.executable).resolve().parent
else:
    app_dir = Path(__file__).resolve().parent

env_file = app_dir / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)
else:
    load_dotenv(override=True)

import uvicorn
from web_app.main import app


def open_browser(url: str, delay: float = 1.2):
    time.sleep(delay)
    try:
        webbrowser.open(url)
    except Exception:
        pass


def main():
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    url = f"http://{host}:{port}"

    hosted_url = os.getenv("HOSTED_SERVER_URL", "(not set in .env)")
    chats_dir = app_dir / "chats"
    chats_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("        Insight-Arc — Conversational Data Analysis Agent")
    print("=" * 65)
    print(f"  Local Web Interface : {url}")
    print(f"  Configuration File  : {env_file if env_file.exists() else 'Default (.env not found)'}")
    print(f"  Hosted Server URL   : {hosted_url}")
    print(f"  Chat Archives       : {chats_dir}")
    print("  Status              : Opening default browser...")
    print("-" * 65)
    print("  Keep this window open while using Insight-Arc.")
    print("  Press Ctrl+C to stop the application.")
    print("=" * 65)

    # Launch browser in background thread
    threading.Thread(target=open_browser, args=(url,), daemon=True).start()

    # Run uvicorn server (single process, no reload for frozen packaging)
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
