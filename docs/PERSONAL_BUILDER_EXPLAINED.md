# Personal_builder Directory Explained

This document walks through **`Personal_builder/`** and what happens when you run **`run.py`**.

---

## 1. What Personal_builder does

**Personal_builder** is a **multi-agent conversation simulator** with a **bidding system**:

- Several **personas** (Gaurav, Anagha, Kanishkha, Nirbhay) each have a fixed number of **credits**.
- Each round, each persona (with credits > 0) **bids** for the right to speak next. The bid is decided by an **LLM** (Claude or LLaMA) based on how relevant the current conversation is to that persona.
- The **highest bidder** “wins” the turn: their credits are reduced by their bid, and they generate the next message (again via LLM) and append it to a shared **conversation history** file.
- The loop continues until **no one has credits left** (or everyone’s bid is 0).

So: **initiation** is `run.py`; **bidding** uses `utils.py` + `bidding_sys_prompt.txt`; **speaking** is done by the `agent_*.py` scripts, which use `utils.py`, `sys_prompt.txt`, and `*_persona_prompt.txt`.

---

## 2. File layout and roles

| File / folder | Role |
|---------------|------|
| **`run.py`** | Entry point. Bidding loop: who speaks next, deduct credits, then `exec(agent_*.py)`. |
| **`utils.py`** | Shared helpers: read/format conversation history, call Claude/Groq for bidding and for agent replies. |
| **`bidding_sys_prompt.txt`** | System prompt for the **bidding** LLM: “Score 0–100 how much you want to speak now”; output must be `{"score": N}`. |
| **`sys_prompt.txt`** | Short instruction for **speaking**: stay in character, continue the conversation, ~50 words. |
| **`*_persona_prompt.txt`** | Per-persona prompt (e.g. “You are Gaurav Atavale, 20 yo AI researcher…”). Combined with `sys_prompt.txt` when that agent speaks. |
| **`agent_Gaurav.py`**, **`agent_Anagha.py`**, … | One script per persona. When executed, they read history, call the LLM once, append one message to `../conversational_history.txt`. |
| **`persona_prompt_builder.py`** | Utility: turns a persona JSON into a text prompt (e.g. for building `*_persona_prompt.txt`). Not used by `run.py` at runtime. |
| **`*.json`** (e.g. `Gaurav_Atavale.json`) | Persona data; can be input to `persona_prompt_builder.py`. |
| **`conversational_history.txt`** | In this repo it lives inside `Personal_builder/`; `run.py` and agents expect it at **`../conversational_history.txt`** (parent of `Personal_builder`). So when run from `Personal_builder/`, the history file is expected at repo root. |
| **`basic_agent.py`**, **`run_old.py`** | Older/simpler variants (e.g. random bids in `run_old.py`); not the main flow. |

---

## 3. Step-by-step: what happens when you run `run.py`

**Assumption:** You run from the **`Personal_builder/`** directory (or with `Personal_builder` on the path so that `../conversational_history.txt` is the parent folder’s history file).

### 3.1 Setup (top of `run.py`)

- **Person–role mapping:**  
  `person_role_dict = {"Gaurav_Atavale": "Gaurav", "Anagha_Palandye": "Anagha", …}`  
  and `role_person_dict` for role → person.
- **Agent scripts:**  
  `file_names_dict = {"Gaurav_Atavale": "agent_Gaurav.py", …}`.
- **Who spoke last:**  
  Reads the **last line** of `../conversational_history.txt`, parses JSON, gets `role`, and sets `init_person = role_person_dict[role]` so the same person doesn’t automatically “win” again by being last.
- **Credits:**  
  `credits_left = {key: 100 for key in person_role_dict}` (everyone starts with 100).

### 3.2 Main loop: “while anyone has credits”

1. **Bid for each person (with credits > 0)**  
   For each persona that still has credits, `utils.generate_bid_score_each_user(person_name, credits_left, model)` is called:
   - Reads that person’s **persona prompt** from `{person_name}_persona_prompt.txt`.
   - Reads last N turns from `../conversational_history.txt` and formats them (e.g. “Gaurav: …\nAnagha: …”).
   - Reads **`bidding_sys_prompt.txt`** and injects current credits (e.g. replaces `||` with `credits_left[person_name]` in `utils.py`).
   - Sends to the LLM (Claude first; on failure, LLaMA via Groq). The LLM is asked to return **only** `{"score": <0–100>}`.
   - Effective bid for that person: `0.01 * score * credits_left[person_name]` (so bid is a percentage of current credits).
   - If a person has 0 credits, their bid is 0.

2. **If all bids are 0**  
   Loop breaks (“Game over”).

3. **Choose winner**  
   `selected_person = max(random_numbers, key=random_numbers.get)` (highest bid).

4. **Rule: winner must not be the same as last speaker**  
   - If `selected_person == init_person`, the code instead picks the **second-highest** bidder as `selected_person` and uses their bid.
   - So the previous speaker never gets the turn immediately again.

5. **Deduct credits**  
   `credits_left[selected_person] -= winning_bid` (capped so it doesn’t go below 0).

