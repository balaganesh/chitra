# Chitra — Technology Stack

## Guiding Principles for Technology Choices

Every technology chosen must satisfy three criteria:

1. **Runs locally** — no cloud dependency, no external API calls
2. **Linux compatible** — must run on Linux, even if developed on macOS
3. **Phase 1 appropriate** — proven, stable, not experimental. We are building a foundation, not exploring bleeding edge tools.

---

## Development Environment

**Machine:** MacBook Air M4 2025, macOS
**Target Runtime:** Linux x86_64 (laptop or desktop hardware)
**Approach:** Develop and test on macOS, ensure Linux compatibility throughout. No macOS-specific libraries or APIs anywhere in the codebase.

---

## Operating System Base

**Linux Distribution:** Ubuntu Server 24.04 LTS (minimal install)

Chosen because:
- No desktop environment installed by default
- Well documented, large community, stable
- LTS release means stability over cutting edge
- Boot directly into Chitra's Orchestration Core — no display manager, no GUI

On the development Mac, a Linux VM (UTM) is used to test Linux compatibility continuously during development.

---

## Primary Language

**Python 3.11+**

Chosen because:
- Best ecosystem for AI, speech, and audio libraries
- Readable and maintainable for an open source project
- Strong async support for the Orchestration Core's concurrent responsibilities
- All required libraries have mature Python bindings
- Appropriate for the scale of Phase 1

---

## AI Orchestration Core

**Language:** Python 3.11+
**Concurrency:** Python asyncio — for handling simultaneous input listening, proactive loop, and capability calls without blocking
**Process management:** Systemd service — Orchestration Core registered as a systemd unit, starts at boot, restarts on failure

---

## Local LLM

**Runtime:** Ollama
**Phase 1 model:** Llama 3.1 8B or Mistral 7B — final choice made during performance testing on target hardware
**Interface:** Ollama local REST API (localhost only, never exposed externally)

**Model swappability — critical design requirement:**
The LLM client is written as a clean, swappable interface. Changing the underlying model is a configuration change (updating a model name in config), not a code change. Local model capabilities and performance are improving rapidly — Chitra benefits from new models as they emerge without any architectural rework. Claude Code must implement this as a strict interface with the model name as an environment variable or config value.

**Important architectural note:**
Ollama is a system-level daemon, not a user application. It is started at boot via systemd before the Orchestration Core starts. The user never interacts with it directly. It is an implementation detail of the LLM inference layer.

In future phases, Ollama will be replaced by a purpose-built native inference capability that is a proper Chitra primitive. For Phase 1, Ollama is the pragmatic and correct choice.

**LLM prompt structure:**
Every LLM call is structured as:
- System prompt: Chitra identity + assembled context (Memory + System State)
- Conversation history: last 10 turns (configurable)
- User message: current input

The LLM is instructed to return structured JSON. The Orchestration Core implements robust JSON parsing with retry on malformed output — see ARCHITECTURE.md and CLAUDE.md.

---

## Speech To Text

**Library:** OpenAI Whisper (local, runs entirely on device)
**Model size:** Whisper Base or Small — balance of accuracy and speed on M4/Linux hardware
**Interface:** Python whisper library, called directly from Voice I/O capability

Whisper runs fully offline. No audio ever leaves the device.

**Known Phase 1 latency:**
Whisper introduces 1–3 seconds of processing time after the user speaks. This is an accepted Phase 1 limitation. As local STT models improve (they are improving rapidly), the Voice I/O capability's STT implementation can be swapped without touching any other component.

---

## Text To Speech

**Library:** Piper TTS
**Voice:** English neural voice model (natural sounding, runs on CPU)
**Interface:** Python subprocess call or Piper Python bindings

Piper is chosen because it produces natural-sounding voice, runs entirely locally, has low latency, and works on both macOS and Linux.

---

## Voice Activity Detection

**Library:** Silero VAD
**Purpose:** Detects when the user starts and stops speaking so Whisper is only called when there is actual speech — not continuously
**Interface:** Python, runs on CPU

---

## Voice Activation

**Wake word:** "Chitra" — user says the OS name to activate listening
**Keyboard trigger:** Spacebar — fallback activation for Phase 1 and demo recording
**Phase 1 implementation:** Keyboard trigger is primary for Phase 1 due to simplicity and reliability. Wake word detection is noted as a future phase item.

---

## Audio I/O

**Library:** PyAudio or sounddevice
**Purpose:** Microphone capture and speaker playback
**Linux backend:** ALSA or PipeWire (PipeWire preferred on modern Linux)

---

## Data Storage

**Database:** SQLite via Python sqlite3 standard library
**Development path:** `~/.chitra/data/`
**Production path:** `/var/chitra/data/`
**Path configuration:** Storage path is set via environment variable `CHITRA_DATA_DIR` — defaults to `~/.chitra/data/` if not set. This allows seamless switching between development and production without code changes.

**One database per capability:**
```
contacts.db
calendar.db
reminders.db
tasks.db
memory.db
```

SQLite chosen because:
- Zero configuration
- No separate database server process
- File-based — easy to backup, inspect, and migrate
- More than sufficient for Phase 1 data volumes

---

## Conversational Interface Display

**Phase 1:** Simple terminal output using Python rich library
**Purpose:** Shows conversation history so a demo viewer can follow along
**Design:** Minimal — user input and Chitra response, clean typography, no decorative elements

This is the only visual element in Chitra. It exists for the demo recording. It is not a UI in the traditional sense — the user never navigates it.

---

## Dependency Management

**Tool:** Python venv + pip with requirements.txt
**Approach:** Pinned versions for all dependencies to ensure reproducible builds

---

## License

**Apache 2.0**

Chosen because:
- Maximum adoption — anyone can use, modify, and build commercially on Chitra
- Explicit patent protection — contributors cannot later sue users for patent infringement related to their contributions
- Appropriate for an OS-level project with ambitions to become a platform others build on

---

## Boot Sequence

On Linux target hardware, the boot sequence is:

```
Linux kernel boots
    ↓
Systemd starts
    ↓
Ollama daemon starts (systemd unit)
    ↓
Chitra Orchestration Core starts (systemd unit, depends on Ollama)
    ↓
Voice I/O capability initializes
    ↓
All other capabilities initialize
    ↓
[First run] Onboarding conversation begins
[Subsequent runs] Proactive loop starts, Chitra speaks greeting
    ↓
System ready — listening for "Chitra" wake word or spacebar
```

No login prompt. No desktop. No shell visible to the user. The device boots directly into Chitra.

---

## What We Are Deliberately Not Using

- Any GUI framework — no Qt, no GTK, no Electron
- Any web framework — no Flask, no FastAPI for user-facing interfaces
- Any cloud SDK or external API client
- Any Android framework or compatibility layer
- Any macOS-specific library

---

## Future Phase Considerations (Not Phase 1)

- Native inference capability replacing Ollama
- Telephony capability via ModemManager on Linux phone hardware
- Hardware port to PinePhone or similar Linux phone
- Always-on wake word detection
- Multi-language STT/TTS support
- Faster STT alternatives if Whisper latency remains problematic

---

*For system architecture see `ARCHITECTURE.md`*
*For capability specifications see `CAPABILITIES.md`*
*For phase 1 boundaries see `PHASE1_SCOPE.md`*
