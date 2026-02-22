"""
Integration tests for the AI Orchestration Core.

Tests:
- Full interaction flow end to end
- Text-mode E2E conversation loop tests
- Proactive loop trigger and response
- JSON parsing failure and retry behavior
- Context assembly correctness
"""

import asyncio
import os
from unittest.mock import AsyncMock, patch

import pytest

# Set test data directory before any imports
os.environ["CHITRA_DATA_DIR"] = "/tmp/chitra_test_orchestration"


from llm.client import LLMClient
from llm.prompts import (
    CORRECTION_PROMPT,
    PROACTIVE_PROMPT_TEMPLATE,
    RESPONSE_FORMAT_INSTRUCTION,
    SYSTEM_IDENTITY,
)
from orchestration.context import ContextAssembler
from orchestration.core import OrchestrationCore
from orchestration.proactive import ProactiveLoop

# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def fresh_data_dir(tmp_path):
    """Provide a fresh temporary data directory for each test."""
    data_dir = str(tmp_path / "chitra_data")
    os.makedirs(data_dir, exist_ok=True)
    os.environ["CHITRA_DATA_DIR"] = data_dir
    return data_dir


@pytest.fixture
def core(fresh_data_dir):
    """Create a fresh OrchestrationCore with isolated data."""
    return OrchestrationCore()


# ── OrchestrationCore Tests ──────────────────────────────────────


class TestOrchestrationCore:
    """Integration tests for the Orchestration Core."""

    def test_initialization(self, core):
        """Core initializes all capabilities and infrastructure."""
        assert core.memory is not None
        assert core.system_state is not None
        assert core.contacts is not None
        assert core.calendar is not None
        assert core.reminders is not None
        assert core.tasks is not None
        assert core.voice_io is not None
        assert core.llm is not None
        assert core.context_assembler is not None

    def test_capability_dispatch_table(self, core):
        """All 6 capabilities are registered in the dispatch table."""
        assert len(core._capabilities) == 6
        assert "contacts" in core._capabilities
        assert "calendar" in core._capabilities
        assert "reminders" in core._capabilities
        assert "tasks" in core._capabilities
        assert "memory" in core._capabilities
        assert "voice_io" in core._capabilities

    def test_initial_state(self, core):
        """Core starts with empty history and inactive user."""
        assert core.conversation_history == []
        assert core.is_user_active is False
        assert core.max_history_turns == 10

    def test_update_history(self, core):
        """_update_history stores user and assistant messages."""
        core._update_history("hello", "hi there")
        assert len(core.conversation_history) == 2
        assert core.conversation_history[0] == {"role": "user", "content": "hello"}
        assert core.conversation_history[1] == {"role": "assistant", "content": "hi there"}

    def test_update_history_trimming(self, core):
        """_update_history trims to max_history_turns when exceeded."""
        core.max_history_turns = 2  # 2 turns = 4 messages max
        for i in range(10):
            core._update_history(f"msg {i}", f"reply {i}")
        assert len(core.conversation_history) == 4
        # Should keep the last 2 turns
        assert core.conversation_history[0]["content"] == "msg 8"
        assert core.conversation_history[3]["content"] == "reply 9"

    @pytest.mark.asyncio
    async def test_execute_action_create_contact(self, core):
        """execute_action dispatches create() with single-dict parameter."""
        result = await core.execute_action({
            "capability": "contacts",
            "action": "create",
            "params": {"name": "Ravi", "relationship": "friend"},
        })
        assert result is not None
        assert "error" not in result
        assert result["name"] == "Ravi"
        assert result["relationship"] == "friend"

    @pytest.mark.asyncio
    async def test_execute_action_get_contact(self, core):
        """execute_action dispatches get() with keyword arguments."""
        await core.execute_action({
            "capability": "contacts",
            "action": "create",
            "params": {"name": "Amma"},
        })
        result = await core.execute_action({
            "capability": "contacts",
            "action": "get",
            "params": {"name": "Amma"},
        })
        assert result is not None
        assert result["name"] == "Amma"

    @pytest.mark.asyncio
    async def test_execute_action_no_params(self, core):
        """execute_action dispatches methods with no parameters."""
        result = await core.execute_action({
            "capability": "contacts",
            "action": "list",
            "params": {},
        })
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_execute_action_unknown_capability(self, core):
        """execute_action returns None for unknown capability names."""
        result = await core.execute_action({
            "capability": "nonexistent",
            "action": "do_thing",
            "params": {},
        })
        assert result is None

    @pytest.mark.asyncio
    async def test_execute_action_unknown_action(self, core):
        """execute_action returns None for unknown action names."""
        result = await core.execute_action({
            "capability": "contacts",
            "action": "nonexistent_method",
            "params": {},
        })
        assert result is None

    @pytest.mark.asyncio
    async def test_execute_action_missing_fields(self, core):
        """execute_action returns None when capability or action is missing."""
        result = await core.execute_action({"capability": "contacts"})
        assert result is None
        result = await core.execute_action({"action": "list"})
        assert result is None

    @pytest.mark.asyncio
    async def test_execute_action_tasks(self, core):
        """execute_action dispatches to tasks capability correctly."""
        result = await core.execute_action({
            "capability": "tasks",
            "action": "create",
            "params": {"title": "Buy groceries", "priority": "high"},
        })
        assert result is not None
        assert result["title"] == "Buy groceries"
        assert result["priority"] == "high"

    @pytest.mark.asyncio
    async def test_execute_action_reminders(self, core):
        """execute_action dispatches to reminders capability correctly."""
        result = await core.execute_action({
            "capability": "reminders",
            "action": "create",
            "params": {"text": "Call mom", "trigger_at": "2026-02-22T19:00:00"},
        })
        assert result is not None
        assert result["text"] == "Call mom"

    @pytest.mark.asyncio
    async def test_execute_action_calendar(self, core):
        """execute_action dispatches to calendar capability correctly."""
        result = await core.execute_action({
            "capability": "calendar",
            "action": "create",
            "params": {"title": "Standup", "date": "2026-02-22", "time": "10:00"},
        })
        assert result is not None
        assert result["title"] == "Standup"

    @pytest.mark.asyncio
    async def test_store_memories(self, core):
        """store_memories saves entries to Memory and they appear in context."""
        await core.store_memories([
            {
                "category": "fact",
                "subject": "work",
                "content": "Works at Flipkart",
                "confidence": 1.0,
                "source": "stated",
            },
            {
                "category": "preference",
                "subject": "coffee",
                "content": "Prefers filter coffee",
                "confidence": 1.0,
                "source": "stated",
            },
        ])
        ctx = await core.memory.get_context()
        block = ctx["context_block"]
        assert "Flipkart" in block
        assert "filter coffee" in block

    @pytest.mark.asyncio
    async def test_store_memories_invalid_entries(self, core):
        """store_memories handles non-dict entries gracefully without crashing."""
        # Should not raise — just log warnings
        await core.store_memories(["not a dict", None, 42])

    @pytest.mark.asyncio
    async def test_store_memories_empty_list(self, core):
        """store_memories handles empty list gracefully."""
        await core.store_memories([])


