# CLAUDE.md — Instructions for Claude Code

## What This Project Is

Chitra is an AI-first operating system. The name comes from Chitragupta — the keeper of records in Hindu mythology, the one who remembers every soul's story. The AI is not a feature on top of an OS — it is the OS. There is no GUI, no app launcher, no home screen. The only interface is conversation — voice or text. The AI Orchestration Core is the primary userspace process. It boots directly on Linux and is the only thing the user ever interacts with.

**Read `VISION.md` before writing any code.** It is the north star for every decision. If anything you are asked to build contradicts `VISION.md`, flag the contradiction explicitly before writing code.

---

## The Most Important Rules

**1. No UI except conversation.**
Never introduce buttons, menus, lists, forms, or any navigable interface element. If a feature requires the user to look at options and choose, the design is wrong. Redesign it as a conversational interaction.

**2. No internet calls.**
Phase 1 is entirely local. No HTTP calls to external services, no cloud APIs, no external LLM APIs. Everything runs on device. Ollama runs locally. All data is local. If you find yourself reaching for requests or httpx to call an external URL, stop.

**3. Capabilities never call each other.**
Only the Orchestration Core orchestrates between capabilities. If you find yourself writing code where one capability imports or calls another, stop and route it through the Orchestration Core instead.

**4. The LLM has no persistent state.**
Never rely on the LLM remembering something between calls. All continuity comes from the Memory capability injecting context. Every LLM call must include the full assembled context from Memory and System State.

**5. Linux compatibility is non-negotiable.**
Development is on macOS but the target is Linux. Never use macOS-specific libraries or APIs. Test Linux compatibility in the UTM VM regularly.

**6. The LLM client is a swappable interface.**
The model name must come from the `CHITRA_LLM_MODEL` environment variable — never hardcoded. Swapping the underlying LLM model must require zero code changes. This is a critical requirement because local models are improving rapidly and Chitra must benefit from new models as they emerge.

**7. Robust JSON parsing — never crash on malformed LLM output.**
The LLM does not always return perfectly formed JSON. The Orchestration Core must:
- Wrap all LLM JSON parsing in try/except
- On malformed JSON, retry the LLM call with an explicit correction prompt (maximum 2 retries)
- On persistent failure, fall back to a safe conversational response — never crash
- Log all malformed outputs for debugging

**8. All storage paths come from configuration.**
Never hardcode `/var/chitra/` or `~/.chitra/` or any storage path. Always read from `CHITRA_DATA_DIR` environment variable. Default to `~/.chitra/data/` if not set.

---

## Architecture Summary

Five layers. Read `ARCHITECTURE.md` for full detail.

```
Conversational Interface        ← minimal terminal display, demo visibility only
AI Orchestration Core           ← primary process, boots on startup, never exits
Capability Modules              ← Voice I/O, Contacts, Calendar,
                                   Reminders, Tasks, Memory, System State
Hardware Abstraction            ← audio, storage, system state
Linux Kernel                    ← untouched foundation
```

---

## LLM Prompt Structure

Every LLM call follows this exact structure:

```
System prompt:
  - Chitra identity and behavior instructions
  - Assembled context: Memory context block + System State snapshot
  - Current conversation history (last 10 turns, from CHITRA_HISTORY_TURNS env var)

User message:
  - Current user input OR proactive loop trigger description
```

The LLM must always be instructed to return this exact JSON structure:

```json
{
  "intent": "string describing detected intent",
  "action": {
    "capability": "capability_name",
    "action": "action_name",
    "params": {}
  },
  "response": "conversational response to speak to the user",
  "memory_store": [
    {
      "category": "preference | fact | observation | relationship",
      "subject": "what this memory is about",
      "content": "the memory in plain natural language",
      "confidence": 1.0,
      "source": "stated | inferred"
    }
  ]
}
```

`action` is null if no capability needs to be called.
`memory_store` is an empty array if nothing new should be stored.
The Orchestration Core stores all `memory_store` entries immediately after every successful LLM call.

---

## Capability Rules

Each capability is defined in `CAPABILITIES.md` with its full API contract. When building or modifying capabilities:

