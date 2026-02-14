"""
Proxy AI Backend - FastAPI server.
Serves conversations (sports, ai, tech, human), personas, matches, and health.
"""

import json
from pathlib import Path

from dotenv import load_dotenv

# Require anthropic at startup so General/Human streaming fails fast if not installed
try:
    import anthropic  # noqa: F401
except ImportError:
    raise ImportError(
        "Missing 'anthropic' package. From the backend folder run: pip install -r requirements.txt\n"
        "Or: python -m pip install anthropic\n"
        "Then start the server with the same Python: python -m uvicorn main:app --reload"
    )

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent
# Load .env from backend/ so ANTHROPIC_API_KEY etc. are set when the server runs
load_dotenv(BASE_DIR / ".env")
CONVERSATIONS_DIR = BASE_DIR / "conversations"
PERSONAS_DIR = BASE_DIR / "personas"
MATCHES_FILE = BASE_DIR / "matches.json"
HUMAN_CONV_FILE = CONVERSATIONS_DIR / "human.json"
PROFILE_FILE = BASE_DIR / "profile.json"
CONNECTION_REQUESTS_FILE = BASE_DIR / "connection_requests.json"
GENERAL_CONV_FILE = CONVERSATIONS_DIR / "general.json"

# Gaurav's Agentic_social_gaurav: personas, history, bidding (exact replica for General tab stream)
GAURAV_ROOT = BASE_DIR.parent / "Agentic_social_gaurav"
GAURAV_PERSON_BUILDER = GAURAV_ROOT / "Personal_builder"
GAURAV_HISTORY_FILE = GAURAV_ROOT / "conversational_history.txt"

# Same dicts as run.py
GAURAV_PERSON_ROLE = {
    "Gaurav_Atavale": "Gaurav",
    "Anagha_Palandye": "Anagha",
    "Kanishkha_S": "Kanishkha",
    "Nirbhay_R": "Nirbhay",
}
GAURAV_ROLE_PERSON = {v: k for k, v in GAURAV_PERSON_ROLE.items()}
GAURAV_INITIAL_CREDITS = 30

app = FastAPI(title="Proxy AI Backend")

# CORS for development - allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Helpers ---

def load_json(filepath: Path, default=None):
    """Load JSON from file. Return default if file not found or invalid."""
    if default is None:
        default = {}
    try:
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except (json.JSONDecodeError, OSError):
        return default


def save_json(filepath: Path, data: dict | list) -> None:
    """Ensure parent dir exists and write JSON."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# --- Request bodies ---

class HumanMessage(BaseModel):
    speaker: str | None = None
    text: str


class ReactBody(BaseModel):
    message_id: int
    emoji: str


class ConnectionRequestBody(BaseModel):
    to: str  # match name


class CreatePersonaBody(BaseModel):
    profile: dict
    conversation: list | None = None  # optional interview Q&A


# --- Endpoints ---

@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok"}


@app.get("/api/conversations/{group}")
async def get_conversation_group(group: str):
    """Read conversation for any group (sports, ai, tech, human, finance, politics, etc.)."""
    if group == "human":
        ensure_human_file()
        data = load_json(HUMAN_CONV_FILE, default={"messages": []})
        if "messages" not in data:
            data = {"messages": []}
        for i, m in enumerate(data["messages"]):
            if "id" not in m:
                m["id"] = i
            if "reactions" not in m:
                m["reactions"] = {}
        return data
    path = CONVERSATIONS_DIR / f"{group.lower()}.json"
    if group.lower() == "general" and not path.exists():
        return {"group": "General", "topic": "general chat", "participants": [], "messages": []}
    data = load_json(path)
    if data == {} and not path.exists():
        raise HTTPException(status_code=404, detail=f"conversation '{group}' not found")
    return data


def _load_personas_list() -> list[dict]:
    """Load all persona JSON files from personas/."""
    if not PERSONAS_DIR.exists():
        return []
    out = []
    for p in PERSONAS_DIR.glob("*.json"):
        try:
            out.append(load_json(p, default={}))
        except Exception:
            continue
    return out


def _general_system_prompt(persona: dict) -> str:
    """Build system prompt for one persona in general chat (like agentic_social_gaurav)."""
    name = persona.get("name", "Unknown")
    return f"""You are {name}. Your personality: {persona.get('personality_summary', '')}
