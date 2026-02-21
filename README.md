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

**AI as primitive.** Every capability is built to be consumed by AI — not by a human pressing a button. Telephony, reminders, contacts, memory — these are OS primitives, not apps.

**Memory.** Chitra knows you. Your people, your preferences, your routines. Stored privately on device. Referenced naturally in conversation. Over time, Chitra doesn't just respond — it anticipates.

**No UI except conversation.** If a feature requires a screen full of options, it is not designed correctly.

---

## Phase 1 — Proof of Concept

Phase 1 builds a working, demonstrable version of Chitra on Linux hardware. The goal is a recorded demo that makes a viewer feel they are seeing a fundamentally different kind of computing.

**Phase 1 capabilities:**
- Voice I/O — speech to text, text to speech, conversational display
- Contacts — local store of people and relationships
- Calendar — events and schedule
- Reminders & Alarms — time-based triggers surfaced conversationally
- Tasks — things to do, referenced proactively
- Memory — the personal knowledge layer, injected into every AI call
- System State — time, date, battery

**Phase 1 constraints:**
- Runs entirely on Linux, no internet dependency
- Local LLM via Ollama (Llama 3.1 8B / Mistral 7B)
- No telephony, no media, no web access — contained and deep

---

## Architecture

```
┌─────────────────────────────────────┐
│       Conversational Interface      │
├─────────────────────────────────────┤
│       AI Orchestration Core         │
├─────────────────────────────────────┤
│         Capability Modules          │
├─────────────────────────────────────┤
│       Hardware Abstraction          │
├─────────────────────────────────────┤
│          Linux Kernel               │
└─────────────────────────────────────┘
```

Full architecture documentation in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

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

Requires Python 3.11+, Ollama, and a Linux or macOS environment.

---

## Documentation

| Document | Description |
|---|---|
| [VISION.md](docs/VISION.md) | The why — principles and philosophy |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture and interaction flows |
| [CAPABILITIES.md](docs/CAPABILITIES.md) | Capability module API contracts |
| [MEMORY_DESIGN.md](docs/MEMORY_DESIGN.md) | Memory layer design |
| [TECH_STACK.md](docs/TECH_STACK.md) | Technology choices and rationale |
| [PHASE1_SCOPE.md](docs/PHASE1_SCOPE.md) | Phase 1 scope and demo acceptance criteria |
| [DEV_SETUP.md](docs/DEV_SETUP.md) | Development environment setup |

---

## License

Apache 2.0 — see [LICENSE](LICENSE).

---

## Status

🟡 **Pre-development** — Architecture and documentation complete. Build starting.
