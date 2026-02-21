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
- Preferred input mode (text or voice)
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
| `CHITRA_WHISPER_MODEL` | `base` | Whisper STT model size (base, small, medium) |
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

## Working Rules — Do

**Ask for approval before significant decisions.**
Significant means anything that affects: architecture, API contracts, data models, file structure, technology choices, capability behavior, or anything that would require changes to the documentation. When in doubt, ask. Do not silently make consequential choices.

**Explain your reasoning before acting.**
Before writing code for a non-trivial piece of work, briefly state what you plan to do and why. Give the user a chance to redirect before you build the wrong thing.

**Work in small, reviewable units.**
Build one meaningful unit at a time — one capability, one flow, one module. Present it for review before moving to the next. Never build several things in one go without approval checkpoints between them.

**Flag contradictions explicitly.**
If a request contradicts VISION.md, the architecture documents, or a previous decision — say so clearly before proceeding. Do not silently comply with something that breaks the design.

**Keep the user informed of progress.**
At the start of each working unit, state what you are building. At the end, summarize what was done and what comes next.

**Suggest improvements when you see them.**
If you notice a better approach, a missing edge case, or a design issue — raise it. You are a technical collaborator, not just an executor.

---

## Working Rules — Don't

**Don't assume without discussion.**
Never make an architectural, structural, or behavioral decision based on assumption. If something is unclear, ask before building.

**Don't make undiscussed changes to existing working code.**
If a new piece of work requires modifying something already built and approved, flag the change explicitly and get approval before making it.

**Don't introduce new dependencies without approval.**
Every new library or tool is a decision. State what you want to add, why, and what it does — before adding it to requirements.txt.

**Don't skip the approval step under time pressure.**
There is no urgency that justifies building the wrong thing. Always pause at approval checkpoints.

**Don't build what isn't in scope.**
Phase 1 scope is defined in PHASE1_SCOPE.md. Do not build Phase 2 features, even if they seem easy or natural to add. Flag them as future work instead.

**Don't leave silent failures.**
Every error must be logged and handled. Never write code that silently swallows exceptions or fails without trace.

---

## Git Workflow

**Branch strategy:**
- `main` — stable, tested, approved code only
- `dev` — active development branch, all session work happens here
- Never commit directly to `main` during a session

**During a session:**
After each meaningful unit of work is approved by the user, commit it to `dev`:
```bash
git add .
git commit -m "descriptive message of what was built"
```

Commit messages must be clear and specific. Examples:
- `Add Memory capability with SQLite storage and get_context() injection`
- `Implement Reminders capability — create, get_fired, dismiss actions`
- `Add robust JSON parsing with retry to Orchestration Core`

**End of session — merge to main:**
After session end protocol is complete (see below), merge `dev` to `main`:
```bash
git checkout main
git merge dev
git push origin main
git checkout dev
```

---

## Testing Protocol

**When to write tests:**
Tests are written at the end of each session, after all session work is complete and approved. Not during development — at the end.

**What to test:**
For every capability built or modified in the session, write tests covering:
- Each action's happy path — correct input, expected output
- Each action's error cases — missing input, invalid input, storage failure
- Edge cases specific to that capability's behavior

For Orchestration Core work, write integration tests covering:
- Full interaction flow end to end
- Proactive loop trigger and response
- JSON parsing failure and retry behavior
- Context assembly correctness

**Test file locations:**
```
tests/
  test_capabilities.py      # Unit tests for all capability actions
  test_orchestration.py     # Integration tests for orchestration flows
  test_memory.py            # Memory-specific tests (context assembly, injection)
  test_onboarding.py        # Onboarding flow tests
```

**Test standard:**
- Every test must have a clear docstring explaining what it tests and why
- Tests must be runnable with `python -m pytest tests/ -v`
- All tests must pass before end of session protocol begins
- A failing test is never left unresolved at session end

---

## Session End Protocol

At the end of every build session, before closing, complete the following in order:

**1. Write and run tests**
Write tests for everything built in the session. Run the full test suite:
```bash
python -m pytest tests/ -v
```
All tests must pass. Fix any failures before proceeding.

**2. Session Log**
Create or append to `logs/session_log.md` with the following structure:

```markdown
## Session — [Date]

### What was discussed
- Key decisions made
- Design questions resolved
- Anything deferred to a future session

### What was built
- List of files created or modified
- Summary of each unit of work completed

### Open questions
- Anything unresolved that needs discussion next session

### Deferred work
- Features or improvements noted but intentionally left for later
```

**3. Change Log**
Create or append to `CHANGELOG.md` in the repo root with the following structure:

```markdown
## [Date] — Session N

### Added
- New capabilities, features, or files added

### Changed
- Modifications to existing behavior or code

### Fixed
- Bugs or issues resolved

### Deferred
- Items explicitly moved to future sessions
```

**4. Test Log**
Create or append to `logs/test_log.md` with the following structure:

```markdown
## Test Run — [Date]

### Summary
- Total tests: N
- Passed: N
- Failed: 0

### Tests added this session
- List of new test cases written

### Coverage notes
- Any areas not yet covered by tests and why
```

**5. Commit to dev and merge to main**
After all protocol steps are complete and the user gives final approval:
```bash
# Commit session end artifacts
git add .
git commit -m "Session end — logs, tests, changelog updated"

# Merge to main
git checkout main
git merge dev
git push origin main
git push origin dev
git checkout dev
```

**Final approval required.**
Do not merge to main without explicit user confirmation. Present a summary of the session and ask: *"Everything looks good — shall I merge to main?"*

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