# ── Proactive Loop Tests ─────────────────────────────────────────


class TestProactiveLoop:
    """Tests for the proactive background loop."""

    def test_initialization(self, core):
        """ProactiveLoop initializes with core reference and interval."""
        loop = ProactiveLoop(core)
        assert loop.core is core
        assert loop.interval == 60  # default

    def test_custom_interval(self, core):
        """ProactiveLoop respects CHITRA_PROACTIVE_INTERVAL env var."""
        os.environ["CHITRA_PROACTIVE_INTERVAL"] = "30"
        loop = ProactiveLoop(core)
        assert loop.interval == 30
        os.environ["CHITRA_PROACTIVE_INTERVAL"] = "60"  # reset

    @pytest.mark.asyncio
    async def test_gather_empty_context(self, core):
        """_gather_proactive_context returns empty list when no data exists."""
        loop = ProactiveLoop(core)
        parts = await loop._gather_proactive_context()
        assert parts == []

    @pytest.mark.asyncio
    async def test_gather_overdue_tasks(self, core):
        """_gather_proactive_context picks up overdue tasks."""
        await core.tasks.create({
            "title": "Submit report",
            "due_date": "2025-01-01",
            "priority": "high",
        })
        loop = ProactiveLoop(core)
        parts = await loop._gather_proactive_context()
        assert any("Submit report" in p for p in parts)
        assert any("Overdue tasks" in p for p in parts)

    @pytest.mark.asyncio
    async def test_gather_fired_reminders(self, core):
        """_gather_proactive_context picks up fired reminders."""
        await core.reminders.create({
            "text": "Take medicine",
            "trigger_at": "2025-01-01T08:00:00",
        })
        loop = ProactiveLoop(core)
        parts = await loop._gather_proactive_context()
        assert any("Take medicine" in p for p in parts)

    @pytest.mark.asyncio
    async def test_gather_neglected_contacts(self, core):
        """_gather_proactive_context picks up neglected contacts."""
        import sqlite3

        await core.contacts.create({"name": "Amma", "relationship": "mother"})
        # Backdate the last_interaction
        conn = sqlite3.connect(os.path.join(core.data_dir, "contacts.db"))
        conn.execute("UPDATE contacts SET last_interaction = '2025-01-01'")
        conn.commit()
        conn.close()

        loop = ProactiveLoop(core)
        parts = await loop._gather_proactive_context()
        assert any("Amma" in p for p in parts)

    @pytest.mark.asyncio
    async def test_tick_skips_when_user_active(self, core):
        """tick() skips when is_user_active is True."""
        core.is_user_active = True
        loop = ProactiveLoop(core)
        # Should return without error
        await loop.tick()
        core.is_user_active = False

    @pytest.mark.asyncio
    async def test_tick_no_data(self, core):
        """tick() runs cleanly when there's nothing to evaluate."""
        loop = ProactiveLoop(core)
        await loop.tick()

    @pytest.mark.asyncio
    async def test_dismiss_fired_reminders(self, core):
        """_dismiss_fired_reminders dismisses all fired reminders."""
        await core.reminders.create({
            "text": "Take medicine",
            "trigger_at": "2025-01-01T08:00:00",
        })
        fired_before = await core.reminders.get_fired()
        assert len(fired_before) == 1

        loop = ProactiveLoop(core)
        await loop._dismiss_fired_reminders()

        fired_after = await core.reminders.get_fired()
        assert len(fired_after) == 0


