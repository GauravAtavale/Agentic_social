# How This Repo Works

This document explains the current structure of the repo and **what happens when you run `backend/run_server.py`**.

---

## 1. High-level structure

The repo has three main areas:

| Area | Purpose |
|------|--------|
| **`backend/`** | The main app: FastAPI server + API + static frontend (HTML/JS/CSS). This is what you run in production. |
| **`Personal_builder/`** | Standalone “Gaurav-style” multi-agent simulation: bidding, persona prompts, agents. Used by the backend only when a separate folder `Agentic_social_gaurav` exists. |
| **Root** | Voice interview script (`run_questions.py`), root `.env`, and optional `Conversations/`. Not required for the backend server. |

The backend is self-contained: it serves the UI and all API routes. It can optionally use **either**:

- **Built-in General flow**: personas from `backend/personas/*.json` + Claude (round-robin), or  
- **Gaurav flow**: a sibling folder `Agentic_social_gaurav` with `Personal_builder/` and `conversational_history.txt` (replay or live bidding stream).

---

## 2. What happens when you run `backend/run_server.py`

When you run:

```bash
python backend/run_server.py
# or: python backend/run_server.py --free-port --no-reload
```

the following happens, in order.

### Step 1: Script setup (`run_server.py`)

1. **Resolve backend directory**  
   `backend_dir = os.path.dirname(os.path.abspath(__file__))` → e.g. `.../Agentic_social/backend`.

2. **Change working directory**  
   `os.chdir(backend_dir)` so that later imports resolve correctly (e.g. `main:app`).

3. **Add backend to Python path**  
   `sys.path.insert(0, backend_dir)` so that `import main` loads `backend/main.py`.

4. **Optional flags**  
   - `--free-port`: kills any process on port 8000, then waits 2 seconds.  
   - `--no-reload`: runs a single process (no file watcher).

5. **Start Uvicorn**  
   `uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=...)`  
   So the **ASGI app** is `app` from the module `main` (i.e. `backend/main.py`).

### Step 2: Loading `main.py` (the FastAPI app)

When Uvicorn loads `main:app`:

1. **Paths and env**  
   - `BASE_DIR` = `backend/`  
   - `load_dotenv(BASE_DIR / ".env")` loads `backend/.env` (e.g. `ANTHROPIC_API_KEY`, `ELEVENLABS_API_KEY`).  
   - Defines paths: `CONVERSATIONS_DIR`, `PERSONAS_DIR`, `MATCHES_FILE`, `PROFILE_FILE`, `GENERAL_CONV_FILE`, etc.

2. **Optional “Gaurav” paths** (used only if that folder exists)  
   - `GAURAV_ROOT = BASE_DIR.parent / "Agentic_social_gaurav"`  
   - `GAURAV_PERSON_BUILDER = GAURAV_ROOT / "Personal_builder"`  
   - `GAURAV_HISTORY_FILE = GAURAV_ROOT / "conversational_history.txt"`  
   So the backend expects a **sibling** repo/folder `Agentic_social_gaurav` next to `Agentic_social`, with `Personal_builder` and history file inside it. The **current** repo’s `Personal_builder/` is not used by the backend unless it is inside such an `Agentic_social_gaurav` folder.

3. **FastAPI app creation**  
   - `app = FastAPI(...)`  
   - CORS middleware (allow all origins for dev)  
   - All routes and `app.mount("/static", StaticFiles(...))` are registered.

4. **Startup event**  
   - `ensure_human_file()` so `conversations/human.json` exists.  
   - Prints “Proxy AI Backend Running”, URLs for app, docs, health.

### Step 3: Server is listening

- **Host/port**: `0.0.0.0:8000` (all interfaces, port 8000).
- **Root `/`** → serves `backend/static/index.html` (main app).
- **`/profile`** → serves `backend/static/profile.html` (questionnaire + voice interview + “Create my persona”).
- **`/static/*`** → static files from `backend/static/` (e.g. `app.js`, `styles.css`, `profile.js`).
- **`/health`** → `{"status": "ok"}`.
- **`/docs`** → auto-generated OpenAPI docs (Swagger).

So: **running `backend/run_server.py` starts the single server that serves both the web UI and the API.** There is no separate frontend server.

---

## 3. How the frontend and API connect

