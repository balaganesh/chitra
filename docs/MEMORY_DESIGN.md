# Chitra — Memory Design

## Overview

Memory is what separates Chitra from a voice assistant. It is the capability that makes Chitra feel like it knows you — because it does. Everything the user has shared, every preference stated, every pattern observed, lives here permanently on device.

The local LLM has no persistent state between conversations. Memory solves this. Before every LLM call, the Orchestration Core pulls a context block from Memory and injects it into the system prompt. The model is briefed fresh every single time. From the model's perspective it always knows the user — because Chitra always tells it what it needs to know.

The name Chitra itself is drawn from Chitragupta — the keeper of records who remembers every deed of every soul. Memory is not a feature. It is the soul of this OS.

---

## What Memory Stores

Memory stores four categories of entry:

**Preference**
Things the user has explicitly stated they like, dislike, or want.
- *"I don't like meetings before 9am"*
- *"I prefer concise responses"*
- *"I like to review my tasks in the morning"*

**Fact**
Concrete factual information about the user's life.
- *"Works at Flipkart in Bengaluru"*
- *"Has a team meeting every Monday at 10am"*
- *"Mother's name is [name]"*

**Observation**
Patterns Chitra has noticed over time, with lower confidence than stated facts.
- *"Usually starts conversations in the morning around 9am"*
- *"Tends to ask for task reminders on Sunday evenings"*

**Relationship**
Context about people in the user's life, linked to a contact.
- *"Mother prefers calls after 7pm, last noted contact 5 days ago"*
- *"Ravi is a colleague, they collaborate frequently"*
- *"Has not noted contact with [name] in over two weeks"*

Note: relationship memories about interaction recency reflect what the user has told Chitra — not verified communication records.

---

## Data Model

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

**Confidence scale:**
- 1.0 — explicitly stated by user
- 0.5–0.9 — inferred or observed, treat as likely but not certain
- Below 0.5 — uncertain, use to inform behavior quietly, never state as fact

---

## How Memory Is Created

Memory entries are created in three ways:

**1. Explicit statement**
The user directly tells Chitra something about themselves.

*"Remember that I don't like being interrupted before 10am"*
*"My mother prefers calls in the evening"*

The Orchestration Core recognizes these as memory-worthy during the LLM reasoning step and calls `Memory.store()` with confidence 1.0 and source "stated".

**2. Conversational extraction**
During normal conversation the LLM notices something worth remembering that the user didn't explicitly flag.

*"I have a standup every day at 9" — said in passing while asking about something else.*

The LLM flags these in the `memory_store` field of its structured JSON response. The Orchestration Core stores them immediately after every LLM call with confidence 0.7 and source "inferred".

**3. Observation over time**
The proactive loop notices patterns from capability data — task completion times, reminder patterns, conversation timing — and stores observations with confidence 0.5–0.6.

These are never presented to the user as certain facts. They inform behavior quietly.

---

## How Memory Is Injected

Before every LLM call the Orchestration Core calls `Memory.get_context()`. This returns a formatted context block inserted into the system prompt.

The context block is structured natural language, not raw JSON. The LLM reads it as background knowledge about the user.

Example context block:
```
About the user:
- Works at Flipkart in Bengaluru
- Prefers not to have meetings before 9am
- Usually starts the day around 9am
- Likes to review tasks in the morning

People:
- Mother: prefers calls after 7pm, last noted contact 5 days ago
- Ravi: colleague at Flipkart, collaborates frequently

Current patterns:
- Tends to set task reminders on Sunday evenings
```

This block is prepended to every LLM system prompt alongside system state. Chitra always has this context. It never has to ask the user to repeat themselves.

---

## How Memory Is Updated

**User correction**
If the user says something that contradicts an existing memory — *"actually I'm fine with 8am meetings now"* — the LLM detects the contradiction, the Orchestration Core calls `Memory.update()` on the relevant entry with corrected content and elevates confidence to 1.0.

**Explicit deletion**
The user can ask Chitra to forget something.
*"Forget what I said about morning meetings"*
The Orchestration Core calls `Memory.deactivate()`. The entry is soft deleted — never injected into context again, but retained in storage.

**Confidence elevation**
If an inferred memory is later confirmed explicitly by the user, confidence is updated to 1.0 and source updated to "stated".

---

## Context Window Management

The local LLM has a finite context window. Memory cannot grow unbounded and overwhelm it.

Rules for context assembly:

**Always include:** All preference entries, all high-confidence facts (confidence ≥ 0.8), all relationship entries where last_referenced is within 30 days.

**Include if relevant:** Observations — only if relevant to current time of day, current conversation topic, or upcoming calendar events.

**Never include:** Entries where active is false. Low confidence observations (below 0.5) older than 60 days.

The `get_context()` action applies these rules automatically. The Orchestration Core never needs to manage context window size manually.

---

## Onboarding and Initial Memory

When Chitra boots for the first time, Memory is empty. The onboarding conversation seeds it with initial context — the user's name, key people in their life, basic work schedule, immediate preferences.

Every answer the user gives during onboarding is stored as a memory entry with confidence 1.0 and source "stated". By the time onboarding is complete, Chitra already knows the user well enough to begin behaving like a companion.

---

## Memory and Privacy

All memory is stored locally on device in SQLite at `~/.chitra/data/memory.db` (development) or `/var/chitra/data/memory.db` (production). No memory entry ever leaves the device. No memory is sent to any external service — including the LLM, since the LLM runs locally via Ollama.

The user can at any time:
- Ask Chitra what it remembers — *"What do you know about me?"*
- Ask it to forget specific things — *"Forget that I mentioned my salary"*
- Request a full memory wipe — *"Forget everything"*

These are first-class conversational interactions, not settings menus.

---

## What Good Memory Feels Like

When Memory is working correctly the user should never feel they are talking to a system that forgets them between sessions. References to past context should feel natural, not mechanical. Chitra uses memory to inform its behavior quietly — not to recite facts back at the user unnecessarily.

**Wrong:**
*"I remember you told me on January 3rd that your mother prefers calls after 7pm."*

**Right:**
*"It's 8pm — good time to call your mother if you've been meaning to."*

Memory informs. It does not perform.

---

*For capability API contract see `CAPABILITIES.md`*
*For how memory is used in orchestration see `ARCHITECTURE.md`*
