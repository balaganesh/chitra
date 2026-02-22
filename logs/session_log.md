## Session — 2026-02-22 (Session 11)

### What was discussed
- Interactive voice conversation with live Ollama — full voice-to-voice loop verification

### Key decisions made
1. **LLM client default model fixed** — code default was still `llama3.1:8b` while docs said `qwen2.5:7b`; aligned code to `qwen2.5:7b`
2. **Silero VAD chunk size fixed** — v6 requires minimum 512 samples; changed from 30ms (480 samples) to 32ms (512 samples)

### What was built
- **Full voice-to-voice loop verified** — Mic → Silero VAD → Whisper STT → Context Assembly → LLM (qwen2.5:7b) → Action Dispatch (reminders.create) → Memory Store → Rich Display → macOS say TTS
- **3-turn interactive conversation completed** — user spoke, Chitra transcribed, reasoned through LLM, executed actions (created reminder), stored memories, and spoke responses
- **Bug fixes** — LLM client default model (`llama3.1:8b` → `qwen2.5:7b`), Silero VAD chunk size (30ms → 32ms)

### Manual verification results
- Turn 1: Whisper transcribed speech, Chitra responded contextually using memory (knew user name "Bala" and prior context about calling mother)
- Turn 2: User requested reminder, Chitra created reminder via `reminders.create` action, made follow-up LLM call, stored memory observations, spoke confirmation
- Turn 3: User confirmed, Chitra responded conversationally, stored memory observation

### Open questions
- Whisper confidence scores were low (0.00–0.58) despite correct transcription — likely due to ambient noise or short utterances; not a blocking issue
- Piper TTS on macOS remains blocked by dyld shared library issue — `say` fallback covers development use

### Deferred work
- Linux VM validation with Piper TTS
- Piper TTS setup script completion
- CI voice test coverage (install audio deps in CI for mocked tests)

---

## Session — 2026-02-22 (Session 10)

### What was discussed
- Voice mode end-to-end testing — installing audio deps, adding dev TTS fallback, writing automated tests, and manual pipeline verification

### Key decisions made
1. **Silero VAD switched from torch.hub to pip package API** — `silero_vad.load_silero_vad()` bundles the model locally, eliminating network fetch at runtime and fixing SSL issues on dev machines
2. **macOS `say` command added as dev-only TTS fallback** — activates automatically when Piper binary is unavailable on Darwin; clearly marked as not for production
3. **Dev TTS fallback controlled by `_dev_tts_fallback` flag** — computed at init time, testable, and does not alter the Piper production code path

### What was built
- **Audio deps installed and verified** — openai-whisper, silero-vad, sounddevice, numpy all installed in dev venv with successful imports
- **macOS `say` TTS fallback** — added `_dev_tts_fallback` flag and `_speak_dev_fallback()` method to `capabilities/voice_io.py`; production Piper path unchanged
- **21 voice pipeline tests** — new `TestVoiceIOVoice` class in `tests/test_capabilities.py` covering model loading, voice input, VAD recording, transcription, TTS (Piper + dev fallback), and mode dispatch
- **Silero VAD loading improved** — replaced `torch.hub.load` with `silero_vad.load_silero_vad()` package API in `_load_silero_vad()`

### Manual verification results
- Audio devices detected: MacBook Air Microphone (input), MacBook Air Speakers (output)
- Voice mode switch: successful
- Whisper base model: loaded from cache, device=cpu
- Silero VAD model: loaded via pip package API
- macOS `say` TTS: spoke text audibly
- Microphone recording: captured 48000 samples (3s at 16kHz)
- Whisper transcription: returned empty for ambient noise (correct behavior)

### Open questions
- Full interactive voice-to-voice loop (user speaks → Whisper → LLM → say response) requires manual testing with live Ollama and speech input
- Piper TTS on macOS remains blocked by dyld shared library issue — `say` fallback covers development use

### Deferred work
- Linux VM validation with Piper TTS
- Interactive voice conversation testing with live Ollama

---

## Session — 2026-02-22 (Session 9)

### What was discussed
- Reviewed the full repository state and identified next steps from where previous sessions left off
- Agreed to tackle three items: documentation accuracy pass, incremental lint tightening, and LLM prompt improvement

