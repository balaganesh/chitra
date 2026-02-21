## Session — 2026-02-21 (Session 3)

### What was discussed
- Building the full orchestration layer: LLM Client, Context Assembly, Orchestration Core, Proactive Loop, Onboarding Flow
- No new architectural decisions required — all design was established in Sessions 1-2

### Key decisions made
1. **Action dispatch uses introspection** — `execute_action()` inspects method signatures to distinguish single-dict methods (e.g. `create(task)`) from keyword-argument methods (e.g. `get(name=...)`)
2. **Proactive prompt template** — added `PROACTIVE_PROMPT_TEMPLATE` to `llm/prompts.py` with `should_speak` field for the LLM to decide if something is worth surfacing
3. **Onboarding uses marker file** — `.onboarding_complete` in data dir for first-boot detection (simpler and more reliable than checking Memory contents)
4. **Input mode detection** — onboarding detects text/voice preference from natural language keywords in the user's answer
5. **Proactive loop auto-dismisses reminders** — after surfacing fired reminders, they are automatically dismissed so they don't fire again on the next tick
6. **Neglected contacts capped at 3** — proactive loop limits to top 3 neglected contacts to avoid overwhelming the LLM

### What was built
- **LLM Client** (`llm/client.py`) — full Ollama HTTP interface via httpx, 3-tier JSON parsing (direct → markdown extraction → brace matching), retry with correction prompt (max 2), safe fallback response
- **Context Assembly** (`orchestration/context.py`) — gathers Memory + System State + Calendar + Reminders, builds structured system prompt with natural language sections, error fallback
- **Orchestration Core** (`orchestration/core.py`) — the brain:
  - Boot sequence: input mode → onboarding check → proactive loop → conversation loop
  - Conversation loop: listen → context → LLM → action dispatch → second LLM (if action) → memory store → display + speak
  - Action dispatch with method signature introspection
  - Conversation history sliding window (configurable turns)
  - Clean shutdown with proactive loop cancellation
- **Proactive Loop** (`orchestration/proactive.py`) — 60s background tick:
  - Gathers fired reminders, upcoming events, neglected contacts, overdue tasks
  - Lightweight LLM call to decide what's worth surfacing
  - Respects `is_user_active` flag
  - Auto-dismisses fired reminders after surfacing
- **Onboarding Flow** (`onboarding/flow.py`) — first-run conversational onboarding:
  - 5 questions: name, input mode, key people, work schedule, preferences
  - Stores all answers to Memory (confidence 1.0, source "stated")
  - Natural language input mode detection
  - Empty answer detection for optional questions
  - Summary generation at end
  - Marker file for first-boot detection
- **Proactive Prompt** (`llm/prompts.py`) — added `PROACTIVE_PROMPT_TEMPLATE`
- **78 pytest tests** across `test_orchestration.py` and `test_onboarding.py` — all passing

### Open questions
- End-to-end testing with actual Ollama LLM is not covered by unit tests — requires Ollama running locally
- The full `handle_input()` pipeline (context → LLM → action → response) is not tested end-to-end because it requires a live LLM connection

### Deferred work
- Piper TTS binary download in setup_piper.py
- Voice mode end-to-end testing with audio deps
- End-to-end integration test with live Ollama
- Linux VM testing

---

## Session — 2026-02-21

### What was discussed
- Read and reviewed all documentation: VISION.md, ARCHITECTURE.md, CAPABILITIES.md, MEMORY_DESIGN.md, TECH_STACK.md, PHASE1_SCOPE.md, DEV_SETUP.md, CLAUDE.md
- Agreed on project scaffold structure matching DEV_SETUP.md specification
- Set up git workflow: created `dev` branch from `main`
- Configured local git identity for the repo

