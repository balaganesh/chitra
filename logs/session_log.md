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
