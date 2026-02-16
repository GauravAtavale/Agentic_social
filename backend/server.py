"""
Web server for Agentic Social: world_chat UI. Runs run.py on startup
and streams new lines from data/conversational_history.txt to the UI.
"""
import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path


def _free_port(port: int = 8001) -> None:
    """Kill any process listening on the given port."""
    try:
        out = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode == 0 and out.stdout.strip():
            for pid in out.stdout.strip().split():
                try:
                    os.kill(int(pid), signal.SIGKILL)
                except (ProcessLookupError, ValueError):
                    pass
            time.sleep(2)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)
sys.path.insert(0, str(BASE_DIR))

# Load .env so subprocess run.py inherits ANTHROPIC_API_KEY, GROQ_API_KEY
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
    load_dotenv(BASE_DIR.parent / ".env")
except ImportError:
    pass

# Paths relative to repo root
REPO_ROOT = BASE_DIR.parent
HISTORY_FILE = REPO_ROOT / "data" / "conversational_history.txt"
FRONTEND_DIR = REPO_ROOT / "frontend"
CONFIG_DIR = REPO_ROOT / "config"
DATA_DIR = REPO_ROOT / "data"

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Agentic Social – world_chat")

_run_process = None


def _load_history():
    """Return list of {role, content} from conversational_history.txt."""
    if not HISTORY_FILE.exists():
        return []
    out = []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    out.append({"role": entry.get("role", ""), "content": entry.get("content", "")})
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return out


def _stream_new_lines():
    """Generator: poll HISTORY_FILE and yield SSE only for new lines (since connection)."""
    # Start from current line count so we only send lines added after client connected
    try:
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                last_count = sum(1 for ln in f if ln.strip())
        else:
            last_count = 0
    except OSError:
        last_count = 0
    while True:
        try:
            if HISTORY_FILE.exists():
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    lines = [ln.strip() for ln in f if ln.strip()]
                for i in range(last_count, len(lines)):
                    try:
                        entry = json.loads(lines[i])
                        ev = {"type": "message", "role": entry.get("role", ""), "content": entry.get("content", "")}
                        yield f"data: {json.dumps(ev)}\n\n"
                    except json.JSONDecodeError:
                        pass
                last_count = len(lines)
        except OSError:
            pass
        time.sleep(0.5)


@app.get("/")
async def serve_index():
    """Serve the main UI (world_chat)."""
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        return {"error": "Frontend files not found."}
    return FileResponse(index_path)


@app.get("/api/history")
async def api_history():
    """Return full conversation history (for initial page load)."""
    return {"messages": _load_history()}


@app.get("/api/history/stream")
async def api_history_stream():
    """SSE: emit new messages as they are appended to conversational_history.txt."""
    def gen():
        for chunk in _stream_new_lines():
            yield chunk

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


def _ensure_history_file_exists():
    """Ensure conversational_history.txt exists with at least one line so run.py can read last speaker."""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not HISTORY_FILE.exists() or HISTORY_FILE.stat().st_size == 0:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            f.write('{"role": "Gaurav", "content": "Conversation started."}\n')
        print("Created empty conversational_history.txt with one seed line for run.py.")


def _start_run_py():
    """Start run.py in the background (writes to ../conversational_history.txt)."""
    global _run_process
    if _run_process is not None and _run_process.poll() is None:
        return
    run_py = BASE_DIR / "run.py"
    if not run_py.exists():
        print("Warning: run.py not found, skipping auto-start")
        return
    _ensure_history_file_exists()
    # Inherit env (including ANTHROPIC_API_KEY, GROQ_API_KEY from .env)
    env = os.environ.copy()
    _run_process = subprocess.Popen(
        [sys.executable, str(run_py)],
        cwd=str(BASE_DIR),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    def log_stderr():
        if _run_process.stderr:
            for line in iter(_run_process.stderr.readline, ""):
                if line:
                    sys.stderr.write("[run.py] " + line.decode("utf-8", errors="replace"))
            _run_process.stderr.close()

    t = threading.Thread(target=log_stderr, daemon=True)
    t.start()
    print("Started run.py in background (PID %s). Check stderr for [run.py] if history is not updating." % _run_process.pid)


@app.on_event("startup")
async def startup():
    _start_run_py()
    print("Agentic Social – world_chat")
    print("  UI: http://localhost:8001")
    print("  run.py is running in background; new lines in data/conversational_history.txt stream to the UI.")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Agentic Social world_chat server")
    parser.add_argument("--free-port", action="store_true", help="Kill process on port 8001 before starting")
    args = parser.parse_args()
    if args.free_port:
        _free_port(8001)
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)


if __name__ == "__main__":
    main()