# ── Context Assembly Tests ───────────────────────────────────────


class TestContextAssembly:
    """Tests for context assembly before LLM calls."""

    @pytest.mark.asyncio
    async def test_assemble_basic(self, core):
        """assemble() returns system_prompt and conversation_history."""
        result = await core.context_assembler.assemble([])
        assert "system_prompt" in result
        assert "conversation_history" in result
        assert isinstance(result["system_prompt"], str)
        assert isinstance(result["conversation_history"], list)

    @pytest.mark.asyncio
    async def test_assemble_includes_identity(self, core):
        """System prompt always includes Chitra identity."""
        result = await core.context_assembler.assemble([])
        assert "Chitra" in result["system_prompt"]

    @pytest.mark.asyncio
    async def test_assemble_includes_format(self, core):
        """System prompt always includes response format instruction."""
        result = await core.context_assembler.assemble([])
        assert "intent" in result["system_prompt"]
        assert "memory_store" in result["system_prompt"]

    @pytest.mark.asyncio
    async def test_assemble_includes_system_state(self, core):
        """System prompt includes current system state."""
        result = await core.context_assembler.assemble([])
        prompt = result["system_prompt"]
        # Should contain time-of-day info
        assert any(
            tod in prompt for tod in ("morning", "afternoon", "evening", "night")
        )

    @pytest.mark.asyncio
    async def test_assemble_includes_memory(self, core):
        """System prompt includes memory context when memories exist."""
        await core.memory.store({
            "category": "fact",
            "subject": "work",
            "content": "Works at Flipkart",
            "confidence": 1.0,
            "source": "stated",
        })
        result = await core.context_assembler.assemble([])
        assert "Flipkart" in result["system_prompt"]

    @pytest.mark.asyncio
    async def test_assemble_preserves_history(self, core):
        """assemble() passes through conversation history unchanged."""
        history = [{"role": "user", "content": "hello"}]
        result = await core.context_assembler.assemble(history)
        assert result["conversation_history"] == history

    @pytest.mark.asyncio
    async def test_format_system_state(self, core):
        """_format_system_state produces natural language state description."""
        state = {
            "datetime": "2026-02-21T22:30:00",
            "day_of_week": "Saturday",
            "time_of_day": "night",
            "battery_percent": 85,
        }
        result = core.context_assembler._format_system_state(state)
        assert "night" in result
        assert "Saturday" in result
        assert "85%" in result

    @pytest.mark.asyncio
    async def test_format_system_state_error(self, core):
        """_format_system_state returns empty string on error state."""
        result = core.context_assembler._format_system_state({"error": "fail"})
        assert result == ""

    @pytest.mark.asyncio
    async def test_format_upcoming_events(self, core):
        """_format_upcoming_events formats events as natural language."""
        events = [
            {
                "title": "Team Meeting",
                "time": "10:00",
                "duration_minutes": 60,
                "participants": ["Ravi", "Priya"],
            },
        ]
        result = core.context_assembler._format_upcoming_events(events)
        assert "Team Meeting" in result
        assert "10:00" in result
        assert "Ravi" in result

    @pytest.mark.asyncio
    async def test_format_upcoming_events_empty(self, core):
        """_format_upcoming_events returns empty string when no events."""
        result = core.context_assembler._format_upcoming_events([])
        assert result == ""

    @pytest.mark.asyncio
    async def test_format_upcoming_reminders(self, core):
        """_format_upcoming_reminders formats reminders as natural language."""
        reminders = [
            {"text": "Call mother", "trigger_at": "2026-02-21T19:00:00"},
        ]
        result = core.context_assembler._format_upcoming_reminders(reminders)
        assert "Call mother" in result

    @pytest.mark.asyncio
    async def test_format_upcoming_reminders_empty(self, core):
        """_format_upcoming_reminders returns empty string when no reminders."""
        result = core.context_assembler._format_upcoming_reminders([])
        assert result == ""

    @pytest.mark.asyncio
    async def test_assemble_includes_capability_catalog(self, core):
        """System prompt includes capability catalog so LLM knows available actions."""
        result = await core.context_assembler.assemble([])
        prompt = result["system_prompt"]
        assert "contacts:" in prompt
        assert "calendar:" in prompt
        assert "reminders:" in prompt
        assert "tasks:" in prompt
        assert "Only use actions from this catalog" in prompt


