# Chitra — Capability Modules

## Overview

Each capability is an independent module with a defined API contract. The AI Orchestration Core is the only caller. Capabilities do not call each other. Capabilities have no UI. Each capability owns its own local data storage.

The API contract for each capability defines:
- **Actions** — what the Orchestration Core can ask it to do
- **Input** — what parameters each action accepts
- **Output** — what each action returns

All inputs and outputs are structured JSON. All data is stored locally on device. Validation and field limits are implementation details handled within each capability's code — not specified here.

---

## Capability 1 — Voice I/O

The conversational interface layer. Handles all input and output — both voice and text. This is the only way the user interacts with Chitra.

**Two input modes — both first-class:**

- **Text mode** — user types at a terminal prompt. Zero latency, always available. This is not a fallback — it is a full, primary input method. Many users will prefer text, especially when voice latency is noticeable or when speaking is not practical.
- **Voice mode** — user speaks, Chitra listens via microphone, transcribes via Whisper STT. Primary mode for hands-free and device use cases.

The user can switch modes at any time — conversationally ("switch to text", "switch to voice") or via a keyboard shortcut. The Orchestration Core receives identical output from both modes and never knows or cares which mode produced the text.

**Responsibilities**
- Accept text input from terminal prompt (text mode)
- Capture microphone input and transcribe via STT (voice mode)
- Detect when the user is speaking (voice activity detection, voice mode only)
- Convert text to speech (TTS) — used in both modes for Chitra's spoken responses
- Play audio response through speaker
- Update the conversational display (rich terminal)
- Manage input mode switching

**Actions**

`listen()`
Returns user input as text. Behavior depends on current input mode:
- **Text mode:** prompts user at terminal, returns typed text with confidence 1.0
- **Voice mode:** activates microphone, detects speech via VAD, transcribes via Whisper STT
```json
Input: none
Output: {
  "text": string,
  "confidence": float
}
```

`speak(text)`
Converts text to speech and plays through speaker. In text mode, TTS is skipped — the user reads Chitra's response on screen. In voice mode, blocks until audio playback is complete.
```json
Input: {
  "text": string
}
Output: {
  "status": "done"
}
```

`display(user_text, chitra_text)`
Updates the conversational interface display with the latest exchange.
```json
Input: {
  "user_text": string,
  "chitra_text": string
}
Output: {
  "status": "done"
}
```

`set_input_mode(mode)`
Switches between text and voice input modes.
```json
Input: {
  "mode": "text" | "voice"
}
Output: {
  "status": "done",
  "mode": "text" | "voice"
}
```

**Technology**
- STT: OpenAI Whisper (local, runs on device) — voice mode only
- TTS: Piper TTS (local, runs on device, natural voice) — both modes
- Voice activity detection: Silero VAD — voice mode only
- Terminal display: rich library

---

## Capability 2 — Contacts

Local store of people the user knows. Chitra references this to understand who the user is talking about and surface relationship context.

**Data Model**
```json
Contact {
  id: string,
  name: string,
  relationship: string,
  phone: string | null,
  email: string | null,
  notes: string,
  last_interaction: date,
  communication_preference: string
}
```

`last_interaction` reflects the date the user last noted an interaction with this person — not a verified call record. Chitra knows what the user tells it.

**Actions**

`get(name)`
Finds a contact by name or partial name.
```json
Input: { "name": string }
Output: Contact | null
```

`list()`
Returns all contacts.
```json
Input: none
Output: Contact[]
```

`create(contact)`
Creates a new contact.
```json
Input: Contact (id auto-generated)
Output: Contact
```

`update(id, fields)`
Updates specific fields on an existing contact.
```json
Input: {
  "id": string,
  "fields": partial Contact
}
Output: Contact
```

`note_interaction(id)`
Updates last_interaction date to now.
```json
Input: { "id": string }
Output: Contact
```

`get_neglected(days_threshold)`
Returns contacts whose last_interaction is older than the threshold. Used by proactive loop.
```json
Input: { "days_threshold": integer }
Output: Contact[]
```

---

## Capability 3 — Calendar

Local store of events and schedule. Chitra references this to understand what the user has coming up and surface relevant context proactively.

**Data Model**
```json
Event {
  id: string,
  title: string,
  date: date,
  time: time,
  duration_minutes: integer,
  notes: string,
  participants: string[]
}
```

**Actions**

`get_upcoming(hours_ahead)`
Returns events scheduled within the next N hours.
```json
Input: { "hours_ahead": integer }
Output: Event[]
```

`get_today()`
Returns all events for today.
```json
Input: none
Output: Event[]
```

