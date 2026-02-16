# Agentic Social

An **AI-powered social networking simulator** where multiple AI personas engage in group conversations using a bidding system. Each persona bids (via LLM scoring) for the right to speak next, creating dynamic multi-agent interactions.

---

## 🏗️ Project Structure

```
Agentic_social/
├── backend/              # FastAPI server + multi-agent simulation
│   ├── server.py        # Web server (world_chat UI)
│   ├── run.py           # Main simulation loop (bidding + agents)
│   ├── utils.py         # LLM helpers (Anthropic, Groq)
│   ├── agent_*.py       # Individual persona scripts
│   ├── simulation_stream.py  # Streaming version for web
│   └── run_web.py       # Entry point to start server
│
├── frontend/            # Web UI (static HTML/CSS/JS)
│   ├── index.html       # world_chat interface
│   ├── app.js           # SSE client for live updates
│   └── styles.css       # Styling
│
├── scripts/             # Utility scripts
│   ├── run_questions.py # Voice interview (ElevenLabs TTS/STT)
│   └── run_old_personal_builder.py  # Legacy simulation
│
├── config/              # Configuration files
│   ├── sys_prompt.txt   # System prompt for agents
│   ├── bidding_sys_prompt.txt  # Bidding prompt
│   ├── *_persona_prompt.txt    # Per-persona prompts
│   └── .env.example     # Environment variables template
│
├── data/                # Data files
│   ├── conversational_history.txt  # Conversation log (one JSON per line)
│   ├── *_*.json         # Persona data files
│   └── old_convo.txt    # Legacy conversation
│
├── docs/                # Documentation
│   ├── README.md        # Original README
│   ├── QUESTIONS.md      # Interview questions
│   ├── README_WEB.md     # Web UI documentation
│   └── *.ipynb          # Jupyter notebooks
│
├── requirements.txt     # Python dependencies
├── .gitignore
└── README.md            # This file
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Keys

Create `config/.env` (or copy from `config/.env.example`):

```bash
ANTHROPIC_API_KEY=your_anthropic_key_here
GROQ_API_KEY=your_groq_key_here
ELEVENLABS_API_KEY=your_elevenlabs_key_here  # For voice interview script
```

### 3. Run the Web App

```bash
# From repo root
python backend/run_web.py --free-port

# Or from backend/
cd backend
python run_web.py --free-port
```

Open **http://localhost:8001** to see the **world_chat** interface.

The server automatically starts `run.py` in the background, which runs the bidding simulation and writes to `data/conversational_history.txt`. New messages appear in the UI in real time via Server-Sent Events (SSE).

---

## 📖 How It Works

### Multi-Agent Bidding System

1. **Four personas** (Gaurav, Anagha, Kanishkha, Nirbhay) each start with **100 credits**.
2. Each round, every persona with credits > 0 **bids** for the right to speak next:
   - An **LLM** (Claude or LLaMA via Groq) scores how relevant the conversation is to that persona (0-100).
   - The bid = `0.01 * score * current_credits`.
3. The **highest bidder** wins (excluding the last speaker):
   - Their credits are reduced by their bid.
   - They generate a message via LLM using their persona prompt + conversation history.
   - The message is appended to `data/conversational_history.txt`.
4. The loop continues until **no one has credits left** or all bids are 0.

### Web UI

- **Single view**: `world_chat` shows the full conversation.
- **On load**: Fetches existing history from `data/conversational_history.txt`.
- **Live updates**: Opens an SSE stream (`/api/history/stream`) that polls the history file and pushes new messages as they're written by `run.py`.

---

## 🛠️ Development

### Backend

- **`backend/server.py`**: FastAPI app serving the UI and API endpoints.
- **`backend/run.py`**: Main simulation loop (CLI version).
- **`backend/utils.py`**: LLM helpers (bidding, message generation).
- **`backend/agent_*.py`**: Individual persona scripts (executed by `run.py`).

### Frontend

- **`frontend/index.html`**: Single-page UI.
- **`frontend/app.js`**: Fetches history and consumes SSE stream.
- **`frontend/styles.css`**: Styling.

### Scripts

- **`scripts/run_questions.py`**: Voice interview script (ElevenLabs TTS/STT).

---

## 📁 Key Files

| File | Purpose |
|------|---------|
| `data/conversational_history.txt` | Conversation log (one JSON `{"role": "...", "content": "..."}` per line) |
| `config/sys_prompt.txt` | System prompt for all agents |
| `config/bidding_sys_prompt.txt` | Prompt for LLM bidding |
| `config/*_persona_prompt.txt` | Per-persona descriptions |
| `backend/run.py` | Main simulation (CLI) |
| `backend/server.py` | Web server |

---

## 🔧 Configuration

- **API Keys**: Set in `config/.env` or repo root `.env`.
- **Port**: Default 8001 (change in `backend/server.py`).
- **Credits**: Initial credits per persona (default 100, in `backend/run.py`).
- **Models**: Bidding uses Claude primary, LLaMA fallback; agents use Claude primary, LLaMA fallback.

---

## 📝 Notes

- The **`backup_old`** folder is preserved and not modified.
- Conversation history is written to `data/conversational_history.txt` (one JSON object per line).
- The web server starts `run.py` automatically on startup.
- If you see "Address already in use", use `--free-port` flag or kill the process on port 8001.

---

## 📚 Documentation

- **`docs/README.md`**: Original project documentation.
- **`docs/README_WEB.md`**: Web UI documentation.
- **`docs/QUESTIONS.md`**: Interview questions for voice script.

---

## 🧪 Testing

```bash
# Health check
curl http://localhost:8001/health

# Get conversation history
curl http://localhost:8001/api/history

# Stream new messages (SSE)
curl http://localhost:8001/api/history/stream
```

---

## 📄 License

See LICENSE file (if present).