# ── LLM Client Tests ─────────────────────────────────────────────


class TestLLMClient:
    """Tests for the LLM client JSON parsing and validation."""

    def test_initialization(self):
        """LLM client initializes with model from env var."""
        client = LLMClient()
        assert client.model == os.environ.get("CHITRA_LLM_MODEL", "qwen2.5:7b")

    def test_parse_valid_json(self):
        """_parse_response parses valid JSON correctly."""
        client = LLMClient()
        raw = '{"intent": "greeting", "response": "Hello!", "action": null, "memory_store": []}'
        result = client._parse_response(raw)
        assert result is not None
        assert result["intent"] == "greeting"
        assert result["response"] == "Hello!"

    def test_parse_json_in_markdown(self):
        """_parse_response extracts JSON from markdown code blocks."""
        client = LLMClient()
        raw = '```json\n{"intent": "greeting", "response": "Hello!"}\n```'
        result = client._parse_response(raw)
        assert result is not None
        assert result["response"] == "Hello!"

    def test_parse_json_with_surrounding_text(self):
        """_parse_response extracts JSON surrounded by other text."""
        client = LLMClient()
        raw = 'Here is my response: {"intent": "greeting", "response": "Hello!"} end'
        result = client._parse_response(raw)
        assert result is not None
        assert result["response"] == "Hello!"

    def test_parse_missing_response_field(self):
        """_parse_response returns None when 'response' field is missing."""
        client = LLMClient()
        raw = '{"intent": "greeting", "action": null}'
        result = client._parse_response(raw)
        assert result is None

    def test_parse_invalid_json(self):
        """_parse_response returns None for completely invalid JSON."""
        client = LLMClient()
        result = client._parse_response("this is not json at all")
        assert result is None

    def test_validate_fills_defaults(self):
        """_validate_response fills missing optional fields with defaults."""
        client = LLMClient()
        result = client._validate_response({"response": "Hello!"})
        assert result["intent"] == "unknown"
        assert result["action"] is None
        assert result["memory_store"] == []

    def test_validate_rejects_non_dict(self):
        """_validate_response returns None for non-dict input."""
        client = LLMClient()
        assert client._validate_response("string") is None
        assert client._validate_response([1, 2, 3]) is None

    def test_fallback_response(self):
        """_fallback_response returns a safe structured response."""
        client = LLMClient()
        result = client._fallback_response()
        assert "response" in result
        assert result["intent"] == "unknown"
        assert result["action"] is None
        assert result["memory_store"] == []


# ── Prompt Tests ─────────────────────────────────────────────────


