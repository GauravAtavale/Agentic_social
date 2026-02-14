"""
Backend additions for General tab multi-agent chat.
Add to backend/main.py:
  1. Constant: GENERAL_CONV_FILE (next to CONNECTION_REQUESTS_FILE).
  2. In get_conversation_group: handle general when file doesn't exist (return empty).
  3. Everything below until @app.get("/api/profile").
"""

# --- Constant (add with other FILE constants) ---
# GENERAL_CONV_FILE = CONVERSATIONS_DIR / "general.json"

# --- In get_conversation_group, before: path = CONVERSATIONS_DIR ... ---
# if group.lower() == "general" and not path.exists():
#     return {"group": "General", "topic": "general chat", "participants": [], "messages": []}

# --- Add these functions and endpoint (before @app.get("/api/profile")) ---

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
