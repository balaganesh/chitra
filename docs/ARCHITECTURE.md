# Chitra — Architecture

## Overview

Chitra is built on Linux kernel with a completely custom userspace. There is no GUI compositor, no window manager, no app framework, no desktop environment. The AI Orchestration Core is the primary userspace process. It boots directly and is the only interface between the user and the machine.

The architecture has five layers. Each layer has a single clear responsibility. Layers communicate only with adjacent layers. No layer reaches across or bypasses another.

---

## The Five Layers

```
┌─────────────────────────────────────┐
│       Conversational Interface      │  Layer 5
├─────────────────────────────────────┤
│       AI Orchestration Core         │  Layer 4
├─────────────────────────────────────┤
│         Capability Modules          │  Layer 3
├─────────────────────────────────────┤
│       Hardware Abstraction          │  Layer 2
├─────────────────────────────────────┤
│          Linux Kernel               │  Layer 1
└─────────────────────────────────────┘
```

---

## Layer 1 — Linux Kernel

The foundation. Manages CPU, memory, storage, audio hardware, input devices. Chitra does not modify the kernel. We use a standard Linux distribution as the base — Ubuntu Server 24.04 LTS minimal install, chosen specifically because it boots without a desktop environment.

The kernel is invisible to the user entirely.

---

## Layer 2 — Hardware Abstraction

A thin set of interfaces that give the Orchestration Core clean, consistent access to hardware without knowledge of specific hardware details.

Responsibilities:
- Microphone input stream
- Speaker output stream
- Storage read/write for capability data
- System state queries — time, date, battery

This layer uses standard Linux interfaces — ALSA or PipeWire for audio, standard filesystem for storage. No custom drivers. No hardware-specific code in upper layers.

---

## Layer 3 — Capability Modules

The working layer of Chitra. Each capability is an independent module — a self-contained process or service with a clean API. The Orchestration Core is the only caller. Capabilities do not call each other. Capabilities have no UI of their own.

Phase 1 capabilities: Voice I/O, Contacts, Calendar, Reminders & Alarms, Tasks, Memory, System State.

Each capability exposes a simple function-style API:
- A defined set of actions it can perform
- A defined input schema for each action
- A defined output schema for each action

The full specification of each capability is in `CAPABILITIES.md`.

---

## Layer 4 — AI Orchestration Core

The brain of Chitra. Boots as the primary process on startup. Never exits. Has four responsibilities:

**1. Input handling**
Receives text from the Voice I/O capability — either typed directly by the user (text mode) or transcribed from speech (voice mode). Both input modes are first-class. The Orchestration Core receives identical text output from both and does not distinguish between them. Passes it into the reasoning pipeline.

**2. Context assembly**
Before every LLM call, assembles full context:
- Current system state — time, date, battery
- Relevant memory — user preferences, relationship context, recent observations
- Active reminders and upcoming calendar events
- Current conversation history (last 10 turns, configurable)

This assembled context is injected into the LLM prompt as a structured system message. The model does not remember the user — the Memory capability does, and briefs the model fresh every single call.

**3. LLM reasoning**
Sends assembled context + user input to the local LLM via Ollama. The LLM returns structured JSON containing:
- Detected intent
- Action to execute if any (capability + action + parameters)
- Conversational response
- Any new memory entries to store

The Orchestration Core parses this JSON with robust error handling. If the LLM returns malformed JSON, the Orchestration Core retries the call with an explicit correction prompt rather than crashing.

**4. Action execution**
If the LLM returns an action, the Orchestration Core calls the appropriate capability module, receives the result, and if needed makes a second LLM call to formulate the conversational response incorporating that result.

**Proactive Loop**

Separate from the input handling pipeline, the Orchestration Core runs a background loop on a 60-second tick (configurable) that:
- Checks triggered reminders and alarms
- Reviews upcoming calendar events
- Reviews memory for contextually relevant observations
- Decides — via a lightweight LLM call — whether anything is worth surfacing to the user unprompted

If yes, it initiates a conversation. The user didn't ask — Chitra noticed.

This loop is the source of the anticipating behavior central to the Chitra vision.

---

## Layer 5 — Conversational Interface

The only thing the user ever sees. A minimal terminal display showing the conversation — what the user said, what Chitra said. No menus. No buttons. No navigation elements.

For Phase 1 this is a simple text display with voice I/O as the primary interaction mode. The screen exists so a viewer watching the demo can follow along.

---

## Full Interaction Flow

A single interaction, end to end:

```
User input — one of two paths:
  [Text mode]  → user types at terminal prompt → text returned directly
  [Voice mode] → user speaks → VAD detects speech → Whisper STT → text
    ↓
Voice I/O returns: {"text": string, "confidence": float}
    ↓
Orchestration Core receives text (identical from both modes)
    ↓
Context Assembly
  — Memory capability: fetch relevant personal context
  — System State capability: current time, date
  — Calendar capability: upcoming events
  — Active reminders
  — Last 10 turns of conversation history
    ↓
LLM call — intent understanding + response/action decision
    ↓
[If malformed JSON] → retry with correction prompt
    ↓
[If action] → Capability module called → result returned
    ↓
[If new memory entries] → Memory.store() called immediately
    ↓
[If needed] → Second LLM call — formulate conversational response
    ↓
Voice I/O — text to speech → speaker (both modes)
    ↓
Conversational Interface — display updated (both modes)
```

---

## Proactive Loop Flow

```
Background loop ticks every 60 seconds (configurable)
    ↓
Check triggered reminders → any fired?
Check calendar → anything upcoming within threshold?
Check memory → any observation worth surfacing?
    ↓
Lightweight LLM call — is there anything worth telling the user right now?
    ↓
[If yes] → Formulate conversational message → Voice I/O → speak
[If no] → Sleep until next tick
```

---

## Key Architectural Principles

**AI as the only orchestrator.** No capability calls another capability. All coordination happens through the Orchestration Core. This keeps capabilities simple, testable, and replaceable.

**Context is assembled fresh every call.** The LLM has no persistent state. Every call is stateless from the model's perspective. All continuity comes from the Memory capability and conversation history injected at runtime.

**Capabilities are replaceable.** Each capability has a defined API contract. The implementation behind that contract can be rewritten without touching the Orchestration Core.

**The LLM is replaceable.** The LLM client is written as a clean interface. Swapping the underlying model (e.g. switching from qwen2.5:7b to a newer release) is a configuration change, not a code change. As local models improve rapidly, Chitra benefits without architectural rework.

**Robust failure handling.** The Orchestration Core never crashes due to malformed LLM output. All capability errors return structured error JSON. The system degrades gracefully.

**No internet dependency.** Every layer operates entirely on-device. The LLM runs locally via Ollama. All data is local. No external calls of any kind in Phase 1.

**Linux compatibility is non-negotiable.** Development happens on macOS but every library and interface choice must run on Linux. macOS-specific APIs are never used.

---

## What This Architecture Is Not

It is not a voice assistant running on top of a traditional OS. There is no traditional OS userspace beneath it — no desktop, no app framework, no launcher.

It is not an agent framework calling cloud APIs. Everything is local.

It is not an app platform. There is no concept of installing or launching apps. Capabilities are OS primitives, not apps.

---

*For capability specifications see `CAPABILITIES.md`*
*For memory layer design see `MEMORY_DESIGN.md`*
*For technology choices see `TECH_STACK.md`*
*For phase 1 boundaries see `PHASE1_SCOPE.md`*