### What was built
- **Full project scaffold** — 30 files across 8 directories:
  - `main.py` — entry point, loads config, boots OrchestrationCore
  - `orchestration/` — core.py, context.py, proactive.py with class stubs
  - `capabilities/` — all 7 capability classes (VoiceIO, Contacts, Calendar, Reminders, Tasks, Memory, SystemState) with full API method signatures matching CAPABILITIES.md
  - `llm/` — client.py (LLMClient with retry/fallback stubs), prompts.py (system identity, JSON format, correction prompt)
  - `storage/` — schema.py with all 5 SQLite CREATE TABLE statements and SCHEMAS registry
  - `onboarding/` — flow.py with OnboardingFlow stub
  - `scripts/` — setup_piper.py, setup_storage.py (functional — creates dirs and initializes DBs)
  - `tests/` — 4 test files with class stubs for all test categories
  - `.env.example` — 4 config variables with defaults
  - `requirements.txt` — pinned Phase 1 dependencies
- **Python venv** created with pytest and pytest-asyncio installed
- **Bug fix** — added `from __future__ import annotations` to 5 capability files for Python 3.11 compatibility with `list[dict]` type hints

### Open questions
- None — scaffold is complete, ready to start building capabilities

### Deferred work
- All capability implementations (starting next session, Memory first)
- Piper TTS download logic in setup_piper.py
- Full test implementations

---

## Session — 2026-02-21 (Session 2)

### What was discussed
- Text input should be a first-class input mode, not a fallback — users often prefer typing
- In text mode, Chitra displays responses only — no TTS audio
- Onboarding should ask preferred input mode (text or voice)
- Introduced `CHITRA_WHISPER_MODEL` env var for configurable Whisper model size
- SSH key setup for GitHub push access

### Key decisions made
1. **Text input is first-class** — equal to voice, not a fallback. Updated all 6 docs.
2. **TTS behavior per mode** — voice mode: speak + display. Text mode: display only.
3. **Default input mode is text** — configurable, stored as user preference after onboarding.
4. **Whisper model configurable** — `CHITRA_WHISPER_MODEL` env var, default "base".
5. **Audio deps are optional** — Voice I/O gracefully degrades to text-only when audio libs are missing.

### What was built
- **All 7 capabilities fully implemented:**
  - `Memory` — SQLite-backed, store/get_context/search/update/deactivate with MEMORY_DESIGN.md context window rules
  - `System State` — cross-platform battery (Linux /sys + macOS pmset), time_of_day classification
  - `Contacts` — CRUD + get_neglected for proactive loop, case-insensitive search
  - `Calendar` — CRUD + get_upcoming/get_today with datetime comparison
  - `Reminders` — CRUD + get_fired/dismiss for proactive loop
  - `Tasks` — CRUD + get_overdue/get_due_today, priority validation
  - `Voice I/O` — text mode (asyncio.to_thread input), voice mode (sounddevice + Silero VAD + Whisper STT), TTS (Piper subprocess), rich terminal display. Lazy model loading, optional deps with graceful degradation.
- **Documentation updates** — 6 docs updated for text input as first-class mode
- **New config** — `CHITRA_WHISPER_MODEL` and `CHITRA_INPUT_MODE` added to .env.example and CLAUDE.md
- **SSH key setup** — generated ed25519 key, configured for GitHub push
- **.gitignore** — added for Python/venv/macOS artifacts

### Open questions
- Silero VAD API: current implementation uses `torch.hub.load`. The `silero-vad==5.1` pip package may provide a simpler API (`from silero_vad import load_silero_vad`). Should be verified when audio deps are installed.
- Piper TTS sample rate (22050 Hz) is hardcoded for the lessac model — may need adjustment for other voice models.

### Deferred work
- LLM client implementation (Ollama interface)
- Orchestration Core implementation (context assembly, main loop, action dispatch)
- Proactive loop implementation
- Onboarding flow implementation
- Piper TTS download logic in setup_piper.py
- Full test implementations
- Voice mode end-to-end testing (requires audio deps installed)