Interests: {persona.get('interests', [])}
Communication style: {persona.get('communication_style', '')}

You are in a general group chat. Reply naturally as yourself. Keep to 1-2 sentences (~50 words). Do not break character."""


def _generate_one_general_message(personas: list[dict], persona_index: int, history: list[dict]) -> str:
    """Generate one message from the given persona using Claude (multi-agent turn)."""
    import os
    from anthropic import Anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "[ANTHROPIC_API_KEY not set]"
    persona = personas[persona_index]
    name = persona.get("name", "Unknown")
    sys_prompt = _general_system_prompt(persona)
    history_text = "\n".join(f"{m.get('speaker', '?')}: {m.get('text', '')}" for m in history[-10:])
    user_content = f"Conversation so far:\n{history_text}\n\nYour turn. Reply as {name} (1-2 sentences only):"
    try:
        client = Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=256,
            system=sys_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
    except Exception as e:
        return f"[Error: {e}]"
    text = ""
    if msg.content and len(msg.content) > 0:
        block = msg.content[0]
        text = getattr(block, "text", None) or (block.get("text") if isinstance(block, dict) else "") or ""
    return (text or "").strip() or "(no response)"


@app.post("/api/conversations/general/generate")
async def generate_general_conversation(turns: int = 10):
    """
    Simulate multi-agent chat for General tab (like agentic_social_gaurav).
    Picks personas from personas/, takes turns speaking via Claude, appends to general.json.
    """
    from datetime import datetime
    import random

    personas = _load_personas_list()
    if len(personas) < 2:
        raise HTTPException(
            status_code=400,
            detail="Need at least 2 personas in personas/ to generate general conversation. Run create_persona.py first.",
        )
    data = load_json(GENERAL_CONV_FILE, default={"group": "General", "topic": "general chat", "participants": [], "messages": []})
    if "messages" not in data:
        data["messages"] = []
    messages = data["messages"]
    participants = list({m.get("speaker") for m in messages if m.get("speaker")})
    for p in personas:
        name = p.get("name")
        if name and name not in participants:
            participants.append(name)
    if not participants:
        participants = [p.get("name", "Unknown") for p in personas[:5]]
    data["participants"] = participants

    # Round-robin over personas (or random if we want variety like bidding)
    num_personas = len(personas)
    for i in range(turns):
        persona_index = i % num_personas
        persona = personas[persona_index]
        name = persona.get("name", "Unknown")
        reply = _generate_one_general_message(personas, persona_index, messages)
        messages.append({
            "speaker": name,
            "text": reply,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })
    data["messages"] = messages
    CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)
    save_json(GENERAL_CONV_FILE, data)
    return {"status": "generated", "turns": turns, "messages": messages}


def _stream_one_general_message(personas: list[dict], persona_index: int, history: list[dict]):
    """Stream one message from the given persona using Claude; yields (speaker, full_text)."""
    import os
    from anthropic import Anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        yield None, "[ANTHROPIC_API_KEY not set]"
        return
    persona = personas[persona_index]
    name = persona.get("name", "Unknown")
    sys_prompt = _general_system_prompt(persona)
    history_text = "\n".join(f"{m.get('speaker', '?')}: {m.get('text', '')}" for m in history[-10:])
    user_content = f"Conversation so far:\n{history_text}\n\nYour turn. Reply as {name} (1-2 sentences only):"
    full_text = ""
    try:
        client = Anthropic(api_key=api_key)
        with client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=256,
            system=sys_prompt,
            messages=[{"role": "user", "content": user_content}],
        ) as stream:
            for text in stream.text_stream:
                full_text += text
                yield (name, text, False)  # (speaker, delta, is_final)
        full_text = (full_text or "").strip() or "(no response)"
        yield (name, full_text, True)
    except Exception as e:
        yield (name, f"[Error: {e}]", True)


def _general_stream_generator(turns: int, pause_seconds: float = 10):
    """Generator that yields SSE events for General tab streaming. Pauses after each message so user can read."""
    from datetime import datetime
    import time

    personas = _load_personas_list()
    if len(personas) < 2:
        yield f"data: {json.dumps({'type': 'error', 'detail': 'Need at least 2 personas'})}\n\n"
        return
    data = load_json(GENERAL_CONV_FILE, default={"group": "General", "topic": "general chat", "participants": [], "messages": []})
    messages = list(data.get("messages") or [])
    num_personas = len(personas)

    for i in range(turns):
        persona_index = i % num_personas
        name = personas[persona_index].get("name", "Unknown")
        yield f"data: {json.dumps({'type': 'message_start', 'speaker': name})}\n\n"
        full_message = ""
        for speaker, chunk, is_final in _stream_one_general_message(personas, persona_index, messages):
            if not is_final and chunk:
                full_message += chunk
                yield f"data: {json.dumps({'type': 'chunk', 'speaker': speaker, 'delta': chunk})}\n\n"
            elif is_final:
                full_message = (chunk or full_message or "").strip() or "(no response)"
        msg_obj = {"speaker": name, "text": full_message, "timestamp": datetime.utcnow().isoformat() + "Z"}
        messages.append(msg_obj)
        yield f"data: {json.dumps({'type': 'message_end', 'speaker': name, 'text': full_message})}\n\n"
        if i < turns - 1:
            time.sleep(pause_seconds)

    data["messages"] = messages
    data["participants"] = list({m.get("speaker") for m in messages if m.get("speaker")})
    CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)
    save_json(GENERAL_CONV_FILE, data)
    yield f"data: {json.dumps({'type': 'done'})}\n\n"


# --- Gaurav exact flow: his personas, history file, bidding, Anthropic Claude stream ---

def _gaurav_format_history(history_path: Path, turns: int = 10) -> str:
    """Same as utils.format_history_as_string: last N lines from conversational_history.txt, 'Role: content\\n'."""
    if not history_path.exists():
        return "No history found."
    formatted = []
    try:
        with open(history_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in lines[-turns:]:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                role = entry.get("role", "Unknown").capitalize()
                content = entry.get("content", "")
                formatted.append(f"{role}: {content}")
            except json.JSONDecodeError:
                continue
    except OSError:
        return "No history found."
    return "\n".join(formatted) if formatted else "No history found."


def _gaurav_stream_one_agent(person_name: str, role: str, history_path: Path, sys_prompt_path: Path, persona_path: Path):
    """
    Same as agent_*.py: load persona + sys_prompt, format history, Anthropic Claude stream.
    Yields (role, delta, is_final) for each chunk then (role, full_text, True).
    """
    import os
    import re

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        yield (role, "[ANTHROPIC_API_KEY not set]", True)
        return
    try:
        with open(sys_prompt_path, "r", encoding="utf-8") as f:
            action_prompt = f.read()
        with open(persona_path, "r", encoding="utf-8") as f:
            persona_prompt = f.read()
    except OSError:
        yield (role, "[Could not read prompt files]", True)
        return

    sys_prompt = persona_prompt + action_prompt
    conversation_hist = _gaurav_format_history(history_path, turns=10)

    full_text = ""
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        with client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=sys_prompt,
            messages=[{"role": "user", "content": conversation_hist}],
        ) as stream:
            for text in stream.text_stream:
                full_text += text
                yield (role, text, False)
    except Exception as e:
        full_text = f"[Error: {e}]"
        yield (role, full_text, True)
        return

    # Clean response: strip leading "Name: " like agent_*.py
    full_text = re.sub(r"^[^:\n]+\s*:\s*", "", full_text, count=1)
    full_text = (full_text or "").strip() or "(no response)"
    yield (role, full_text, True)


def _gaurav_replay_stream_generator(pause_seconds: float = 5):
    """
    Replay conversational_history.txt: stream every message with pause_seconds between each.
    No API calls - just read the file and emit message_start, chunk, message_end, then sleep.
    """
    import time

    if not GAURAV_HISTORY_FILE.exists():
        yield f"data: {json.dumps({'type': 'error', 'detail': 'conversational_history.txt not found'})}\n\n"
        return

    messages = []
    try:
        with open(GAURAV_HISTORY_FILE, "r", encoding="utf-8") as f:
            raw = f.read()
        # Some lines have multiple JSONs separated by "} {" - split and parse each
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            for i, part in enumerate(line.split("} {")):
                s = part.strip()
                if i > 0:
                    s = "{" + s
                if not s.endswith("}"):
                    s += "}"
                try:
                    entry = json.loads(s)
                    role = entry.get("role", "").strip()
                    content = (entry.get("content") or "").strip()
                    if role and content:
                        messages.append({"role": role, "content": content})
                except json.JSONDecodeError:
                    continue
    except OSError:
        yield f"data: {json.dumps({'type': 'error', 'detail': 'Could not read conversational_history.txt'})}\n\n"
        return

    if not messages:
        yield f"data: {json.dumps({'type': 'error', 'detail': 'No messages in conversational_history.txt'})}\n\n"
        return

    for i, msg in enumerate(messages):
        role = msg.get("role", "Unknown")
        text = msg.get("content", "")
        yield f"data: {json.dumps({'type': 'message_start', 'speaker': role})}\n\n"
        yield f"data: {json.dumps({'type': 'chunk', 'speaker': role, 'delta': text})}\n\n"
        yield f"data: {json.dumps({'type': 'message_end', 'speaker': role, 'text': text})}\n\n"
        if i < len(messages) - 1:
            time.sleep(pause_seconds)

    yield f"data: {json.dumps({'type': 'done'})}\n\n"


def _gaurav_stream_generator(max_rounds: int = 15, pause_seconds: float = 3):
    """
    Exact run.py flow: credits (30 each), random bid, winner speaks (winner != init_person),
    stream reply via Anthropic Claude token-by-token, append to conversational_history.txt,
    then sleep(pause_seconds). Same as Gaurav but with Anthropic instead of Groq.
    """
    if not GAURAV_PERSON_BUILDER.exists() or not GAURAV_HISTORY_FILE.exists():
        yield f"data: {json.dumps({'type': 'error', 'detail': 'Gaurav folder not found (Agentic_social_gaurav with conversational_history.txt)'})}\n\n"
        return

    sys_prompt_path = GAURAV_PERSON_BUILDER / "sys_prompt.txt"
    if not sys_prompt_path.exists():
        yield f"data: {json.dumps({'type': 'error', 'detail': 'sys_prompt.txt not found in Personal_builder'})}\n\n"
        return

    credits_left = {k: GAURAV_INITIAL_CREDITS for k in GAURAV_PERSON_ROLE}
    init_person = None
    try:
        with open(GAURAV_HISTORY_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if lines:
            last = lines[-1].strip()
            if last:
                entry = json.loads(last)
                init_person = GAURAV_ROLE_PERSON.get(entry.get("role"))
    except (OSError, json.JSONDecodeError):
        pass
    if init_person is None:
        init_person = list(GAURAV_PERSON_ROLE.keys())[0]

    import random

    round_count = 0
    while round_count < max_rounds and any(credits_left[k] > 0 for k in credits_left):
        random_numbers = {}
        for key in GAURAV_PERSON_ROLE:
            random_numbers[key] = random.randint(1, credits_left[key]) if credits_left[key] > 0 else 0
        if all(v == 0 for v in random_numbers.values()):
            break

        selected_person = max(random_numbers, key=random_numbers.get)
        winning_bid = random_numbers[selected_person]
        if winning_bid <= 0 or selected_person == init_person:
            round_count += 1
            continue

        credits_left[selected_person] -= winning_bid
        role = GAURAV_PERSON_ROLE[selected_person]
        persona_path = GAURAV_PERSON_BUILDER / f"{selected_person}_persona_prompt.txt"
        if not persona_path.exists():
            round_count += 1
            continue

        yield f"data: {json.dumps({'type': 'message_start', 'speaker': role})}\n\n"
        full_message = ""
        for r, chunk, is_final in _gaurav_stream_one_agent(
            selected_person, role, GAURAV_HISTORY_FILE, sys_prompt_path, persona_path
        ):
            if not is_final and chunk:
                full_message += chunk
                yield f"data: {json.dumps({'type': 'chunk', 'speaker': r, 'delta': chunk})}\n\n"
            elif is_final:
                full_message = (chunk or full_message or "").strip() or "(no response)"

        with open(GAURAV_HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps({"role": role, "content": full_message}) + "\n")

        yield f"data: {json.dumps({'type': 'message_end', 'speaker': role, 'text': full_message})}\n\n"
        init_person = selected_person
        round_count += 1
        if round_count < max_rounds and any(credits_left[k] > 0 for k in credits_left):
            import time
            time.sleep(pause_seconds)

    yield f"data: {json.dumps({'type': 'done'})}\n\n"


@app.get("/api/conversations/general/stream")
async def stream_general_conversation(turns: int = 15, pause_seconds: float = 3, replay: bool = False):
    """
    Stream General chat (SSE). Default: generate live via Anthropic Claude (token-by-token streaming).
    If replay=true and conversational_history.txt exists, replays that file with pause_seconds between messages.
    """
    def gen():
        if replay and GAURAV_HISTORY_FILE.exists():
            for chunk in _gaurav_replay_stream_generator(pause_seconds=pause_seconds):
                yield chunk
        elif GAURAV_PERSON_BUILDER.exists() and GAURAV_HISTORY_FILE.exists():
            for chunk in _gaurav_stream_generator(max_rounds=turns, pause_seconds=pause_seconds):
                yield chunk
        else:
            for chunk in _general_stream_generator(turns, pause_seconds=pause_seconds):
                yield chunk

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@app.get("/api/profile")
async def get_profile():
    """Get current user profile (for display name in human chat)."""
    data = load_json(PROFILE_FILE, default={})
    return data


@app.post("/api/profile")
async def post_profile(body: dict):
    """Save current user profile (e.g. from questionnaire)."""
    save_json(PROFILE_FILE, body)
    return {"status": "saved"}


def _claude_reply(recent_messages: list[dict]) -> str | None:
    """Get a short reply from Claude given recent conversation."""
    import os
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        lines = []
        for m in recent_messages[-10:]:
            lines.append(f"{m.get('speaker', '?')}: {m.get('text', '')}")
        prompt = "Recent chat:\n" + "\n".join(lines) + "\n\nReply briefly as a friendly AI assistant (1-3 sentences). No markdown."
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        if msg.content and len(msg.content) > 0:
            text = getattr(msg.content[0], "text", None) or (msg.content[0].get("text") if isinstance(msg.content[0], dict) else "")
            return (text or "").strip()
    except Exception:
        pass
    return None


@app.post("/api/conversations/human")
async def post_conversation_human(body: HumanMessage):
    """Append user message and optionally Claude reply. Each message has id and reactions."""
    from datetime import datetime

    ensure_human_file()
    data = load_json(HUMAN_CONV_FILE, default={"messages": []})
    if "messages" not in data:
        data["messages"] = []

    speaker = body.speaker
    if not speaker or not speaker.strip():
        profile = load_json(PROFILE_FILE, default={})
        prof = profile.get("profile", profile)
        speaker = (prof.get("fullName") or prof.get("name") or "Guest").strip() or "Guest"

    for m in data["messages"]:
        if "reactions" not in m:
            m["reactions"] = {}
        if "id" not in m:
            m["id"] = data["messages"].index(m)

    user_msg = {
        "id": len(data["messages"]),
        "speaker": speaker,
        "text": body.text,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "reactions": {},
    }
    data["messages"].append(user_msg)

    reply = _claude_reply(data["messages"])
    if reply:
        claude_msg = {
            "id": len(data["messages"]),
            "speaker": "Claude",
            "text": reply,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "reactions": {},
        }
        data["messages"].append(claude_msg)

    save_json(HUMAN_CONV_FILE, data)
    return {"status": "success", "messages": data["messages"]}


@app.post("/api/conversations/human/react")
async def post_human_react(body: ReactBody):
    """Add or increment an emoji reaction on a message."""
    ensure_human_file()
    data = load_json(HUMAN_CONV_FILE, default={"messages": []})
    messages = data.get("messages", [])
    if body.message_id < 0 or body.message_id >= len(messages):
        raise HTTPException(status_code=400, detail="Invalid message_id")
    msg = messages[body.message_id]
    if "reactions" not in msg:
        msg["reactions"] = {}
    msg["reactions"][body.emoji] = msg["reactions"].get(body.emoji, 0) + 1
    save_json(HUMAN_CONV_FILE, data)
    return {"status": "ok", "reactions": msg["reactions"]}


@app.post("/api/connection-requests")
async def post_connection_request(body: ConnectionRequestBody):
    """Store a connection request (to match name)."""
    requests = load_json(CONNECTION_REQUESTS_FILE, default=[])
    requests.append({"to": body.to, "status": "pending"})
    save_json(CONNECTION_REQUESTS_FILE, requests)
    return {"status": "sent", "to": body.to}


@app.delete("/api/conversations/human")
async def delete_conversation_human():
    """Clear all messages in human.json."""
    ensure_human_file()
    save_json(HUMAN_CONV_FILE, {"messages": []})
    return {"status": "cleared"}


@app.get("/api/matches")
async def get_matches():
    """Read matches.json; return array sorted by score descending."""
    data = load_json(MATCHES_FILE, default=[])
    if isinstance(data, dict):
        data = data.get("matches", data.get("data", []))
    if not isinstance(data, list):
        data = []
    return sorted(data, key=lambda m: m.get("score", 0), reverse=True)


@app.get("/api/questions")
async def get_questions():
    """Return list of voice interview questions (from QUESTIONS.md or default list)."""
    questions_path = BASE_DIR.parent / "QUESTIONS.md"
    if questions_path.exists():
        text = questions_path.read_text(encoding="utf-8")
        questions = [
            line[2:].strip() for line in text.splitlines()
            if line.strip().startswith("- ") and not line.strip().startswith("- <!--")
        ]
        if questions:
            return {"questions": questions}
    # Default list if file missing
    return {
        "questions": [
            "If a crystal ball could tell you the truth about yourself, your life, or the future, what would you want to know?",
            "I see myself as someone who is curious about many different things—how strongly do you agree with this?",
            "Can you name four qualities about yourself you are proud of? Why?",
            "What is an activity that makes you lose track of time?",
            "What subjects, current events, or causes are you passionate about?",
            "What's something you never thought you'd be able to do, until you actually did it?",
        ]
    }


class TranscribeBody(BaseModel):
    """Base64-encoded audio (e.g. from browser MediaRecorder)."""
    audio_base64: str


@app.post("/api/transcribe")
async def transcribe_audio(body: TranscribeBody):
    """Transcribe audio to text using ElevenLabs STT. Send JSON: {"audio_base64": "..."}."""
    import base64
    import os
    import tempfile

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ELEVENLABS_API_KEY not set")
    try:
        content = base64.b64decode(body.audio_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 audio")
    if not content:
        raise HTTPException(status_code=400, detail="Empty audio")
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        from elevenlabs.client import ElevenLabs
        client = ElevenLabs(api_key=api_key)
        with open(tmp_path, "rb") as f:
            result = client.speech_to_text.convert(file=f, model_id="scribe_v2")
        return {"text": (result.text or "").strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.get("/api/personas")
async def get_personas():
    """List all JSON files in personas/ and return array of persona objects."""
    if not PERSONAS_DIR.exists():
        return []
    out = []
    for p in PERSONAS_DIR.glob("*.json"):
        try:
            out.append(load_json(p, default={}))
        except Exception:
            continue
    return out


PERSONA_FROM_TRANSCRIPT = """Extract a personality profile from this interview transcript.

