#!/usr/bin/env python3
"""
Script 2: Generate AI group conversations (Sports, AI, Tech) and match scores.
Loads all personas, picks 3 per group, generates 10-message conversations, then match scores.
"""

import json
import os
import random
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
PERSONAS_DIR = BASE_DIR / "personas"
CONVERSATIONS_DIR = BASE_DIR / "conversations"

GROUP_TOPICS = {
    "Sports": "favorite sports teams and recent games",
    "AI": "latest developments in AI and machine learning",
    "Tech": "new technology trends and products",
}

NUM_MESSAGES = 10
MODEL = "claude-sonnet-4-20250514"


def load_json(filepath: Path) -> dict | list:
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def save_json(filepath: Path, data: dict | list) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_all_personas() -> list[dict]:
    """Load every JSON file in personas/."""
    if not PERSONAS_DIR.exists():
        return []
    personas = []
    for p in PERSONAS_DIR.glob("*.json"):
        try:
            personas.append(load_json(p))
        except Exception as e:
            print(f"Warning: skip {p}: {e}")
    return personas


def system_prompt_for_persona(persona: dict, group: str, topic: str) -> str:
    return f"""You are {persona.get('name', 'Unknown')}. Your personality: {persona.get('personality_summary', '')}
Interests: {persona.get('interests', [])}
Communication style: {persona.get('communication_style', '')}

You're in a {group} group chat discussing {topic}.
Respond naturally in your style. Keep responses 1-2 sentences. Do not break character."""


def get_client():
    from anthropic import Anthropic

    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("Error: ANTHROPIC_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)
    return Anthropic(api_key=key)


def generate_one_message(
    client, group: str, topic: str, personas: list[dict], persona_index: int, history: list[dict]
) -> str:
    """Generate the next message from persona at persona_index."""
    persona = personas[persona_index]
    name = persona.get("name", "Unknown")
    sys_prompt = system_prompt_for_persona(persona, group, topic)

    history_text = "\n".join(
        f"{m['speaker']}: {m['text']}" for m in history
    )

    user_content = f"Conversation so far:\n{history_text}\n\nYour turn. Reply as {name} (1-2 sentences only):"

    try:
        msg = client.messages.create(
            model=MODEL,
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
    return text.strip() or "(no response)"


def generate_group_conversation(client, group: str, personas: list[dict]) -> dict:
    """Generate a 10-message conversation for one group."""
    topic = GROUP_TOPICS[group]
    messages = []
    # Round-robin: 0, 1, 2, 0, 1, 2, ...
    for i in range(NUM_MESSAGES):
        idx = i % 3
        name = personas[idx].get("name", "Unknown")
        text = generate_one_message(client, group, topic, personas, idx, messages)
        messages.append({
            "speaker": name,
            "text": text,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })
    return {
        "group": group,
        "topic": topic,
        "participants": [p.get("name", "Unknown") for p in personas],
        "messages": messages,
    }


def generate_matches(client, personas: list[dict]) -> list[dict]:
    """Compute match score for each unique pair of personas."""
    from itertools import combinations

    matches = []
    for a, b in combinations(personas, 2):
        name_a = a.get("name", "A")
        name_b = b.get("name", "B")
        prompt = f"""Rate compatibility 0-100 between these two people based on their personalities.

Person A: {json.dumps({k: v for k, v in a.items() if k not in ('created_at', 'source_interview')})}
Person B: {json.dumps({k: v for k, v in b.items() if k not in ('created_at', 'source_interview')})}

Return ONLY valid JSON:
{{"score": number, "reason": "1 sentence explanation"}}"""

        try:
            msg = client.messages.create(
                model=MODEL,
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as e:
            matches.append({"user_a": name_a, "user_b": name_b, "score": 0, "reason": str(e)})
            continue

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
            out = json.loads(text)
            score = int(out.get("score", 0))
            reason = out.get("reason", "")
        except (json.JSONDecodeError, ValueError):
            score, reason = 0, "Parse error"
        matches.append({"user_a": name_a, "user_b": name_b, "score": score, "reason": reason})

    return sorted(matches, key=lambda m: m["score"], reverse=True)


def main():
    personas = load_all_personas()
    if len(personas) < 3:
        print("Warning: Need at least 3 personas in personas/. Exiting.")
        return

    client = get_client()
    CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)

    for group in ["Sports", "AI", "Tech"]:
        print(f"Generating {group} conversation... ", end="", flush=True)
        selected = random.sample(personas, 3)
        conv = generate_group_conversation(client, group, selected)
        out_path = CONVERSATIONS_DIR / f"{group.lower()}.json"
        save_json(out_path, conv)
        print("Done!")

    print("Generating match scores... ", end="", flush=True)
    matches = generate_matches(client, personas)
    save_json(BASE_DIR / "matches.json", matches)
    print("Done!")


if __name__ == "__main__":
    main()
