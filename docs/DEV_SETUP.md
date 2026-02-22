# Chitra — Development Environment Setup

## Overview

Development happens on macOS (MacBook Air M4). The target runtime is Linux. This guide sets up everything needed to develop, test, and run Chitra locally on the Mac, with Linux compatibility maintained throughout.

---

## Prerequisites

Before starting, ensure the following are installed on your Mac:

**Homebrew** — macOS package manager
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**Python 3.11+**
```bash
brew install python@3.11
```

**Git**
```bash
brew install git
```

---

## Step 1 — Clone the Repository

```bash
git clone https://github.com/[your-username]/chitra.git
cd chitra
```

---

## Step 2 — Python Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Step 3 — Install Ollama

Ollama runs the local LLM on device. It is a system-level daemon, not a user application.

```bash
brew install ollama
```

Start Ollama as a background service:
```bash
ollama serve &
```

Pull the Phase 1 model:
```bash
ollama pull qwen2.5:7b
```

Verify it works:
```bash
ollama run qwen2.5:7b "say hello"
```

To switch models, update `CHITRA_LLM_MODEL` in your `.env` file. No code changes required.

---

## Step 4 — Install Audio Dependencies

**PortAudio** — required by PyAudio for microphone and speaker access:
```bash
brew install portaudio
```

**FFmpeg** — required by Whisper for audio processing:
```bash
brew install ffmpeg
```

---

## Step 5 — Install Piper TTS

Run the setup script to download the Piper binary and English neural voice model:
```bash
python scripts/setup_piper.py
```

This downloads Piper into the path specified by `CHITRA_DATA_DIR`. Safe to run multiple times.

---

## Step 6 — Configure Environment

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` to set your configuration:
```bash
# Data directory — use ~/.chitra for development, /var/chitra for production
CHITRA_DATA_DIR=~/.chitra

# LLM model — change this to swap models, no code change required
CHITRA_LLM_MODEL=qwen2.5:7b

# Proactive loop tick interval in seconds
CHITRA_PROACTIVE_INTERVAL=60

# Conversation history turns to include in LLM context
CHITRA_HISTORY_TURNS=10
```

---

## Step 7 — Initialize Data Storage

Create data directories and initialize SQLite databases:
```bash
python scripts/setup_storage.py
```

This creates:
```
~/.chitra/
  data/
    contacts.db
    calendar.db
    reminders.db
    tasks.db
    memory.db
  tts/
    piper binary
    voice model
  logs/
    chitra.log
```

---

## Step 8 — Run the Test Suite

Before starting Chitra, verify all capabilities are working:
```bash
python -m pytest tests/ -v
```

All tests should pass before proceeding.

---

## Step 9 — Start Chitra

```bash
python main.py
```

**First run:** Chitra starts an onboarding conversation to learn about you. Answer the questions — this seeds the Memory capability with your initial context. Onboarding runs once only.

**Subsequent runs:** Chitra boots directly into normal operation, speaks a greeting, and begins accepting input.

**Input modes:** Chitra starts in text mode by default — type at the terminal prompt. Switch to voice mode conversationally ("switch to voice") or via keyboard shortcut. In voice mode, press spacebar to begin speaking. Both modes are first-class.

To exit:
```bash
Ctrl+C
```

---

## Linux VM Setup (for Linux compatibility testing)

To test on Linux without separate hardware:

**Install UTM** (free, macOS virtualization):
```
https://mac.getutm.app
```

**Create Ubuntu Server 24.04 VM:**
- Download Ubuntu Server 24.04 LTS ISO
- Create new VM in UTM, allocate 4GB RAM minimum, 20GB storage
- Boot from ISO, complete minimal install
- Do not install desktop environment

**In the VM, repeat Steps 1–9 using Linux equivalents:**

```bash
# Replace brew with apt
sudo apt update
sudo apt install python3.11 python3.11-venv git ffmpeg portaudio19-dev -y

# Ollama on Linux
curl -fsSL https://ollama.com/install.sh | sh

# Everything else is identical
```

Run Chitra in the VM to verify Linux compatibility before any major commit.

---

## Project Structure

```
chitra/
  main.py                       # Entry point — boots Orchestration Core
  .env.example                  # Example environment configuration
  requirements.txt              # Pinned Python dependencies
  orchestration/
    core.py                     # AI Orchestration Core
    context.py                  # Context assembly for LLM calls
    proactive.py                # Proactive loop (60s tick)
  capabilities/
    voice_io.py                 # Voice I/O capability
    contacts.py                 # Contacts capability
    calendar.py                 # Calendar capability
    reminders.py                # Reminders & Alarms capability
    tasks.py                    # Tasks capability
    memory.py                   # Memory capability
    system_state.py             # System State capability
  llm/
    client.py                   # Ollama interface (swappable)
    prompts.py                  # LLM prompt templates
  storage/
    schema.py                   # SQLite schema definitions
  onboarding/
    flow.py                     # First run onboarding conversation
  scripts/
    setup_piper.py              # Piper TTS setup
    setup_storage.py            # Storage initialization
    seed_demo.py                # Demo scenario seed data
  tests/
    test_orchestration.py       # Orchestration integration tests (54 tests)
    test_onboarding.py          # Onboarding flow tests (26 tests)
    test_capabilities.py        # Capability unit tests (94 tests)
    test_memory.py              # Memory-specific tests (38 tests)
  docs/
    VISION.md
    ARCHITECTURE.md
    CAPABILITIES.md
    MEMORY_DESIGN.md
    TECH_STACK.md
    PHASE1_SCOPE.md
    DEV_SETUP.md
    CLAUDE.md
  LICENSE                       # Apache 2.0
  README.md
```

---

## Common Issues

**Microphone not working on Mac**
Grant Terminal microphone permission in System Settings → Privacy & Security → Microphone.

**Ollama not responding**
Check it is running: `ollama list`. If not, restart: `ollama serve &`

**Piper voice sounds wrong**
Re-run `python scripts/setup_piper.py` to redownload the voice model.

**Storage permission error**
Check `~/.chitra/` directory permissions: `ls -la ~/.chitra/`

**Model not found**
Ensure you pulled the model matching `CHITRA_LLM_MODEL` in your `.env`: `ollama pull qwen2.5:7b`

---

*For architecture overview see `ARCHITECTURE.md`*
*For technology choices see `TECH_STACK.md`*
