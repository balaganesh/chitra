## 2026-02-22 — Session 15

### Added
- `docs/DEPLOYMENT.md` — Linux device deployment guide with hardware recommendations
- `CONTRIBUTING.md` — contribution guidelines
- `CODE_OF_CONDUCT.md` — Contributor Covenant v2.1
- `SECURITY.md` — security vulnerability disclosure policy
- `.github/ISSUE_TEMPLATE/bug_report.md` — bug report template
- `.github/ISSUE_TEMPLATE/feature_request.md` — feature request template
- `.github/PULL_REQUEST_TEMPLATE.md` — pull request checklist

### Changed
- `.gitignore` — added `.ruff_cache/` and `.cursor/`
- `README.md` — added Contributing, Security sections and deployment doc link

### Fixed
- Removed unused `Dockerfile` and `.dockerignore` (Docker approach abandoned)

### Deferred
- `scripts/deploy.sh` and `scripts/chitra.service` — for when hardware is acquired

## 2026-02-22 — Session 14

### Added
- 18 text-mode E2E tests in `TestTextModeE2E` covering full conversation pipeline with real capability databases
- Manual E2E verification with live Ollama in text mode (6-turn conversation)

### Changed
- Total tests: 233 → 251

### Fixed
- Nothing

### Deferred
- Nothing

## 2026-02-22 — Session 13

### Added
- `requirements-ci.txt` — lightweight CI dependency file (no torch/whisper/silero-vad)
- `libportaudio2` added to CI and Dockerfile system dependencies

### Changed
- CI workflow uses `requirements-ci.txt` instead of full `requirements.txt` to avoid heavy ML deps on runners
- Optional audio/ML imports in `capabilities/voice_io.py` now catch `Exception` instead of just `ImportError` (handles `OSError` from sounddevice on headless Linux)

### Fixed
- CI test failures on ubuntu-latest caused by sounddevice `OSError` on headless systems (no PortAudio runtime)

### Deferred
- Local Docker-based Linux validation (user unable to install Docker)
- Full ML-dep test suite on Linux CI (torch/whisper install too heavy for CI runners)

## 2026-02-22 — Session 12

### Added
- **Piper runtime check** in `capabilities/voice_io.py` — `_check_piper_available()` verifies binary, platform-specific shared libraries, and voice model file exist before marking TTS as available

### Changed
- **TTS methods return bool** in `capabilities/voice_io.py` — `_speak_blocking()` and `_speak_dev_fallback()` now return True/False indicating actual speech outcome; `speak()` logs accurately instead of always claiming success

### Fixed
- **Piper TTS false positive on macOS** — binary existed but crashed at runtime due to missing shared libraries; now detected correctly via file-system check instead of process execution (which hangs macOS crash reporter)
- **TTS false success logging** — `speak()` previously logged "Spoke: ..." even when TTS failed silently; now logs "TTS failed for: ..." on failure

### Deferred
- Linux VM validation with Piper TTS
- CI voice test coverage

---

## 2026-02-22 — Session 11

### Added
- Nothing

### Changed
- Nothing

### Fixed
- **LLM client default model** in `llm/client.py` — changed from `llama3.1:8b` to `qwen2.5:7b` to match installed model and documentation
- **Silero VAD chunk size** in `capabilities/voice_io.py` — changed from 30ms (480 samples) to 32ms (512 samples) to meet Silero VAD v6 minimum requirement
- **Test assertion** in `tests/test_orchestration.py` — updated LLM client initialization test to expect `qwen2.5:7b` default

### Verified
- **Full voice-to-voice loop** — 3-turn interactive conversation: Mic → VAD → Whisper STT → Context → LLM (qwen2.5:7b) → Action Dispatch → Memory Store → Display → macOS say TTS

### Deferred
- Linux VM validation with Piper TTS
- Piper TTS setup script completion
- CI voice test coverage

---

## 2026-02-22 — Session 10