6. **Winner speaks**  
   `exec(open(file_names_dict[selected_person]).read())`:
   - That script (e.g. `agent_Gaurav.py`) runs in the same process.
   - It loads `sys_prompt.txt` and `{person_name}_persona_prompt.txt`, concatenates them as the system prompt.
   - It gets the last 10 turns from `../conversational_history.txt` via `utils.format_history_as_string(10)`.
   - It calls `utils.agent_sim(model, sys_prompt, conversation_hist_format)` (Claude or Groq) to generate one reply.
   - It strips a leading “Name: ” from the reply (if present), then appends one line to `../conversational_history.txt`:  
     `{"role": "<display name>", "content": "<text>"}`.
   - Then it exits (control back to `run.py`).

7. **Update “last speaker”**  
   `init_person = selected_person` so the next round enforces “winner ≠ last speaker” again.

8. **Repeat** until no one has credits or all bids are 0.

So in one sentence: **`run.py` repeatedly has each persona bid (via LLM), picks the highest bidder (excluding the last speaker), deducts their bid from their credits, then runs the corresponding `agent_*.py` which generates one message and appends it to the shared history file.**

---

## 4. How `utils.py` supports this

- **`format_history_as_string(turns=10)`**  
  Reads `../conversational_history.txt`, takes the last `turns` lines, parses each as JSON, and returns a string like `"Gaurav: ...\nAnagha: ...\n"`.

- **`generate_bid_score_each_user(person_name, credits_left, model_LLM)`**  
  Builds the bidding prompt (persona + history + bidding instructions with current credits), calls `agent_sim(...)`, parses the response as JSON, and returns the string (e.g. `'{"score": 75}'`). The caller in `run.py` then does `int(0.01 * score * credits_left[key])` to get the actual bid.

- **`agent_sim(model_LLM, plan_sys_prompt, user_query)`**  
  Generic LLM call: if the model name starts with `claude`, uses **Anthropic**; if it starts with `llama` or `meta`, uses **Groq**. Uses `plan_sys_prompt` as system prompt and `user_query` as user message. For Groq it streams and concatenates chunks; for Claude it uses the first content block’s text. **Note:** API keys are currently hardcoded in `utils.py` (and in `basic_agent.py`); they should be moved to env vars.

---

## 5. Agent scripts (e.g. `agent_Gaurav.py`)

Each **`agent_<Role>.py`** is almost identical; only the **person name** (and thus the persona file and role label) change:

1. Set `person_name` (e.g. `"Gaurav_Atavale"`) and `role` (e.g. `"Gaurav"`).
2. Read `sys_prompt.txt` and `{person_name}_persona_prompt.txt`; concatenate → full system prompt.
3. Get last 10 turns: `conversation_hist_format = utils.format_history_as_string(turns=10)`.
4. Call `utils.agent_sim(init_model, sys_prompt, conversation_hist_format)` to get one reply.
5. Strip a leading `"Name: "` (or similar) from the reply with a regex.
6. Append one line to `../conversational_history.txt`: `{"role": role, "content": agent_resp}`.

So when `run.py` does `exec(open("agent_Gaurav.py").read())`, it doesn’t “call a function”; it **runs the script**, which performs one LLM call and one file append, then exits.

---

## 6. Data flow summary

```
run.py
  │
  ├─► Read ../conversational_history.txt → last speaker → init_person
  ├─► credits_left = { everyone: 100 }
  │
  └─► while any(credits_left > 0):
        │
        ├─► For each person with credits > 0:
        │     utils.generate_bid_score_each_user(...)
        │       ├─► Read *_persona_prompt.txt, bidding_sys_prompt.txt
        │       ├─► format_history_as_string(10)
        │       └─► LLM → {"score": 0–100}  →  bid = 0.01 * score * credits
        │
        ├─► If all bids 0 → break
        ├─► Winner = max bidder (or second-highest if winner == init_person)
        ├─► credits_left[winner] -= bid
        ├─► exec(open(agent_<Winner>.py).read())
        │     │
        │     └─► agent_*.py:
        │           sys_prompt + persona_prompt → LLM(history) → one reply
        │           Append {"role", "content"} to ../conversational_history.txt
        │
        └─► init_person = winner
```

---

## 7. Important details

- **Paths:** All history reads/writes use **`../conversational_history.txt`**. So when you run from `Personal_builder/`, the history file is in the **parent** of `Personal_builder` (in this repo, that would be the repo root). The copy inside `Personal_builder/conversational_history.txt` is likely a local snapshot or seed; the “live” file for a run is the one in the parent.
- **API keys:** `utils.py` and `basic_agent.py` contain hardcoded Anthropic and Groq API keys. These should be moved to environment variables (e.g. `.env`) and loaded at runtime.
- **No backend dependency:** `run.py` and the agent scripts do not import the main app; they are a **standalone** simulation. The **backend** (`backend/main.py`) can reimplement a similar flow when it finds an `Agentic_social_gaurav` folder (with its own `Personal_builder` and `conversational_history.txt`); it does not run this repo’s `Personal_builder/run.py` directly.

This is the full picture of what is happening in **Personal_builder**, with **run.py** as the initiation code.
