## 2026-02-22 — Session 6

### Added
- **`scripts/seed_demo.py`** — demo scenario seed script that pre-populates all capability databases for the PHASE1_SCOPE.md demo
  - Contacts: Amma (mother, last interaction 5 days ago), Ravi (best friend, 2 days), Priya (colleague, today)
  - Calendar: Team meeting 30 min from now (dynamic time so demo always works)
  - Tasks: Review project notes, Update documentation, Prepare presentation — all with due dates
  - Memory: 9 entries — user name, input mode preference, work schedule, relationships, calling mother preference, project notes preference, morning routine observation
  - Marks onboarding complete so Chitra boots directly into conversation
  - Wipes and re-creates all databases each run for clean state
  - Uses dynamic dates so temporal references are always correct
- **End-to-end demo verified** against live Ollama with `qwen2.5:7b` — full pipeline works:
  proactive loop → greeting → reminder creation → second proactive → confirmation

### Changed
- Default LLM model: `llama3.1:8b` → `qwen2.5:7b` in `.env.example` (best JSON instruction following at 7B class)
- Neglected contacts threshold: 7 days → 3 days in proactive loop (matches demo scenario where Amma is 5 days neglected)
- Calendar seed: static `10:00` → dynamic `now + 30 min` so upcoming events always appear in proactive context

### Fixed
- Proactive loop found no context because meeting time was in the past and neglected threshold was too high — both now dynamically correct

### Deferred
- Voice mode end-to-end testing with audio deps
- Linux VM testing

---

## 2026-02-22 — Session 5

### Added
- **`scripts/setup_piper.py`** — full implementation replacing stub: downloads Piper TTS binary from GitHub releases and `en_US-lessac-medium` voice model from HuggingFace
  - Platform detection: macOS (arm64, x86_64) and Linux (x86_64, aarch64)
  - SSL certificate fallback for macOS (Python certifi may not be configured)
  - Idempotent — skips files that already exist, safe to re-run
  - Temporary directory extraction to avoid tarball naming conflicts
  - Progress logging, cleanup of tarballs after extraction

### Changed
- Nothing

### Fixed
- Nothing

### Deferred
- ~~End-to-end integration test with live Ollama~~ (seed script ready, Session 6)
- Voice mode end-to-end testing with audio deps
- Linux VM testing

---

## 2026-02-22 — Session 4

### Added
- **132 capability tests** — filled `test_capabilities.py` (95 tests) and `test_memory.py` (37 tests) with formal pytest coverage for all 7 capabilities
- `test_capabilities.py` covers: Contacts (19), Calendar (14), Reminders (14), Tasks (19), SystemState (9), VoiceIO (20)
- `test_memory.py` covers: store (11), search (6), update (3), deactivate (3), context block formatting (7), context window rules (4), last_referenced tracking (2), relationship aging (2)
- **README.md updated** — reflects current implementation status, capabilities, orchestration layer, tech stack, configuration, project structure, test counts

### Changed
- Total test count: 80 → 212 (132 new tests, all passing)

### Fixed
- Nothing

### Deferred
- ~~Piper TTS binary download in setup_piper.py~~ (done in Session 5)
- Voice mode end-to-end testing with audio deps
- End-to-end integration test with live Ollama
- Linux VM testing

---

## 2026-02-21 — Session 3

### Added
- **LLM Client** (`llm/client.py`) — full Ollama HTTP interface with robust 3-tier JSON parsing, retry with correction prompt, safe fallback response
- **Context Assembly** (`orchestration/context.py`) — assembles Memory, System State, Calendar, and Reminders into structured system prompt for every LLM call
- **Orchestration Core** (`orchestration/core.py`) — full implementation: boot sequence, conversation loop, action dispatch with method introspection, memory storage, conversation history sliding window, clean shutdown
- **Proactive Loop** (`orchestration/proactive.py`) — 60s background tick checking fired reminders, upcoming events, neglected contacts, overdue tasks; lightweight LLM call for surfacing decisions; auto-dismisses fired reminders
- **Onboarding Flow** (`onboarding/flow.py`) — 5-step conversational onboarding (name, input mode, key people, work schedule, preferences); marker file for first-boot detection; natural language input mode detection
- **Proactive prompt template** (`llm/prompts.py`) — `PROACTIVE_PROMPT_TEMPLATE` for proactive loop LLM calls
- **78 pytest tests** — comprehensive coverage for OrchestrationCore, ProactiveLoop, ContextAssembly, LLMClient, Prompts, and OnboardingFlow