class TestPrompts:
    """Tests for prompt templates."""

    def test_system_identity_exists(self):
        """SYSTEM_IDENTITY is defined and mentions Chitra."""
        assert "Chitra" in SYSTEM_IDENTITY

    def test_response_format_instruction(self):
        """RESPONSE_FORMAT_INSTRUCTION contains required JSON fields."""
        assert "intent" in RESPONSE_FORMAT_INSTRUCTION
        assert "action" in RESPONSE_FORMAT_INSTRUCTION
        assert "response" in RESPONSE_FORMAT_INSTRUCTION
        assert "memory_store" in RESPONSE_FORMAT_INSTRUCTION

    def test_correction_prompt(self):
        """CORRECTION_PROMPT exists and mentions JSON."""
        assert "JSON" in CORRECTION_PROMPT

    def test_capability_catalog_exists(self):
        """CAPABILITY_CATALOG lists all capabilities and their actions."""
        from llm.prompts import CAPABILITY_CATALOG

        assert "contacts:" in CAPABILITY_CATALOG
        assert "calendar:" in CAPABILITY_CATALOG
        assert "reminders:" in CAPABILITY_CATALOG
        assert "tasks:" in CAPABILITY_CATALOG
        assert "memory:" in CAPABILITY_CATALOG
        assert "voice_io:" in CAPABILITY_CATALOG
        assert "Only use actions from this catalog" in CAPABILITY_CATALOG

    def test_proactive_prompt_template(self):
        """PROACTIVE_PROMPT_TEMPLATE contains format placeholder and should_speak."""
        assert "{context}" in PROACTIVE_PROMPT_TEMPLATE
        assert "should_speak" in PROACTIVE_PROMPT_TEMPLATE

    def test_proactive_prompt_formats(self):
        """PROACTIVE_PROMPT_TEMPLATE formats correctly with context."""
        formatted = PROACTIVE_PROMPT_TEMPLATE.format(context="Overdue: Buy milk")
        assert "Buy milk" in formatted
        assert "should_speak" in formatted


# ── Text-Mode End-to-End Tests ───────────────────────────────────


def _make_llm_response(response_text, action=None, memory_store=None):
    """Build a valid LLM response dict for mocking."""
    return {
        "intent": "general",
        "action": action,
        "response": response_text,
        "memory_store": memory_store or [],
    }