### Key decisions made
1. **Model references standardized to `qwen2.5:7b`** — all 7 docs that referenced `llama3.1:8b` or `Llama 3.1 8B` updated to reflect the actual selected model
2. **Ruff rule selection made explicit** — moved from implicit defaults to 11 explicitly selected rule categories for clarity and progressive enforcement
3. **E501 (line-too-long) deliberately deferred** — SQL strings, prompt templates, and natural-language content are more readable long; enforcing 100-char in these contexts adds churn without quality benefit
4. **Memory category constraint strengthened at prompt level** — rather than relying solely on server-side validation to reject bad categories, the prompt now explicitly enumerates the 4 valid categories and tells the LLM not to use others

### What was built
- **Documentation accuracy pass** — fixed outdated model references, test stub labels, missing config variable, incorrect proactive threshold, incorrect audio library name, and missing files in project structure across README.md, CLAUDE.md, DEV_SETUP.md, TECH_STACK.md, ARCHITECTURE.md, PHASE1_SCOPE.md
- **Lint tightening** — updated `pyproject.toml` with explicit rule selection; auto-fixed 54 violations (import sorting, trailing commas, docstring formatting, escaped quotes, superfluous else); manually fixed 4 violations (PERF401, RUF005); wrapped 3 long lines in source
- **LLM prompt improvement** — rewrote `RESPONSE_FORMAT_INSTRUCTION` memory_store section with explicit category enumeration, added constraint text, added guard against misusing memory for reminders/tasks/events; reinforced in `CAPABILITY_CATALOG` memory section

### Open questions
- None blocking

### Deferred work
- Linux VM validation
- Voice mode end-to-end testing with audio dependencies
- E501 enforcement in tests and string-heavy files

---

## Session — 2026-02-22 (Session 8)

### What was discussed
- Post-closure follow-up requested after GitHub Actions reported failure on the latest run
- Investigated and resolved the CI failure, then propagated the fix across branches
- Requested to re-close the session after post-closure work

### Key decisions made
1. **CI should install only what it actually needs** — avoid optional audio dependencies in CI setup
2. **Keep voice/audio deps optional for runtime environments** — preserve project behavior while stabilizing CI
3. **Apply the CI fix to both `dev` and `main`** so branch behavior remains consistent

### What was built
- **CI hotfix** in `.github/workflows/ci.yml`:
  - Replaced `pip install -r requirements.txt` with explicit install list for core/test/lint dependencies used by workflow steps
- **Ruff config adjustment** in `pyproject.toml`:
  - Expanded exclude list to include temporary virtualenv directory patterns used during local CI reproduction
- **Branch synchronization**:
  - Committed and pushed fix on `dev`
  - Fast-forward merged `dev` into `main` and pushed `main`
- **Re-closure test run**:
  - Full suite rerun with 212/212 passing

### Open questions
- None blocking

### Deferred work
- Incremental lint tightening and cleanup pass
- Linux VM validation
- Voice mode end-to-end testing with audio dependencies

---

## Session — 2026-02-22 (Session 7)

### What was discussed
- Requested a repository status review and then approved execution of next steps
- Agreed to prioritize baseline engineering guardrails first: CI + lint checks
- Requested session closure protocol once CI/lint setup was complete

### Key decisions made
1. **Baseline-first quality gates** — introduce CI and lint without broad code churn
2. **Ruff scope kept practical** — start with a stable baseline and tighten incrementally later
3. **Branch targets for CI** — run checks on both `main` and `dev` for immediate feedback during active development

### What was built
- **Repository assessment completed** with status summary and actionable next steps
- **CI workflow added** at `.github/workflows/ci.yml`:
  - Python 3.11 environment
  - `pip install -r requirements.txt`
  - `ruff check .`
  - `pytest tests/ -v`
- **Ruff baseline configuration added** in `pyproject.toml`
- **Cleanup fixes**:
  - Removed unused `sys` import from `main.py`
  - Removed unused `Reminders` import from `scripts/seed_demo.py`
- **Session closure protocol executed**:
  - Full test suite rerun successfully (212/212 passing)
  - Logs and changelog updated for this session

### Open questions
- None blocking. Next improvement track is incremental lint tightening after this baseline.

### Deferred work
- Incremental lint rule tightening and cleanup pass
- Linux VM validation
- Voice mode end-to-end testing with audio dependencies

---

## Session — 2026-02-22 (Session 6)

### What was discussed
- Building the demo seed script to pre-populate databases for the PHASE1_SCOPE.md demo scenario
- Reviewed all capability APIs (Contacts, Calendar, Tasks, Memory, Reminders) to understand exact field names and create patterns
- Selected `qwen2.5:7b` as the recommended LLM model for 16GB M4 MacBook Air
- Ran the full demo scenario end-to-end against live Ollama — identified and fixed two issues with proactive loop context gathering
- Reviewed the onboarding marker mechanism to skip onboarding for seeded data