### Changed
- `LLMClient.call()` now accepts `conversation_history` parameter for multi-turn continuity
- Memory `get_context()` only updates `last_referenced` for entries actually included in context (fixes aging/recency rules)
- Context assembly now includes `CAPABILITY_CATALOG` in every system prompt

### Fixed
- Conversation history was not being sent to the LLM — multi-turn continuity was broken
- Onboarding marked complete even on failure — partially seeded Memory could never be retried
- Memory `last_referenced` bulk update on all active entries defeated relationship aging rules
- LLM had no catalog of available actions — could hallucinate unsupported capabilities

### Deferred
- Piper TTS binary download in setup_piper.py
- Voice mode end-to-end testing with audio deps
- End-to-end integration test with live Ollama
- Linux VM testing
- ~~Fill test_capabilities.py and test_memory.py stubs~~ (done in Session 4)

---

## 2026-02-21 — Session 2

### Added
- **Memory capability** — full SQLite implementation with store, get_context (context window rules from MEMORY_DESIGN.md), search, update, deactivate
- **System State capability** — cross-platform battery reading (Linux + macOS), time_of_day classification
- **Contacts capability** — CRUD, case-insensitive partial name search, note_interaction, get_neglected for proactive loop
- **Calendar capability** — CRUD, get_upcoming with datetime comparison, get_today, get_range, JSON participants field
- **Reminders capability** — CRUD, get_fired (proactive loop), dismiss, list_upcoming, delete
- **Tasks capability** — CRUD, get_overdue (proactive loop), get_due_today, priority validation
- **Voice I/O capability** — two first-class input modes (text + voice), Piper TTS subprocess pipeline, Silero VAD + Whisper STT voice pipeline, rich terminal display, lazy model loading, optional audio deps with graceful degradation
- `.gitignore` for Python, venv, macOS, IDE, and Claude Code artifacts
- `CHITRA_WHISPER_MODEL` env var for configurable Whisper model size
- `CHITRA_INPUT_MODE` env var for default input mode
- SSH key setup for GitHub remote push

### Changed
- **Text input elevated to first-class** — updated CAPABILITIES.md, ARCHITECTURE.md, PHASE1_SCOPE.md, TECH_STACK.md, CLAUDE.md, DEV_SETUP.md
- Onboarding now asks preferred input mode (text or voice)
- `speak()` skips TTS in text mode — display only
- Added `set_input_mode()` action to Voice I/O API contract
- Configuration reference in CLAUDE.md now includes CHITRA_WHISPER_MODEL

### Fixed
- Nothing

### Deferred
- LLM client implementation (Ollama interface)
- Orchestration Core (context assembly, main loop, action dispatch)
- Proactive loop
- Onboarding flow
- Piper TTS binary download in setup_piper.py
- Full test suite implementation
- Voice mode end-to-end testing with audio deps

---

## 2026-02-21 — Session 1

### Added
- Full project scaffold — directory structure, module stubs, and configuration
- `main.py` entry point that boots the OrchestrationCore
- 7 capability class stubs with API signatures matching CAPABILITIES.md
- Orchestration module stubs (core, context assembly, proactive loop)
- LLM client stub with retry/fallback pattern and prompt templates
- SQLite schema definitions for all 5 capability databases
- Onboarding flow stub
- Setup scripts (storage initialization is functional, Piper TTS is placeholder)
- 4 test file stubs organized by test category
- `.env.example` with all Phase 1 configuration variables
- `requirements.txt` with pinned Phase 1 dependencies
- Git workflow: `dev` branch created from `main`

### Changed
- Nothing (first session)

### Fixed
- Added `from __future__ import annotations` to 5 capability files for Python 3.11 compatibility

### Deferred
- All capability implementations (Memory capability first, next session)
- Piper TTS binary download in setup_piper.py
- Test implementations