class TestTextModeE2E:
    """End-to-end tests for the text-mode conversation pipeline.

    These wire together the full chain: listen (text) → context assembly →
    LLM call (mocked) → action dispatch → capability execution (real DB) →
    followup LLM → display → speak, using real capability instances with
    isolated temp databases.
    """

    @pytest.fixture
    def e2e_core(self, fresh_data_dir):
        """OrchestrationCore with real capabilities, isolated data, text mode."""
        core = OrchestrationCore()
        core.voice_io._input_mode = "text"
        return core

    # ── 1. Full single-turn pipeline (no action) ─────────────────

    @pytest.mark.asyncio
    async def test_single_turn_no_action(self, e2e_core):
        """Full pipeline: user input → context → LLM → response displayed."""
        core = e2e_core

        mock_llm_return = _make_llm_response("Hello! How can I help you today?")

        with patch.object(core.llm, "call", new_callable=AsyncMock, return_value=mock_llm_return):
            response = await core.handle_input("hello")

        assert response == "Hello! How can I help you today?"
        assert len(core.conversation_history) == 2
        assert core.conversation_history[0] == {"role": "user", "content": "hello"}
        assert core.conversation_history[1] == {
            "role": "assistant", "content": "Hello! How can I help you today?",
        }

    # ── 2. Full single-turn pipeline with action round-trip ──────

    @pytest.mark.asyncio
    async def test_single_turn_with_action_creates_contact(self, e2e_core):
        """User says 'add contact Ravi' → LLM returns action → contact created in DB → followup."""
        core = e2e_core

        first_llm = _make_llm_response(
            "I'll add Ravi to your contacts.",
            action={"capability": "contacts", "action": "create", "params": {"name": "Ravi", "relationship": "friend"}},
        )
        followup_llm = _make_llm_response("Done! I've added Ravi as a friend to your contacts.")

        call_count = 0

        async def mock_call(system_prompt, user_message, history=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return first_llm
            return followup_llm

        with patch.object(core.llm, "call", side_effect=mock_call):
            response = await core.handle_input("add contact Ravi")

        assert call_count == 2
        assert response == "Done! I've added Ravi as a friend to your contacts."

        # Verify contact actually exists in the database
        contact = await core.contacts.get(name="Ravi")
        assert contact is not None
        assert contact["name"] == "Ravi"
        assert contact["relationship"] == "friend"

    @pytest.mark.asyncio
    async def test_single_turn_with_action_creates_task(self, e2e_core):
        """Action round-trip: create task → verify in DB → followup response."""
        core = e2e_core

        first_llm = _make_llm_response(
            "I'll create that task.",
            action={"capability": "tasks", "action": "create", "params": {"title": "Buy groceries", "priority": "high"}},
        )
        followup_llm = _make_llm_response("Added 'Buy groceries' as a high-priority task.")

        call_count = 0

        async def mock_call(system_prompt, user_message, history=None):
            nonlocal call_count
            call_count += 1
            return first_llm if call_count == 1 else followup_llm

        with patch.object(core.llm, "call", side_effect=mock_call):
            response = await core.handle_input("remind me to buy groceries")

        assert response == "Added 'Buy groceries' as a high-priority task."
        tasks = await core.tasks.list()
        assert any(t["title"] == "Buy groceries" for t in tasks)

    @pytest.mark.asyncio
    async def test_single_turn_with_action_creates_reminder(self, e2e_core):
        """Action round-trip: create reminder → verify in DB."""
        core = e2e_core

        first_llm = _make_llm_response(
            "Setting a reminder.",
            action={
                "capability": "reminders", "action": "create",
                "params": {"text": "Call mom", "trigger_at": "2026-02-23T10:00:00"},
            },
        )
        followup_llm = _make_llm_response("I'll remind you to call mom tomorrow at 10 AM.")

        calls = []

        async def mock_call(system_prompt, user_message, history=None):
            calls.append(user_message)
            return first_llm if len(calls) == 1 else followup_llm

        with patch.object(core.llm, "call", side_effect=mock_call):
            response = await core.handle_input("remind me to call mom tomorrow at 10am")

        assert "call mom" in response.lower()
        reminders = await core.reminders.list_upcoming(hours_ahead=48)
        assert any(r["text"] == "Call mom" for r in reminders)

    # ── 3. Memory storage from LLM response ──────────────────────

    @pytest.mark.asyncio
    async def test_single_turn_stores_memory(self, e2e_core):
        """LLM returns memory_store entries → stored in Memory DB → appear in context."""
        core = e2e_core

        mock_return = _make_llm_response(
            "Nice! I'll remember you work at Flipkart.",
            memory_store=[{
                "category": "fact",
                "subject": "work",
                "content": "Works at Flipkart",
                "confidence": 1.0,
                "source": "stated",
            }],
        )

        with patch.object(core.llm, "call", new_callable=AsyncMock, return_value=mock_return):
            await core.handle_input("I work at Flipkart")

        ctx = await core.memory.get_context()
        assert "Flipkart" in ctx.get("context_block", "")

    @pytest.mark.asyncio
    async def test_action_plus_memory_in_same_turn(self, e2e_core):
        """LLM returns both an action and memory_store in the same turn."""
        core = e2e_core

        first_llm = _make_llm_response(
            "Adding Amma.",
            action={"capability": "contacts", "action": "create", "params": {"name": "Amma", "relationship": "mother"}},
            memory_store=[{
                "category": "relationship",
                "subject": "Amma",
                "content": "User's mother is Amma",
                "confidence": 1.0,
                "source": "stated",
            }],
        )
        followup_llm = _make_llm_response("I've added Amma as your mother in contacts.")

        call_count = 0

        async def mock_call(system_prompt, user_message, history=None):
            nonlocal call_count
            call_count += 1
            return first_llm if call_count == 1 else followup_llm

        with patch.object(core.llm, "call", side_effect=mock_call):
            await core.handle_input("my mother's name is Amma, add her to contacts")

        contact = await core.contacts.get(name="Amma")
        assert contact is not None
        assert contact["relationship"] == "mother"

        ctx = await core.memory.get_context()
        assert "Amma" in ctx.get("context_block", "")

    # ── 4. Multi-turn conversation with history ──────────────────

    @pytest.mark.asyncio
    async def test_multi_turn_history_accumulates(self, e2e_core):
        """Conversation history grows across turns and is passed to LLM."""
        core = e2e_core
        captured_histories = []

        async def mock_call(system_prompt, user_message, history=None):
            captured_histories.append(list(history) if history else [])
            return _make_llm_response(f"Reply to: {user_message}")

        with patch.object(core.llm, "call", side_effect=mock_call):
            await core.handle_input("first message")
            await core.handle_input("second message")
            await core.handle_input("third message")

        assert len(captured_histories) == 3
        assert len(captured_histories[0]) == 0
        assert len(captured_histories[1]) == 2
        assert len(captured_histories[2]) == 4

        assert captured_histories[1][0]["content"] == "first message"
        assert captured_histories[2][2]["content"] == "second message"

    @pytest.mark.asyncio
    async def test_multi_turn_history_trimming(self, e2e_core):
        """History trims to max_history_turns, keeping most recent turns."""
        core = e2e_core
        core.max_history_turns = 2  # Keep only 2 turns = 4 messages

        async def mock_call(system_prompt, user_message, history=None):
            return _make_llm_response(f"Reply to: {user_message}")

        with patch.object(core.llm, "call", side_effect=mock_call):
            for i in range(5):
                await core.handle_input(f"turn {i}")

        assert len(core.conversation_history) == 4
        assert core.conversation_history[0]["content"] == "turn 3"
        assert core.conversation_history[2]["content"] == "turn 4"

    @pytest.mark.asyncio
    async def test_multi_turn_context_includes_prior_memories(self, e2e_core):
        """Memory stored in turn 1 appears in context for turn 2."""
        core = e2e_core
        captured_prompts = []

        turn = 0

        async def mock_call(system_prompt, user_message, history=None):
            nonlocal turn
            turn += 1
            captured_prompts.append(system_prompt)
            if turn == 1:
                return _make_llm_response(
                    "Got it, you prefer dark mode.",
                    memory_store=[{
                        "category": "preference",
                        "subject": "ui_theme",
                        "content": "Prefers dark mode",
                        "confidence": 1.0,
                        "source": "stated",
                    }],
                )
            return _make_llm_response("Sure, I remember you like dark mode.")

        with patch.object(core.llm, "call", side_effect=mock_call):
            await core.handle_input("I prefer dark mode")
            await core.handle_input("what are my preferences?")

        assert "dark mode" not in captured_prompts[0].lower()
        assert "dark mode" in captured_prompts[1].lower()

    # ── 5. Conversation loop integration ─────────────────────────

    @pytest.mark.asyncio
    async def test_conversation_loop_listen_handle_display_speak(self, e2e_core):
        """Full loop iteration: listen → handle_input → display → speak."""
        core = e2e_core

        mock_llm_return = _make_llm_response("Good morning!")

        listen_calls = 0

        async def mock_listen():
            nonlocal listen_calls
            listen_calls += 1
            if listen_calls == 1:
                return {"text": "good morning", "confidence": 1.0}
            raise KeyboardInterrupt

        with (
            patch.object(core.voice_io, "listen", side_effect=mock_listen),
            patch.object(core.voice_io, "display", new_callable=AsyncMock, return_value={"status": "done"}) as mock_display,
            patch.object(core.voice_io, "speak", new_callable=AsyncMock, return_value={"status": "done"}) as mock_speak,
            patch.object(core.llm, "call", new_callable=AsyncMock, return_value=mock_llm_return),
        ):
            with pytest.raises(KeyboardInterrupt):
                await core._conversation_loop()

        mock_display.assert_called_once_with("good morning", "Good morning!")
        mock_speak.assert_called_once_with("Good morning!")
        assert core.conversation_history[0]["content"] == "good morning"
        assert core.conversation_history[1]["content"] == "Good morning!"

    @pytest.mark.asyncio
    async def test_conversation_loop_skips_empty_input(self, e2e_core):
        """Loop continues past empty input without calling LLM."""
        core = e2e_core

        listen_calls = 0

        async def mock_listen():
            nonlocal listen_calls
            listen_calls += 1
            if listen_calls == 1:
                return {"text": "", "confidence": 1.0}
            if listen_calls == 2:
                return {"text": "hi", "confidence": 1.0}
            raise KeyboardInterrupt

        with (
            patch.object(core.voice_io, "listen", side_effect=mock_listen),
            patch.object(core.voice_io, "display", new_callable=AsyncMock, return_value={"status": "done"}),
            patch.object(core.voice_io, "speak", new_callable=AsyncMock, return_value={"status": "done"}),
            patch.object(core.llm, "call", new_callable=AsyncMock, return_value=_make_llm_response("Hey!")) as mock_llm,
        ):
            with pytest.raises(KeyboardInterrupt):
                await core._conversation_loop()

        mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_conversation_loop_skips_listen_error(self, e2e_core):
        """Loop continues past listen errors without crashing."""
        core = e2e_core

        listen_calls = 0

        async def mock_listen():
            nonlocal listen_calls
            listen_calls += 1
            if listen_calls == 1:
                return {"error": "Microphone not found"}
            if listen_calls == 2:
                return {"text": "hello", "confidence": 1.0}
            raise KeyboardInterrupt

        with (
            patch.object(core.voice_io, "listen", side_effect=mock_listen),
            patch.object(core.voice_io, "display", new_callable=AsyncMock, return_value={"status": "done"}),
            patch.object(core.voice_io, "speak", new_callable=AsyncMock, return_value={"status": "done"}),
            patch.object(core.llm, "call", new_callable=AsyncMock, return_value=_make_llm_response("Hi!")) as mock_llm,
        ):
            with pytest.raises(KeyboardInterrupt):
                await core._conversation_loop()

        mock_llm.assert_called_once()

    # ── 6. Error resilience ──────────────────────────────────────

    @pytest.mark.asyncio
    async def test_conversation_loop_survives_llm_failure(self, e2e_core):
        """Loop recovers from an LLM exception and continues to next turn."""
        core = e2e_core

        listen_calls = 0

        async def mock_listen():
            nonlocal listen_calls
            listen_calls += 1
            if listen_calls == 1:
                return {"text": "crash me", "confidence": 1.0}
            if listen_calls == 2:
                return {"text": "try again", "confidence": 1.0}
            raise KeyboardInterrupt

        call_count = 0

        async def mock_llm_call(system_prompt, user_message, history=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("LLM connection lost")
            return _make_llm_response("I'm back!")

        with (
            patch.object(core.voice_io, "listen", side_effect=mock_listen),
            patch.object(core.voice_io, "display", new_callable=AsyncMock, return_value={"status": "done"}) as mock_display,
            patch.object(core.voice_io, "speak", new_callable=AsyncMock, return_value={"status": "done"}),
            patch.object(core.llm, "call", side_effect=mock_llm_call),
        ):
            with pytest.raises(KeyboardInterrupt):
                await core._conversation_loop()

        display_calls = mock_display.call_args_list
        assert len(display_calls) == 2
        # First turn: handle_input catches LLM error and returns fallback
        assert "trouble processing" in display_calls[0].args[1].lower()
        # Second turn: LLM succeeds
        assert display_calls[1].args[1] == "I'm back!"

    @pytest.mark.asyncio
    async def test_handle_input_returns_fallback_on_exception(self, e2e_core):
        """handle_input returns a user-friendly message when context assembly crashes."""
        core = e2e_core

        with patch.object(
            core.context_assembler, "assemble", side_effect=RuntimeError("DB locked"),
        ):
            response = await core.handle_input("hello")

        assert "trouble processing" in response.lower()

    # ── 7. Action with no result (action returns None) ───────────

    @pytest.mark.asyncio
    async def test_action_returns_none_skips_followup(self, e2e_core):
        """When action dispatch returns None, no followup LLM call is made."""
        core = e2e_core

        mock_return = _make_llm_response(
            "I'll try to do that.",
            action={"capability": "nonexistent", "action": "do_thing", "params": {}},
        )

        with patch.object(core.llm, "call", new_callable=AsyncMock, return_value=mock_return) as mock_llm:
            response = await core.handle_input("do something impossible")

        mock_llm.assert_called_once()
        assert response == "I'll try to do that."

    # ── 8. Full listen→display→speak in text mode ────────────────

    @pytest.mark.asyncio
    async def test_text_mode_speak_skips_tts(self, e2e_core):
        """In text mode, speak() returns immediately without TTS."""
        core = e2e_core
        result = await core.voice_io.speak("Hello world")
        assert result == {"status": "done"}

    @pytest.mark.asyncio
    async def test_display_records_conversation_log(self, e2e_core):
        """display() appends exchanges to the conversation log."""
        core = e2e_core
        await core.voice_io.display("user says hi", "chitra says hello")
        assert len(core.voice_io._conversation_log) == 2
        assert core.voice_io._conversation_log[0] == {"role": "user", "text": "user says hi"}
        assert core.voice_io._conversation_log[1] == {"role": "chitra", "text": "chitra says hello"}

    # ── 9. Two-action sequence across turns ──────────────────────

    @pytest.mark.asyncio
    async def test_create_then_retrieve_across_turns(self, e2e_core):
        """Turn 1 creates a contact, turn 2 retrieves it — both via full pipeline."""
        core = e2e_core

        turn = 0

        async def mock_call(system_prompt, user_message, history=None):
            nonlocal turn
            turn += 1
            if turn == 1:
                return _make_llm_response(
                    "Adding Priya.",
                    action={"capability": "contacts", "action": "create", "params": {"name": "Priya", "relationship": "sister"}},
                )
            if turn == 2:
                return _make_llm_response("Done! Priya has been added.")
            if turn == 3:
                return _make_llm_response(
                    "Looking up Priya.",
                    action={"capability": "contacts", "action": "get", "params": {"name": "Priya"}},
                )
            return _make_llm_response("Priya is your sister.")

        with patch.object(core.llm, "call", side_effect=mock_call):
            r1 = await core.handle_input("add my sister Priya to contacts")
            r2 = await core.handle_input("who is Priya?")

        assert "Priya" in r1
        assert "sister" in r2.lower()
        assert len(core.conversation_history) == 4