### Added
- **21 voice pipeline tests** in `tests/test_capabilities.py` — `TestVoiceIOVoice` class covering model loading (Whisper lazy load, VAD lazy load, idempotent), voice input pipeline (transcription, no-speech, error paths, mode dispatch), VAD recording (speech detection, no-speech, max duration), transcription (normalization, Whisper params), TTS (Piper subprocess, failure handling, empty output, audio playback), and dev TTS fallback (macOS say, platform check, mode gating)
- **macOS `say` TTS dev fallback** in `capabilities/voice_io.py` — `_dev_tts_fallback` flag, `_speak_dev_fallback()` method, activated when Piper is unavailable on Darwin

### Changed
- **Silero VAD loading** in `capabilities/voice_io.py` — replaced `torch.hub.load` with `silero_vad.load_silero_vad()` pip package API (bundles model locally, no network fetch)
- **Audio dependencies installed** — openai-whisper, silero-vad, sounddevice, numpy verified in dev venv

### Fixed
- Nothing

### Deferred
- Linux VM validation with Piper TTS
- Interactive voice conversation testing with live Ollama

---

## 2026-02-22 — Session 9

### Added
- Nothing

### Changed
- **Documentation accuracy pass** across 7 files — all model references updated from `llama3.1:8b` to `qwen2.5:7b`, test stub labels corrected to actual counts, missing config variable `CHITRA_INPUT_MODE` added to CLAUDE.md, proactive loop threshold corrected (7→3 days), audio library corrected (`sounddevice`), missing files added to project structure in DEV_SETUP.md
- **Ruff lint configuration tightened** in `pyproject.toml` — explicit rule selection expanded from defaults to 11 categories (E, F, W, I001, COM812, RET505, PERF, RUF005, D403, D413, Q003); 58 violations fixed (54 auto-fixed, 4 manual)
- **LLM prompt improved** in `llm/prompts.py` — memory_store category constraint made explicit with allowed values list, guard against storing reminders/tasks/events as memories, ambiguous pipe syntax replaced with clear enumeration

### Fixed
- Import ordering across 6 files (auto-fixed by ruff I001)
- Missing trailing commas across 11 locations (auto-fixed by ruff COM812)
- Docstring capitalization in 13 test methods (auto-fixed by ruff D403)
- 2 manual list comprehension replacements in `capabilities/memory.py` (PERF401)
- 2 collection literal concatenation fixes in `capabilities/memory.py` and `capabilities/contacts.py` (RUF005)
- Line-length violations in `capabilities/contacts.py`, `capabilities/memory.py`, `orchestration/context.py` (E501)
- Superfluous else-after-return in `capabilities/voice_io.py` (RET505)

### Deferred
- Linux VM validation
- Voice mode end-to-end testing with audio dependencies
- E501 enforcement in tests and string-heavy scripts (cosmetic, low value)

---

## 2026-02-22 — Session 8

### Added
- Nothing

### Changed
- CI dependency installation in `.github/workflows/ci.yml` now installs only core/test/lint packages required for the workflow (instead of full `requirements.txt`)
- Ruff exclude list in `pyproject.toml` expanded to include local virtualenv directory patterns used during CI reproduction

### Fixed
- GitHub Actions failure in `lint-and-test` caused by optional audio dependency build path (`openai-whisper`) during CI setup

### Deferred
- Incremental lint tightening (reduce baseline ignores over follow-up sessions)
- Linux VM validation
- Voice mode end-to-end testing with audio dependencies

---

## 2026-02-22 — Session 7

### Added
- **GitHub Actions CI workflow** (`.github/workflows/ci.yml`) running on pushes/PRs to `main` and `dev`
  - Python 3.11 setup
  - Dependency installation from `requirements.txt`
  - Lint step: `ruff check .`
  - Test step: `pytest tests/ -v`
- **Ruff configuration** (`pyproject.toml`) with Python 3.11 target and baseline lint policy

### Changed
- Project quality gates now include automated lint + tests in CI
- Local test run for closure: 212 tests passing

### Fixed
- Removed unused import `sys` from `main.py`
- Removed unused `Reminders` import from `scripts/seed_demo.py`

### Deferred
- Incremental lint tightening (reduce ignores and fix remaining non-baseline issues over follow-up sessions)
- Linux VM validation
- Voice mode end-to-end testing with audio dependencies

---

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
