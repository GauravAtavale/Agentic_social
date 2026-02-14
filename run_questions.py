#!/usr/bin/env python3
"""
Voice Q&A: questions spoken via ElevenLabs TTS, you answer by voice; answers
transcribed with ElevenLabs STT. Conversation saved to conversation.json
and optional audio in conversation_audio/.
Usage: python run_questions.py
Requires: ELEVENLABS_API_KEY in .env
"""

import json
import os
import sys
import tempfile
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

QUESTIONS_FILE = Path(__file__).parent / "QUESTIONS.md"
BASE_DIR = Path(__file__).parent
# CONVERSATION_FILE and AUDIO_DIR set in main() from session number

# Recording
SAMPLE_RATE = 44100
CHANNELS = 1
MAX_RECORD_SECONDS = 90
stop_recording = False
recorded_frames = []


def get_client():
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        print("Set ELEVENLABS_API_KEY in .env", file=sys.stderr)
        sys.exit(1)
    from elevenlabs.client import ElevenLabs
    return ElevenLabs(api_key=api_key)


def load_questions():
    text = QUESTIONS_FILE.read_text(encoding="utf-8")
    questions = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("- "):
            questions.append(line[2:].strip())
    return questions


def speak(client, text):
    """Speak text via ElevenLabs (no text printed)."""
    from elevenlabs.play import play
    audio = client.text_to_speech.convert(
        text=text,
        voice_id="EST9Ui6982FZPSi7gCHi",
        model_id="eleven_multilingual_v2",
    )
    play(audio)


def _record_callback(indata, frames, time_info, status):
    if status:
        print(status, file=sys.stderr)
    if not stop_recording:
        recorded_frames.append(indata.copy())


def record_audio_to_file(path: Path) -> None:
    """Record from mic until user presses Enter. Saves WAV to path."""
    import sounddevice as sd
    import soundfile as sf
    global stop_recording, recorded_frames
    stop_recording = False
    recorded_frames = []

    def wait_for_enter():
        input()
        global stop_recording
        stop_recording = True

    print("  [Speak your answer now. Press Enter when done.]")
    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        blocksize=1024,
        callback=_record_callback,
    )
    stream.start()
    wait_for_enter()
    stream.stop()
    stream.close()

    if not recorded_frames:
        return
    import numpy as np
    audio = np.concatenate(recorded_frames, axis=0)
    sf.write(str(path), audio, SAMPLE_RATE, subtype="PCM_16")


def transcribe(client, wav_path: Path) -> str:
    """Transcribe WAV file with ElevenLabs STT."""
    if wav_path.stat().st_size == 0:
        return ""
    with open(wav_path, "rb") as f:
        result = client.speech_to_text.convert(file=f, model_id="scribe_v2")
    return (result.text or "").strip()


def main():
    # Which personality/session (1–4)? Saves to conv1.json, conv2.json, ...
    while True:
        raw = input("Session number (1, 2, 3, 4, etc.): ").strip()
        if raw.isdigit() and int(raw) >= 1:
            session_num = int(raw)
            break
        print("Enter a number >= 1 (e.g. 1 for conv1.json, 2 for conv2.json)")
    conversation_file = BASE_DIR / f"conv{session_num}.json"
    audio_dir = BASE_DIR / f"conversation_audio_{session_num}"

    client = get_client()
    questions = load_questions()
    if not questions:
        print("No questions in QUESTIONS.md")
        return

    audio_dir.mkdir(parents=True, exist_ok=True)
    conversation = []

    for i, q in enumerate(questions):
        print(f"\n--- Question {i + 1}/{len(questions)} ---")
        speak(client, q)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            record_audio_to_file(tmp_path)
            if tmp_path.exists() and tmp_path.stat().st_size > 0:
                save_path = audio_dir / f"answer_{i + 1:02d}.wav"
                save_path.parent.mkdir(parents=True, exist_ok=True)
                save_path.write_bytes(tmp_path.read_bytes())
            answer_text = transcribe(client, tmp_path) if tmp_path.exists() and tmp_path.stat().st_size > 0 else ""
        finally:
            tmp_path.unlink(missing_ok=True)

        print(f"  You said: {answer_text or '(no speech detected)'}")
        conversation.append({"question": q, "answer": answer_text})
        # Save after each answer so nothing is lost if interrupted
        conversation_file.write_text(json.dumps(conversation, indent=2), encoding="utf-8")
        print(f"  Saved to {conversation_file}")

    print(f"\nDone. Full conversation in {conversation_file}")
    if audio_dir.exists() and any(audio_dir.glob("answer_*.wav")):
        print(f"Answer audio saved in {audio_dir}/")


if __name__ == "__main__":
    main()
