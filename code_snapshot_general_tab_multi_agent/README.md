# General Tab Multi-Agent Chat — Code Snapshot

Saved snapshot of the code that simulates multi-agent conversation in the **General** tab (inspired by agentic_social_gaurav).

## What it does

- **Backend:** `POST /api/conversations/general/generate?turns=10` loads personas from `personas/`, takes turns (round-robin), and for each turn calls Claude with that persona’s prompt + last 10 messages, then appends to `conversations/general.json`.
- **Frontend:** General tab shows “Generate conversation (multi-agent)” when empty; clicking it calls the generate endpoint and renders the returned messages.

## Where this code lives in the project

| Snapshot file | Project location |
|---------------|------------------|
| `backend_general_tab.py` | `backend/main.py` — add constant `GENERAL_CONV_FILE`, GET general empty handling, and everything from `_load_personas_list` through `generate_general_conversation` endpoint |
| `frontend_general_tab.js` | `backend/static/app.js` — replace `loadChat()` and add `generateGeneralConversation()` |
| `frontend_general_tab.css` | `backend/static/styles.css` — add after `.empty-msg` |

## Restoring

- Merge the backend block into `backend/main.py` (after the existing `get_conversation_group` and before `@app.get("/api/profile")`).
- Replace the `loadChat` function in `app.js` with the version in the snapshot and add `generateGeneralConversation`.
- Append the CSS in `frontend_general_tab.css` to `styles.css` (after `.empty-msg`).

Saved: 2025-02-14
