# Chitra — Phase 1 Scope

## Objective

Build a working, demonstrable version of Chitra that proves the architecture is real and the vision is achievable. The output is a recorded demo — shareable online — that makes a viewer feel they are seeing a fundamentally different kind of computing.

Phase 1 is not feature complete. It is proof of concept. Depth and correctness over breadth.

## Target Hardware

Development machine: MacBook Air M4 2025 running macOS. All code must be Linux-compatible — no macOS-specific libraries or dependencies.

Runtime target: Linux on laptop or desktop hardware. Phase 1 does not require a phone form factor.

## First Run — Onboarding

When Chitra boots for the first time it has no knowledge of the user. Before normal operation begins, Chitra conducts a short conversational onboarding to seed the Memory capability with initial context.

Onboarding covers:
- User's name
- Preferred input mode (text or voice)
- A few key people in their life and their relationship
- Basic work schedule and routine
- Any immediate preferences the user wants Chitra to know

Onboarding is entirely conversational — no forms, no settings screens. Chitra asks, the user answers, Memory stores. When onboarding is complete, normal operation begins.

On subsequent boots, onboarding is skipped. Chitra already knows the user.

## The Demo Scenario — Acceptance Criteria

Phase 1 is complete when this scenario runs end to end without failure.

**Important note on interactions:** Chitra's awareness of contact interactions (e.g. "it's been 5 days since you called your mother") is based on interactions the user has explicitly noted to Chitra — not verified call history from a telephony system. Telephony is not part of Phase 1. Chitra knows what the user tells it.

---

**Scene: Morning**

Chitra boots. No home screen. The conversational interface appears — minimal, just the dialogue. The user says "Chitra" to activate. Chitra responds:

*"Good morning Bala. You have a team meeting at 10. It's 8:47. You mentioned last week you wanted to call your mother more often — it's been 5 days since you last noted a call with her."*

Bala says: *"Set a reminder to call her at 7 this evening. Also remind me 15 minutes before the meeting."*

Chitra: *"Done. Reminder set for 7pm for your mother. Meeting reminder set for 9:45."*

A few moments later, unprompted:

*"You have no tasks scheduled for this afternoon. You had noted wanting to review your project notes this week — want me to remind you at 2pm?"*

Bala: *"Yes."*

Chitra: *"Reminder set for 2pm — review project notes."*

---

This scenario demonstrates: proactive behavior, memory of stated preferences, task chaining, natural conversation, and zero UI navigation.

## Phase 1 Capabilities — In Scope

**Voice I/O**
Two first-class input modes: text (user types at terminal) and voice (microphone → Whisper STT). Both are primary — text is not a fallback. Users can switch freely between modes. Text to speech for all Chitra responses in both modes. This is the only human interface.

**Contacts**
Local contact store. Name, relationship type, phone, email, notes, last interaction date (user-noted). Queryable by the AI Orchestration Core.

**Calendar**
Store and query events. Basic — title, date, time. Chitra references upcoming events proactively.

**Reminders & Alarms**
Create, store, and trigger time-based reminders. The proactive loop checks these and surfaces them conversationally.

**Tasks**
Create and store tasks with optional due dates and context. The proactive loop references these when relevant.

**Memory**
The personal knowledge layer. Stores facts, preferences, relationship context, and observations the user has shared. Injected as context into every LLM call. This is what makes Chitra feel like it knows you.

**System State**
Current time, date, battery level. Always available to the Orchestration Core.

**Local LLM**
Runs entirely on device via Ollama. Model: qwen2.5:7b (selected for best JSON instruction following at 7B class). Alternatives: llama3.1:8b, mistral:7b. The LLM client is written as a clean swappable interface so replacing the model is a configuration change, not a code change. No external API calls.

## Phase 1 — Explicitly Out of Scope

- Telephony — no calls or SMS in Phase 1
- Internet access — no web search, no external APIs, no cloud
- Media playback
- Navigation or maps
- Any graphical UI beyond the minimal conversational display
- Multi-user support
- Security or encryption layer
- App installation or any app framework of any kind
- Natural language learning or model fine-tuning
- Wake word detection (text input and spacebar activation are Phase 1 alternatives)

## Known Phase 1 Limitations

**STT Latency:** Whisper introduces 1-3 seconds of processing time after the user speaks before Chitra responds. This is acceptable for Phase 1. Users who prefer zero-latency input can use text mode at any time. Local model capabilities and speed are improving rapidly — the LLM client architecture allows model replacement as better options emerge.

## What Phase 1 Must Feel Like

A viewer watching the demo should feel: *"This is the future I didn't know I wanted."*

Chitra should feel like a person, not a tool. It should speak first when it has something relevant to say. It should remember things the user told it days ago and reference them naturally. It should never ask the user to navigate anywhere or make a choice from a list.

If at any point during build a decision makes Chitra feel more like a voice-controlled app launcher and less like a companion — that decision is wrong. Refer to VISION.md.

## Definition of Done

- Demo scenario runs end to end on Linux
- Onboarding flow complete and functional
- All Phase 1 capabilities functional and stable
- Local LLM running fully on device, no internet required
- Conversational interface is the only interface
- Both text and voice input modes functional as first-class input methods
- Code is clean, documented, and ready for open source publication under Apache 2.0
- All documents complete and accurate

*For architecture see `ARCHITECTURE.md`*
*For capability specifications see `CAPABILITIES.md`*
