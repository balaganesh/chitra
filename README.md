# Chitra

> *From Chitragupta — the keeper of records who remembers every soul's story.*

An AI-first operating system where conversation is the only interface. No apps. No home screen. No navigation. Just you and an OS that knows you, remembers you, and works on your behalf.

---

## The Idea

Every operating system ever built is organized around the same metaphor: apps. You decide which app to open, which button to press, which screen to navigate to. The computer is a tool you operate.

Chitra inverts this.

The AI is the orchestrator. You express intent. The system acts. The user is freed from the cognitive overhead of operating a device and returned to simply living their life.

This is not a voice assistant bolted onto a traditional OS. The GUI shell, the app framework, the launcher — none of these exist. The AI Orchestration Core boots as the primary userspace process. It is the only interface between the human and the machine.

---

## What Makes It Different

**Local first.** Intelligence and data live on the device. No cloud. No API keys. No subscription. No data leaving your hands.

**AI as primitive.** Every capability is built to be consumed by AI — not by a human pressing a button. Reminders, contacts, calendar, memory — these are OS primitives, not apps.

**Memory.** Chitra knows you. Your people, your preferences, your routines. Stored privately on device. Referenced naturally in conversation. Over time, Chitra doesn't just respond — it anticipates.

**No UI except conversation.** If a feature requires a screen full of options, it is not designed correctly.

---

## Architecture

```
┌─────────────────────────────────────┐
│       Conversational Interface      │  Voice or text — the only interface
├─────────────────────────────────────┤
│       AI Orchestration Core         │  Context assembly, LLM reasoning, action dispatch
├─────────────────────────────────────┤
│         Capability Modules          │  7 independent modules with clean APIs
├─────────────────────────────────────┤
│       Hardware Abstraction          │  Audio, storage, system state
├─────────────────────────────────────┤
│          Linux Kernel               │  Ubuntu Server 24.04 LTS
└─────────────────────────────────────┘
```

Full architecture documentation in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Capabilities

All 7 Phase 1 capabilities are implemented:

| Capability | Description |
|---|---|
| **Voice I/O** | Two first-class input modes (text and voice), Piper TTS, Silero VAD + Whisper STT, rich terminal display |
| **Memory** | Personal knowledge layer — facts, preferences, relationships, observations. Injected into every LLM call |
| **Contacts** | Local contact store with relationships, interaction tracking, neglected contact detection |
| **Calendar** | Events with participants, time-based queries, proactive surfacing |
| **Reminders** | Time-based triggers, fired detection for proactive loop, dismissal |
| **Tasks** | Priority-based task management, overdue detection, due-today queries |
| **System State** | Cross-platform battery reading, time-of-day classification |

---

## Orchestration Layer

The brain of Chitra — fully implemented:

- **Orchestration Core** — boot sequence, conversation loop, action dispatch with method introspection, memory storage, conversation history sliding window, clean shutdown
- **Context Assembly** — assembles Memory + System State + Calendar + Reminders into a structured system prompt for every LLM call, includes capability catalog
- **Proactive Loop** — 60-second background tick checking fired reminders, upcoming events, neglected contacts, overdue tasks; lightweight LLM call to decide what's worth surfacing
- **LLM Client** — Ollama HTTP interface with 3-tier JSON parsing, retry with correction prompt, safe fallback response
- **Onboarding Flow** — 5-step conversational first-run setup (name, input mode, key people, work schedule, preferences); marker file for first-boot detection

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.11+, asyncio |
| Local LLM | Ollama (qwen2.5:7b recommended) |
| Speech-to-Text | OpenAI Whisper (local) |
| Text-to-Speech | Piper TTS |
| Voice Activity Detection | Silero VAD |
| Audio I/O | sounddevice |
| Data Storage | SQLite (one DB per capability) |
| Terminal Display | rich |
| Testing | pytest, pytest-asyncio |

---

## Getting Started