1. User opens **http://localhost:8000** → FastAPI serves `index.html`.
2. `index.html` loads `/static/app.js` and `/static/styles.css`.
3. `app.js` calls backend APIs, e.g.:  
   - `GET /api/conversations/{group}` for Human, Sports, AI, Tech, General (or topic).  
   - `GET /api/conversations/general/stream` for General tab (SSE stream).  
   - `POST /api/conversations/human` to send a message.  
   - `GET /api/personas`, `GET /api/matches`, `POST /api/create-persona`, etc.
4. **Profile** flow: user goes to `/profile` → `profile.html` → questionnaire and/or in-app voice interview → `POST /api/create-persona` → backend writes a JSON file under `backend/personas/`.

So the “frontend” is just static files served by the same FastAPI app; there is no separate Node/React/Vite server.

---

## 4. Where things live (data and config)

- **Personas**: `backend/personas/*.json` (from Profile “Create my persona” or `backend/create_persona.py`).
- **Conversations**: `backend/conversations/` (e.g. `human.json`, `general.json`, `sports.json`, `ai.json`, `tech.json`).
- **User profile**: `backend/profile.json`.
- **Matches**: `backend/matches.json` (can be generated by `backend/generate_conversations.py`).
- **Connection requests**: `backend/connection_requests.json`.
- **Env**: `backend/.env` (and optionally root `.env` for `run_questions.py`).

---

## 5. General tab: two modes

The **General** tab stream (`GET /api/conversations/general/stream`) can behave in two ways:

1. **Built-in mode** (no `Agentic_social_gaurav`):  
   Uses `backend/personas/*.json` only. Requires at least 2 personas. Streams turns via Claude in round-robin; no bidding, no `Personal_builder`, no `conversational_history.txt`.

2. **Gaurav mode** (when `Agentic_social_gaurav` exists next to this repo):  
   - **Replay**: if `Agentic_social_gaurav/conversational_history.txt` exists and frontend sends `replay=true`, the backend just replays that file with a pause between messages (no API calls).  
   - **Live generate**: uses `Agentic_social_gaurav/Personal_builder/` (sys_prompt, persona prompts, bidding logic) and appends to `conversational_history.txt`, streaming tokens via Claude.  
   The backend does **not** use the `Personal_builder/` folder that lives **inside** the current repo (`Agentic_social`); it only looks for `Agentic_social_gaurav/Personal_builder/`.

So: **running `backend/run_server.py` is enough to use the app and the built-in General flow.** The Gaurav flow is an optional extra that depends on a separate folder layout.

---

## 6. Other scripts (not started by `run_server.py`)

- **`run_questions.py`** (root): Standalone voice Q&A; TTS questions, records answers, STT; writes to `conversation.json` (and optional audio). Uses root `.env` (e.g. `ELEVENLABS_API_KEY`). Not part of the backend server.
- **`backend/create_persona.py`**: CLI to turn an interview JSON (e.g. from `run_questions.py`) into a persona JSON in `backend/personas/`.
- **`backend/generate_conversations.py`**: Generates group conversations (sports, ai, tech) and `matches.json` from personas; needs at least 3 personas in `backend/personas/`.
- **`Personal_builder/run.py`**: Standalone simulation (bidding, agents, history file). Intended to be run inside an `Agentic_social_gaurav`-style layout; the backend reimplements a similar flow in `main.py` when that folder exists.

---

## 7. Summary: “What happens when I run `backend/run_server.py`?”

1. **`run_server.py`** switches into `backend/`, adds it to `sys.path`, optionally frees port 8000, then starts **Uvicorn** with `main:app` on `0.0.0.0:8000`.
2. **`main.py`** loads: paths, `.env`, and the FastAPI app with all routes and static mount.
3. The **same process** serves the web app (HTML/JS/CSS) and all APIs; no separate frontend server.
4. **General tab** uses either built-in personas in `backend/personas/` or, if present, the sibling `Agentic_social_gaurav` folder (replay or live stream with `Personal_builder` there).
5. **Personal_builder** in the current repo is not used by the backend unless it is placed inside an `Agentic_social_gaurav` directory next to this repo.

If you want to simplify the architecture next, we can (for example) unify the General tab to a single path, clarify or move `Personal_builder`, and document a single recommended way to run the app.