### Key decisions made
1. **Wipe and re-create on every run** — seed script deletes all existing databases and re-creates from scratch. Ensures clean, reproducible state.
2. **Dynamic dates** — all dates computed from `datetime.now()` so the demo scenario is temporally correct regardless of when it's run
3. **Amma's last_interaction set to 5 days ago** — matches the demo scenario exactly
4. **9 memory entries** — covers both onboarding data and demo-specific memories
5. **No reminders pre-seeded** — the user creates these during the demo conversation
6. **`qwen2.5:7b` selected as default model** — best JSON instruction following at 7B class, fits comfortably in 16GB M4, ~32 tok/s
7. **Neglected contacts threshold lowered to 3 days** — 7 days was too high for the demo scenario (Amma is 5 days neglected)
8. **Calendar meeting time set dynamically** — `now + 30 min` instead of static `10:00` so it always appears in upcoming events

### What was built
- **`scripts/seed_demo.py`** — complete demo seed script:
  - `seed_contacts()` — Amma, Ravi, Priya with correct last_interaction offsets
  - `seed_calendar()` — Team meeting 30 min from now (dynamic)
  - `seed_tasks()` — 3 pending tasks with due dates computed from today
  - `seed_memory()` — 9 memory entries across all 4 categories
  - `_mark_onboarding_complete()` — creates `.onboarding_complete` marker
  - `_wipe_databases()` — removes all existing .db files for clean state
- **End-to-end demo run** — verified against live Ollama with qwen2.5:7b:
  - Proactive loop surfaces meeting + neglected Amma ✅
  - Greeting uses user's name from memory ✅
  - Reminder creation dispatches correctly ✅
  - Second proactive tick fires unprompted ✅
  - Confirmation creates 2pm reminder ✅

### Open questions
- LLM sometimes tries to store memories with invalid category "reminder" — validation catches it correctly, but prompt could be improved to prevent the attempt

### Deferred work
- Voice mode end-to-end testing with audio deps
- Linux VM testing

---

## Session — 2026-02-22 (Session 5)

### What was discussed
- Implementing the Piper TTS setup script — the last deferred item from Session 2
- Researched Piper release structure on GitHub and voice model URLs on HuggingFace

### Key decisions made
1. **Piper version pinned to 2023.11.14-2** — latest stable release with pre-built binaries for all 4 platform targets
2. **Voice model: en_US-lessac-medium** — matches the model referenced in voice_io.py and documentation
3. **SSL fallback for macOS** — Python's default certifi bundle may not be configured; falls back to unverified context for known URLs (GitHub, HuggingFace). Acceptable for one-time setup script, not runtime code.
4. **Temporary directory extraction** — avoids tarball naming conflict where `piper/` directory collides with `piper` binary filename

### What was built
- **`scripts/setup_piper.py`** — complete implementation replacing the placeholder stub:
  - Platform detection via `platform.system()` and `platform.machine()` — maps to 4 tarball variants
  - `_download_file()` — downloads with temporary file pattern, SSL certificate fallback, progress logging
  - `_extract_piper_binary()` — extracts tarball to temp directory first, moves contents to `tts_dir`, sets executable permissions
  - `setup_piper()` — orchestrates binary download/extraction + voice model download, idempotent (skips existing files)
  - Downloads: Piper binary (~18 MB), voice model (~60 MB), model config (~5 KB)

### Open questions
- Piper binary requires shared libraries (libespeak-ng, libonnxruntime) that extract alongside it from the tarball. On macOS, `dyld` fails to find them via `@rpath` — this is expected since macOS is the dev platform, not the target runtime. On Linux (target), the shared libs are found correctly via relative rpath.

### Deferred work
- Voice mode end-to-end testing with audio deps
- End-to-end integration test with live Ollama
- Linux VM testing

---

## Session — 2026-02-22 (Session 4)

### What was discussed
- Filling the empty test stubs for all 7 capabilities from Session 2
- No new architectural decisions — all capabilities were already built and smoke-tested

### Key decisions made
- None — this was a test-writing session, no design changes

