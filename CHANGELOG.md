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