Transcript:
{text}

Return ONLY valid JSON (no markdown, no explanation):
{{ "name": "person's name", "interests": ["interest1", "interest2", "interest3"], "communication_style": "description", "personality_summary": "2-3 sentence summary", "top_topics": ["topic1", "topic2", "topic3"], "seeking": "what they want to find/meet" }}"""

PERSONA_FROM_PROFILE = """From this user profile (questionnaire), create a personality profile for an AI twin.

Profile:
{text}

Return ONLY valid JSON (no markdown, no explanation):
{{ "name": "person's full name", "interests": ["interest1", "interest2", "interest3"], "communication_style": "description", "personality_summary": "2-3 sentence summary", "top_topics": ["topic1", "topic2", "topic3"], "seeking": "what they want to find/meet" }}"""


def _call_claude_for_persona(prompt_text: str) -> dict:
    import os
    from anthropic import Anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not set")
    client = Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt_text}],
    )
    text = ""
    if msg.content and len(msg.content) > 0:
        block = msg.content[0]
        text = getattr(block, "text", None) or (block.get("text") if isinstance(block, dict) else "") or ""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Claude returned invalid JSON")


@app.post("/api/create-persona")
async def create_persona(body: CreatePersonaBody):
    """Create a persona from profile + optional voice interview conversation."""
    from datetime import datetime

    profile = body.profile or {}
    conversation = body.conversation

    if conversation and len(conversation) > 0:
        lines = []
        for turn in conversation:
            q = turn.get("question", "")
            a = turn.get("answer", "")
            lines.append(f"Q: {q}\nA: {a}")
        text = "\n\n".join(lines)
        prompt = PERSONA_FROM_TRANSCRIPT.format(text=text)
    else:
        text = json.dumps(profile, indent=2)
        prompt = PERSONA_FROM_PROFILE.format(text=text)

    persona = _call_claude_for_persona(prompt)
    for key in ("name", "interests", "communication_style", "personality_summary", "top_topics", "seeking"):
        if key not in persona:
            persona[key] = "" if key != "interests" else []
    persona["created_at"] = datetime.utcnow().isoformat() + "Z"
    persona["source"] = "interview" if conversation else "questionnaire"

    name = (persona.get("name") or "unknown").strip()
    safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in name).strip() or "persona"
    PERSONAS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PERSONAS_DIR / f"{safe_name}.json"
    save_json(out_path, persona)
    return {"status": "created", "path": str(out_path.name), "persona": persona}


def ensure_human_file():
    """Create conversations/human.json with empty messages if it doesn't exist."""
    if not HUMAN_CONV_FILE.exists():
        CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)
        save_json(HUMAN_CONV_FILE, {"messages": []})


# --- Frontend (serve static app at /) ---

STATIC_DIR = BASE_DIR / "static"


@app.get("/")
async def serve_frontend():
    """Serve the Proxy frontend."""
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend not found")
    return FileResponse(index_path)


@app.get("/profile")
async def serve_profile():
    """Serve the profile/questionnaire page."""
    profile_path = STATIC_DIR / "profile.html"
    if not profile_path.exists():
        raise HTTPException(status_code=404, detail="Profile page not found")
    return FileResponse(profile_path)


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# --- Startup ---

@app.on_event("startup")
async def startup():
    ensure_human_file()
    print("🚀 Proxy AI Backend Running")
    print("🌐 App:  http://localhost:8000")
    print("📖 Docs: http://localhost:8000/docs")
    print("🎯 Health: http://localhost:8000/health")