See [`docs/DEV_SETUP.md`](docs/DEV_SETUP.md) for complete setup instructions.

**Quick start:**
```bash
git clone https://github.com/balaganesh/chitra.git
cd chitra
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/setup_storage.py
python main.py
```

Requires Python 3.11+ and Ollama. Audio dependencies (whisper, sounddevice, torch) are optional — text mode works without them.

---

## Configuration

All configuration via environment variables (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `CHITRA_DATA_DIR` | `~/.chitra/data` | Storage directory for all capability databases |
| `CHITRA_LLM_MODEL` | `qwen2.5:7b` | Ollama model name — swap models without code changes |
| `CHITRA_WHISPER_MODEL` | `base` | Whisper STT model size (base, small, medium) |
| `CHITRA_INPUT_MODE` | `text` | Default input mode (text or voice) |
| `CHITRA_PROACTIVE_INTERVAL` | `60` | Proactive loop tick interval in seconds |
| `CHITRA_HISTORY_TURNS` | `10` | Conversation history turns included in LLM context |

---

## Project Structure

```
chitra/
  main.py                       # Entry point — boots Orchestration Core
  orchestration/
    core.py                     # AI Orchestration Core — the brain
    context.py                  # Context assembly for LLM calls
    proactive.py                # Proactive background loop
  capabilities/
    voice_io.py                 # Voice I/O (text + voice input, TTS, display)
    memory.py                   # Memory — the personal knowledge layer
    contacts.py                 # Contacts capability
    calendar.py                 # Calendar capability
    reminders.py                # Reminders capability
    tasks.py                    # Tasks capability
    system_state.py             # System State capability
  llm/
    client.py                   # Ollama LLM interface
    prompts.py                  # System prompts and capability catalog
  storage/
    schema.py                   # SQLite schema definitions
  onboarding/
    flow.py                     # First-run onboarding conversation
  scripts/
    setup_piper.py              # Piper TTS setup
    setup_storage.py            # Storage initialization
  tests/
    test_orchestration.py       # Orchestration + LLM + context + E2E tests (72 tests)
    test_onboarding.py          # Onboarding flow tests (26 tests)
    test_capabilities.py        # Capability unit tests (115 tests)
    test_memory.py              # Memory-specific tests (38 tests)
  docs/                         # Architecture and design documentation
```

---

## Tests

251 tests, all passing:

```bash
source venv/bin/activate
python3 -m pytest tests/ -v
```

Coverage includes all 7 capabilities (including voice mode with mocked audio hardware), Orchestration Core, Proactive Loop, Context Assembly, LLM Client, Prompts, Onboarding Flow, and text-mode E2E pipeline tests. Both text and voice modes verified end-to-end with live Ollama.

---

## Documentation

| Document | Description |
|---|---|
| [VISION.md](docs/VISION.md) | The why — principles and philosophy |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture and interaction flows |
| [CAPABILITIES.md](docs/CAPABILITIES.md) | Capability module API contracts |
| [MEMORY_DESIGN.md](docs/MEMORY_DESIGN.md) | Memory layer design and context window rules |
| [TECH_STACK.md](docs/TECH_STACK.md) | Technology choices and rationale |
| [PHASE1_SCOPE.md](docs/PHASE1_SCOPE.md) | Phase 1 scope and demo acceptance criteria |
| [DEV_SETUP.md](docs/DEV_SETUP.md) | Development environment setup |

---

## License

Apache 2.0 — see [LICENSE](LICENSE).

---

## Status

🟢 **Phase 1 — Core implementation complete.** All 7 capabilities, orchestration layer, LLM client, proactive loop, and onboarding flow are built and tested. Both text and voice modes verified end-to-end with live Ollama (qwen2.5:7b). Full voice-to-voice conversation verified on macOS (Whisper STT + LLM + macOS say TTS). CI pipeline active on Linux (lint + 230 tests + Piper TTS validation on ubuntu-latest).
