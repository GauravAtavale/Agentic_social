#!/usr/bin/env python3
"""
Script 1: Extract personality profile from an interview transcript using Claude.
Reads interview JSON, sends transcript to Claude, saves persona to personas/{name}.json
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Paths relative to backend/
BASE_DIR = Path(__file__).resolve().parent
PERSONAS_DIR = BASE_DIR / "personas"

PERSONA_PROMPT = """Extract a personality profile from this interview transcript.

Transcript:
{transcript}

Return ONLY valid JSON (no markdown, no explanation):
{{
  "name": "person's name",
  "interests": ["interest1", "interest2", "interest3"],
  "communication_style": "description of how they communicate",
  "personality_summary": "2-3 sentence summary",
  "top_topics": ["topic1", "topic2", "topic3"],
  "seeking": "what they want to find/meet"
}}"""


def load_json(filepath: Path) -> dict | list:
    """Load JSON from file. Raises on error."""
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def build_transcript(conversation: list) -> str:
    """Build a single transcript string from conversation array."""
    lines = []
    for turn in conversation:
        q = turn.get("question", "")
        a = turn.get("answer", "")
        lines.append(f"Q: {q}\nA: {a}")
    return "\n\n".join(lines)


def extract_persona_with_claude(transcript: str) -> dict:
    """Call Claude to extract persona JSON. Validates and returns dict."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)

    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": PERSONA_PROMPT.format(transcript=transcript)}],
        )
    except Exception as e:
        print(f"Error calling Claude API: {e}", file=sys.stderr)
        sys.exit(1)

    # Get text from the first block
    text = ""
    if message.content and len(message.content) > 0:
        block = message.content[0]
        if hasattr(block, "text"):
            text = block.text
        elif isinstance(block, dict) and "text" in block:
            text = block["text"]

    if not text:
        print("Error: Claude returned no text", file=sys.stderr)
        sys.exit(1)

    # Strip markdown code fence if present
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"Error: Claude response was not valid JSON: {e}", file=sys.stderr)
        print("Raw response:", text[:500], file=sys.stderr)
        sys.exit(1)

    # Basic validation
    required = ["name", "interests", "communication_style", "personality_summary", "top_topics", "seeking"]
    for key in required:
        if key not in data:
            print(f"Error: Claude response missing required field: {key}", file=sys.stderr)
            sys.exit(1)

    return data


def main():
    if len(sys.argv) < 2:
        print("Usage: python create_persona.py interviews/<interview_file>.json", file=sys.stderr)
        sys.exit(1)

    interview_path = Path(sys.argv[1])
    if not interview_path.is_absolute():
        interview_path = BASE_DIR / interview_path

    if not interview_path.exists():
        print(f"Error: File not found: {interview_path}", file=sys.stderr)
        sys.exit(1)

    # Load interview
    try:
        interview = load_json(interview_path)
    except Exception as e:
        print(f"Error reading interview: {e}", file=sys.stderr)
        sys.exit(1)

    conversation = interview.get("conversation", [])
    if not conversation:
        print("Error: interview has no 'conversation' array", file=sys.stderr)
        sys.exit(1)

    transcript = build_transcript(conversation)
    persona = extract_persona_with_claude(transcript)

    # Add metadata
    from datetime import datetime

    persona["created_at"] = datetime.utcnow().isoformat() + "Z"
    persona["source_interview"] = str(interview_path.name)

    # Sanitize filename from name
    name = persona.get("name", "unknown").strip()
    safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in name).strip() or "persona"

    PERSONAS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PERSONAS_DIR / f"{safe_name}.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(persona, f, indent=2, ensure_ascii=False)

    print(f"Success! Persona saved to {out_path}")


if __name__ == "__main__":
    main()