- Respect the API contract exactly — inputs and outputs as specified
- Each capability is a self-contained Python class in its own file
- Each capability manages its own SQLite database only — never reads another capability's database
- No capability has a UI of any kind
- All capability errors must be handled gracefully — return structured error JSON, never raise unhandled exceptions
- Validation and field limits live in the capability code — not in architecture documents

---

## Memory Is the Heart of Chitra

The Memory capability is what makes Chitra feel like it knows the user. Treat it with care.

- Every LLM call must include the Memory context block — no exceptions
- New facts, preferences, and observations detected in conversation must be stored immediately via `memory_store` in the LLM response
- Memory informs behavior quietly — Chitra never recites facts back at the user mechanically
- The difference between good and bad memory use:
  - **Wrong:** *"I remember you told me on January 3rd that your mother prefers calls after 7pm."*
  - **Right:** *"It's 8pm — good time to call your mother if you've been meaning to."*
- See `MEMORY_DESIGN.md` for full design

---

## The Proactive Loop

The proactive loop runs as an async background task in the Orchestration Core. It ticks every 60 seconds (from `CHITRA_PROACTIVE_INTERVAL` env var). It is not optional — it is central to the vision.

On every tick:
1. Call `Reminders.get_fired()` — check for triggered reminders
2. Call `Calendar.get_upcoming(hours_ahead=1)` — check for imminent events
3. Call `Contacts.get_neglected(days_threshold=7)` — check for neglected relationships
4. Call `Tasks.get_overdue()` — check for overdue tasks
5. Make a lightweight LLM call with this context — ask: is there anything worth telling the user right now?
6. If yes — formulate a conversational message, call `VoiceIO.speak()`, call `VoiceIO.display()`
7. If no — sleep until next tick

The proactive loop never interrupts an active conversation. Check for an `is_user_active` flag on the Orchestration Core before speaking.

---

## Onboarding Flow

On first run (`~/.chitra/data/` is empty or a `first_run` flag is set), Chitra runs an onboarding conversation before normal operation.

Onboarding asks the user:
- Their name
- Key people in their life and relationships
- Basic work schedule
- Any immediate preferences

Every answer is stored immediately to Memory with confidence 1.0 and source "stated". Onboarding ends with a summary of what Chitra now knows, and normal operation begins.

Onboarding must never be skipped on first run. On subsequent boots it must never appear.

---

## Configuration Reference

All configuration comes from environment variables (`.env` file):

| Variable | Default | Purpose |
|---|---|---|
| `CHITRA_DATA_DIR` | `~/.chitra/data` | Storage directory |
| `CHITRA_LLM_MODEL` | `llama3.1:8b` | Ollama model name |
| `CHITRA_PROACTIVE_INTERVAL` | `60` | Proactive loop tick in seconds |
| `CHITRA_HISTORY_TURNS` | `10` | Conversation turns in LLM context |

---

## What Good Code Looks Like in This Project

- Clean, readable Python with clear docstrings
- Async throughout the Orchestration Core — use asyncio properly
- One capability per file, one class per capability
- No sprawling files — keep files focused and single-purpose
- Tests for every capability action in `tests/test_capabilities.py`
- Integration tests for the full interaction flow in `tests/test_orchestration.py`
- Comments explain *why*, not *what*
- All configuration from environment variables, never hardcoded

---

## When You Are Unsure

If a decision is not covered by these instructions or the architecture documents, ask yourself:

*Does this make Chitra feel more like a person and less like a tool?*

If yes, proceed. If no, reconsider. If still unsure, flag it as a question in a code comment rather than making a silent assumption.

---

## Document Index

| Document | Purpose |
|---|---|
| VISION.md | The why. Read first, always. |
| PHASE1_SCOPE.md | What Phase 1 builds and the demo acceptance criteria |
| ARCHITECTURE.md | The five layers, interaction flows, proactive loop |
| CAPABILITIES.md | Every capability's API contract |
| MEMORY_DESIGN.md | Memory layer design in full |
| TECH_STACK.md | Technology choices and rationale |
| DEV_SETUP.md | Environment setup from scratch |
| CLAUDE.md | This file |