### What was built
- **`tests/test_memory.py`** — 37 tests across 2 classes:
  - **TestMemoryStorage** (20 tests) — store all 4 categories, defaults, unique IDs, validation errors (missing category/subject/content, invalid category, invalid source), search (by subject/content, case-insensitive, no results, excludes inactive, ordered by confidence), update (content, refreshes last_referenced, not found), deactivate (success, excludes from context, not found)
  - **TestMemoryContext** (17 tests) — empty context, includes preferences, includes high-confidence facts, excludes low-confidence facts, includes recent relationships, includes observations, excludes inactive, section formatting (About/People/Patterns), multiple sections, last_referenced tracking (included vs excluded), relationship aging (30-day rule: old excluded, recent included)

- **`tests/test_capabilities.py`** — 95 tests across 6 classes:
  - **TestContacts** (19 tests) — create (full/minimal/missing name), get (exact/partial/case-insensitive/not found), list (empty/all/ordered), update (fields/invalid/not found), note_interaction (success/not found), get_neglected (none/finds old/ordered)
  - **TestCalendar** (14 tests) — create (basic/participants/duration/missing fields), get_today (found/ordered/empty), get_range (found/inclusive/empty), get_upcoming (future/excludes past)
  - **TestReminders** (14 tests) — create (basic/contact_id/missing fields), get_fired (past/excludes future/excludes dismissed), dismiss (success/not found), list_upcoming (found/excludes past/excludes dismissed), delete (success/not found)
  - **TestTasks** (19 tests) — create (basic/full/missing title/invalid priority/valid priorities), list (all/pending/done/invalid/empty), complete (success/not found), get_overdue (found/excludes future/excludes done/excludes no date), get_due_today (found/excludes other dates/excludes done)
  - **TestSystemState** (9 tests) — get returns all keys, datetime is ISO, day_of_week valid, battery is integer, time_of_day classification, mocked time-of-day (morning/afternoon/evening/night)
  - **TestVoiceIO** (20 tests) — default mode, conversation log empty, set_input_mode (text/invalid/voice without deps), listen text (normal/empty/strips whitespace/EOF), speak text mode (skips TTS/empty), display (adds to log/user only/chitra only/returns done), confidence extraction (no segments/good/poor/clamped)

- **README.md** — updated from "Pre-development" to "Core implementation complete" with full project details

### Open questions
- None

### Deferred work
- Piper TTS binary download in setup_piper.py
- Voice mode end-to-end testing with audio deps
- End-to-end integration test with live Ollama
- Linux VM testing
- Keyboard shortcuts / spacebar activation (mentioned in docs, not critical for POC)

---

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

**Code review fixes (from Codex evaluation):**
- **Conversation history now sent to LLM** — `LLMClient.call()` accepts `conversation_history` param; `handle_input()` passes history to both LLM calls for multi-turn continuity
- **Onboarding no longer marks complete on failure** — removed `_mark_complete()` from exception handler; onboarding retries on next boot if it crashes
- **Memory last_referenced scoped to included entries** — changed from blanket update of all active rows to only updating entries actually included in the context block, so aging/recency rules work correctly
- **Capability catalog added to system prompt** — `CAPABILITY_CATALOG` constant lists all 6 capabilities with their exact actions and params; injected into every LLM call so the model doesn't hallucinate actions
- **torch.hub.load network warning** — added docstring note about potential network fetch on first VAD model load
- **80 pytest tests** (2 added for new fixes) — all passing

### Open questions
- End-to-end testing with actual Ollama LLM is not covered by unit tests — requires Ollama running locally
- The full `handle_input()` pipeline (context → LLM → action → response) is not tested end-to-end because it requires a live LLM connection

### Deferred work
- Piper TTS binary download in setup_piper.py
- Voice mode end-to-end testing with audio deps
- End-to-end integration test with live Ollama
- Linux VM testing
- Fill test_capabilities.py and test_memory.py stubs (Session 2 capability tests)
- Keyboard shortcuts / spacebar activation (mentioned in docs, not critical for POC)

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
- ~~Silero VAD API~~ — **Resolved in Session 10**: switched to `silero_vad.load_silero_vad()` pip package API
- Piper TTS sample rate (22050 Hz) is hardcoded for the lessac model — may need adjustment for other voice models.

### Deferred work
- LLM client implementation (Ollama interface)
- Orchestration Core implementation (context assembly, main loop, action dispatch)
- Proactive loop implementation
- Onboarding flow implementation
- Piper TTS download logic in setup_piper.py
- Full test implementations
- ~~Voice mode end-to-end testing~~ — **Completed in Session 10**
