# Agentic Social Simulator

Create a Agentic Social Media Simulator

## Questions script (ElevenLabs, voice-only)

Run the question flow: each question is **spoken** via ElevenLabs TTS (no text). You **answer by voice**; the script records your answer and transcribes it with ElevenLabs STT. The conversation is saved to `conversation.json` and your answer audio files to `conversation_audio/`.

```bash
pip install -r requirements.txt
cp .env.example .env   # add your ELEVENLABS_API_KEY
python run_questions.py
```

For each question: listen to the voice, then speak your answer. When finished, press **Enter**. Repeat for all questions.

## High level things to do
1. Create Profile --> based on Linkedin, Insta etc
2. Gather + Integrate Conversational data | Record convo with eleven labs
3. Chat Persona Building
4. Web app -> Group chat / Human chat / Interest groups