`create(event)`
Creates a new calendar event.
```json
Input: Event (id auto-generated)
Output: Event
```

`get_range(start_date, end_date)`
Returns events within a date range.
```json
Input: {
  "start_date": date,
  "end_date": date
}
Output: Event[]
```

---

## Capability 4 — Reminders & Alarms

Time-based triggers. When a reminder fires, the proactive loop picks it up and surfaces it conversationally.

**Data Model**
```json
Reminder {
  id: string,
  text: string,
  trigger_at: datetime,
  repeat: string | null,
  status: "pending" | "fired" | "dismissed",
  contact_id: string | null
}
```

**Actions**

`create(reminder)`
Creates a new reminder.
```json
Input: Reminder (id auto-generated)
Output: Reminder
```

`get_fired()`
Returns all reminders whose trigger_at has passed and status is "pending". Called by proactive loop on every tick.
```json
Input: none
Output: Reminder[]
```

`dismiss(id)`
Marks a reminder as dismissed after it has been surfaced to the user.
```json
Input: { "id": string }
Output: Reminder
```

`list_upcoming(hours_ahead)`
Returns pending reminders due within N hours.
```json
Input: { "hours_ahead": integer }
Output: Reminder[]
```

`delete(id)`
Deletes a reminder.
```json
Input: { "id": string }
Output: { "status": "deleted" }
```

---

## Capability 5 — Tasks

Things the user needs to do. Chitra references tasks proactively when the user has free time or when tasks are overdue.

**Data Model**
```json
Task {
  id: string,
  title: string,
  notes: string,
  due_date: date | null,
  status: "pending" | "done",
  priority: "high" | "normal" | "low",
  created_at: datetime
}
```

**Actions**

`create(task)`
Creates a new task.
```json
Input: Task (id auto-generated)
Output: Task
```

`list(status)`
Returns tasks filtered by status.
```json
Input: { "status": "pending" | "done" | "all" }
Output: Task[]
```

`complete(id)`
Marks a task as done.
```json
Input: { "id": string }
Output: Task
```

`get_overdue()`
Returns pending tasks past their due date. Used by proactive loop.
```json
Input: none
Output: Task[]
```

`get_due_today()`
Returns pending tasks due today.
```json
Input: none
Output: Task[]
```

---

## Capability 6 — Memory

The most important capability. Stores everything Chitra knows about the user — stated preferences, observed patterns, relationship context, personal facts. Injected as context into every LLM call.

Full design in `MEMORY_DESIGN.md`. API contract summary here.

**Data Model**
```json
MemoryEntry {
  id: string,
  category: "preference" | "fact" | "observation" | "relationship",
  subject: string,
  content: string,
  confidence: float,
  source: "stated" | "inferred",
  contact_id: string | null,
  created_at: datetime,
  last_referenced: datetime,
  active: boolean
}
```

**Actions**

`store(entry)`
Saves a new memory entry.
```json
Input: MemoryEntry (id auto-generated)
Output: MemoryEntry
```

`get_context()`
Returns all memory entries formatted as a context block for LLM injection. Called on every Orchestration Core tick before LLM call.
```json
Input: none
Output: {
  "context_block": string
}
```

`search(query)`
Returns memory entries relevant to a topic or subject.
```json
Input: { "query": string }
Output: MemoryEntry[]
```

`update(id, content)`
Updates an existing memory entry.
```json
Input: {
  "id": string,
  "content": string
}
Output: MemoryEntry
```

`deactivate(id)`
Soft deletes a memory entry — sets active to false. Entry is never injected into context again but is retained in storage.
```json
Input: { "id": string }
Output: { "status": "deactivated" }
```

---

## Capability 7 — System State

Always-available device and environment context. Injected into every LLM call alongside Memory.

**Actions**

`get()`
Returns current system state snapshot.
```json
Input: none
Output: {
  "datetime": datetime,
  "day_of_week": string,
  "battery_percent": integer,
  "time_of_day": "morning" | "afternoon" | "evening" | "night"
}
```

---

## Capability Interaction Rules

These rules are non-negotiable and must be respected in all build sessions:

1. Capabilities never call other capabilities directly
2. All capability calls go through the Orchestration Core
3. Each capability manages its own data — no capability reads another's data store
4. All capability data is stored locally — no network calls from any capability
5. All inputs and outputs are JSON
6. Every action must handle errors gracefully and return a structured error response rather than crashing

---

*For memory layer detail see `MEMORY_DESIGN.md`*
*For orchestration logic see `ARCHITECTURE.md`*
*For phase 1 boundaries see `PHASE1_SCOPE.md`*
