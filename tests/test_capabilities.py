"""
Unit tests for all capability module actions.

Tests each capability's:
- Happy path — correct input, expected output
- Error cases — missing input, invalid input
- Edge cases specific to each capability
"""

import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

os.environ["CHITRA_DATA_DIR"] = "/tmp/chitra_test_capabilities"

from capabilities.contacts import Contacts
from capabilities.calendar import Calendar
from capabilities.reminders import Reminders
from capabilities.tasks import Tasks
from capabilities.system_state import SystemState
from capabilities.voice_io import VoiceIO


# ═══════════════════════════════════════════════════════════════════
# Contacts
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture
def contacts(tmp_path):
    """Create a fresh Contacts instance with isolated database."""
    db_path = str(tmp_path / "contacts.db")
    return Contacts(db_path)


class TestContacts:
    """Tests for the Contacts capability."""

    # ── Create ────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_create_contact(self, contacts):
        """Creating a contact returns the entry with generated ID."""
        result = await contacts.create({"name": "Amma", "relationship": "mother"})
        assert "id" in result
        assert result["name"] == "Amma"
        assert result["relationship"] == "mother"
        assert result["last_interaction"] is not None

    @pytest.mark.asyncio
    async def test_create_contact_minimal(self, contacts):
        """Creating a contact with only name succeeds."""
        result = await contacts.create({"name": "Ravi"})
        assert result["name"] == "Ravi"
        assert result["relationship"] is None

    @pytest.mark.asyncio
    async def test_create_contact_full_fields(self, contacts):
        """Creating a contact with all fields succeeds."""
        result = await contacts.create({
            "name": "Bala",
            "relationship": "self",
            "phone": "9876543210",
            "email": "bala@example.com",
            "notes": "Main user",
            "communication_preference": "text",
        })
        assert result["phone"] == "9876543210"
        assert result["email"] == "bala@example.com"
        assert result["communication_preference"] == "text"

    @pytest.mark.asyncio
    async def test_create_missing_name(self, contacts):
        """Creating a contact without name returns error."""
        result = await contacts.create({"relationship": "friend"})
        assert "error" in result

    # ── Get ───────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_by_name(self, contacts):
        """Get finds contact by exact name."""
        await contacts.create({"name": "Ravi"})
        result = await contacts.get("Ravi")
        assert result is not None
        assert result["name"] == "Ravi"

    @pytest.mark.asyncio
    async def test_get_partial_name(self, contacts):
        """Get finds contact by partial name match."""
        await contacts.create({"name": "Rajesh Kumar"})
        result = await contacts.get("Raj")
        assert result is not None
        assert "Rajesh" in result["name"]

    @pytest.mark.asyncio
    async def test_get_case_insensitive(self, contacts):
        """Get is case-insensitive."""
        await contacts.create({"name": "Amma"})
        result = await contacts.get("amma")
        assert result is not None
        assert result["name"] == "Amma"

    @pytest.mark.asyncio
    async def test_get_not_found(self, contacts):
        """Get returns None when no match."""
        result = await contacts.get("Nobody")
        assert result is None

    # ── List ──────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_list_empty(self, contacts):
        """List returns empty list when no contacts."""
        result = await contacts.list()
        assert result == []

    @pytest.mark.asyncio
    async def test_list_all(self, contacts):
        """List returns all contacts."""
        await contacts.create({"name": "Amma"})
        await contacts.create({"name": "Ravi"})
        result = await contacts.list()
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_ordered_by_name(self, contacts):
        """List returns contacts ordered by name."""
        await contacts.create({"name": "Zara"})
        await contacts.create({"name": "Amma"})
        result = await contacts.list()
        assert result[0]["name"] == "Amma"
        assert result[1]["name"] == "Zara"

    # ── Update ────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_update_fields(self, contacts):
        """Update modifies specified fields."""
        created = await contacts.create({"name": "Ravi", "relationship": "friend"})
        updated = await contacts.update(created["id"], {"phone": "1234567890"})
        assert updated["phone"] == "1234567890"
        assert updated["name"] == "Ravi"  # Unchanged

    @pytest.mark.asyncio
    async def test_update_ignores_invalid_fields(self, contacts):
        """Update ignores fields not in VALID_FIELDS."""
        created = await contacts.create({"name": "Ravi"})
        result = await contacts.update(created["id"], {"invalid_field": "value"})
        assert "error" in result
        assert "No valid fields" in result["error"]

    @pytest.mark.asyncio
    async def test_update_not_found(self, contacts):
        """Update returns error for nonexistent contact."""
        result = await contacts.update("nonexistent-id", {"name": "New"})
        assert "error" in result
        assert "not found" in result["error"]

    # ── Note interaction ──────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_note_interaction(self, contacts):
        """note_interaction updates last_interaction to today."""
        created = await contacts.create({"name": "Amma"})
        result = await contacts.note_interaction(created["id"])
        assert result["last_interaction"] == datetime.now().date().isoformat()

    @pytest.mark.asyncio
    async def test_note_interaction_not_found(self, contacts):
        """note_interaction returns error for nonexistent contact."""
        result = await contacts.note_interaction("nonexistent-id")
        assert "error" in result

    # ── Get neglected ─────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_neglected_none(self, contacts):
        """get_neglected returns empty when all contacts are recent."""
        await contacts.create({"name": "Amma"})  # last_interaction is today
        result = await contacts.get_neglected(7)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_neglected_finds_old(self, contacts):
        """get_neglected finds contacts with old last_interaction."""
        import sqlite3

        created = await contacts.create({"name": "Old Friend"})
        # Set last_interaction to 10 days ago
        old_date = (datetime.now().date() - timedelta(days=10)).isoformat()
        conn = sqlite3.connect(contacts.db_path)
        conn.execute("UPDATE contacts SET last_interaction = ? WHERE id = ?", (old_date, created["id"]))
        conn.commit()
        conn.close()

        result = await contacts.get_neglected(7)
        assert len(result) == 1
        assert result[0]["name"] == "Old Friend"

    @pytest.mark.asyncio
    async def test_get_neglected_ordered_by_oldest(self, contacts):
        """get_neglected returns contacts ordered by oldest interaction first."""
        import sqlite3

        c1 = await contacts.create({"name": "Older"})
        c2 = await contacts.create({"name": "Old"})

        d1 = (datetime.now().date() - timedelta(days=20)).isoformat()
        d2 = (datetime.now().date() - timedelta(days=10)).isoformat()

        conn = sqlite3.connect(contacts.db_path)
        conn.execute("UPDATE contacts SET last_interaction = ? WHERE id = ?", (d1, c1["id"]))
        conn.execute("UPDATE contacts SET last_interaction = ? WHERE id = ?", (d2, c2["id"]))
        conn.commit()
        conn.close()

        result = await contacts.get_neglected(7)
        assert len(result) == 2
        assert result[0]["name"] == "Older"


# ═══════════════════════════════════════════════════════════════════
# Calendar
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture
def calendar(tmp_path):
    """Create a fresh Calendar instance with isolated database."""
    db_path = str(tmp_path / "calendar.db")
    return Calendar(db_path)


class TestCalendar:
    """Tests for the Calendar capability."""

    # ── Create ────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_create_event(self, calendar):
        """Creating an event returns the entry with generated ID."""
        result = await calendar.create({
            "title": "Team Meeting",
            "date": "2026-02-22",
            "time": "10:00",
        })
        assert "id" in result
        assert result["title"] == "Team Meeting"
        assert result["date"] == "2026-02-22"
        assert result["time"] == "10:00"
        assert result["duration_minutes"] == 60  # Default

    @pytest.mark.asyncio
    async def test_create_event_with_participants(self, calendar):
        """Creating an event with participants stores them as list."""
        result = await calendar.create({
            "title": "Review",
            "date": "2026-02-22",
            "time": "14:00",
            "participants": ["Ravi", "Priya"],
        })
        assert result["participants"] == ["Ravi", "Priya"]

    @pytest.mark.asyncio
    async def test_create_event_custom_duration(self, calendar):
        """Creating an event with custom duration."""
        result = await calendar.create({
            "title": "Quick sync",
            "date": "2026-02-22",
            "time": "09:00",
            "duration_minutes": 15,
        })
        assert result["duration_minutes"] == 15

    @pytest.mark.asyncio
    async def test_create_missing_title(self, calendar):
        """Creating an event without title returns error."""
        result = await calendar.create({"date": "2026-02-22", "time": "10:00"})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create_missing_date(self, calendar):
        """Creating an event without date returns error."""
        result = await calendar.create({"title": "Meeting", "time": "10:00"})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create_missing_time(self, calendar):
        """Creating an event without time returns error."""
        result = await calendar.create({"title": "Meeting", "date": "2026-02-22"})
        assert "error" in result

    # ── Get today ─────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_today(self, calendar):
        """get_today returns events for today."""
        today = datetime.now().date().isoformat()
        await calendar.create({"title": "Today's meeting", "date": today, "time": "10:00"})
        await calendar.create({"title": "Tomorrow's meeting", "date": "2099-01-01", "time": "10:00"})
        result = await calendar.get_today()
        assert len(result) == 1
        assert result[0]["title"] == "Today's meeting"

    @pytest.mark.asyncio
    async def test_get_today_ordered_by_time(self, calendar):
        """get_today returns events ordered by time."""
        today = datetime.now().date().isoformat()
        await calendar.create({"title": "Afternoon", "date": today, "time": "14:00"})
        await calendar.create({"title": "Morning", "date": today, "time": "09:00"})
        result = await calendar.get_today()
        assert result[0]["title"] == "Morning"
        assert result[1]["title"] == "Afternoon"

    @pytest.mark.asyncio
    async def test_get_today_empty(self, calendar):
        """get_today returns empty list when no events today."""
        await calendar.create({"title": "Future", "date": "2099-01-01", "time": "10:00"})
        result = await calendar.get_today()
        assert result == []

    # ── Get range ─────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_range(self, calendar):
        """get_range returns events within date range."""
        await calendar.create({"title": "In range", "date": "2026-03-15", "time": "10:00"})
        await calendar.create({"title": "Out of range", "date": "2026-04-01", "time": "10:00"})
        result = await calendar.get_range("2026-03-01", "2026-03-31")
        assert len(result) == 1
        assert result[0]["title"] == "In range"

    @pytest.mark.asyncio
    async def test_get_range_inclusive(self, calendar):
        """get_range includes events on boundary dates."""
        await calendar.create({"title": "Start boundary", "date": "2026-03-01", "time": "10:00"})
        await calendar.create({"title": "End boundary", "date": "2026-03-31", "time": "10:00"})
        result = await calendar.get_range("2026-03-01", "2026-03-31")
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_range_empty(self, calendar):
        """get_range returns empty when no events in range."""
        result = await calendar.get_range("2099-01-01", "2099-01-31")
        assert result == []

    # ── Get upcoming ──────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_upcoming_future_events(self, calendar):
        """get_upcoming returns events within the time window."""
        # Create an event 30 minutes from now
        now = datetime.now()
        future = now + timedelta(minutes=30)
        await calendar.create({
            "title": "Soon",
            "date": future.date().isoformat(),
            "time": future.strftime("%H:%M"),
        })
        result = await calendar.get_upcoming(hours_ahead=1)
        assert len(result) == 1
        assert result[0]["title"] == "Soon"

    @pytest.mark.asyncio
    async def test_get_upcoming_excludes_past(self, calendar):
        """get_upcoming does not return past events."""
        await calendar.create({"title": "Past", "date": "2020-01-01", "time": "10:00"})
        result = await calendar.get_upcoming(hours_ahead=1)
        assert result == []


# ═══════════════════════════════════════════════════════════════════
# Reminders
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture
def reminders(tmp_path):
    """Create a fresh Reminders instance with isolated database."""
    db_path = str(tmp_path / "reminders.db")
    return Reminders(db_path)


class TestReminders:
    """Tests for the Reminders capability."""

    # ── Create ────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_create_reminder(self, reminders):
        """Creating a reminder returns the entry with generated ID."""
        result = await reminders.create({
            "text": "Call Amma",
            "trigger_at": "2026-02-22T19:00:00",
        })
        assert "id" in result
        assert result["text"] == "Call Amma"
        assert result["trigger_at"] == "2026-02-22T19:00:00"
        assert result["status"] == "pending"

    @pytest.mark.asyncio
    async def test_create_with_contact_id(self, reminders):
        """Creating a reminder with contact_id."""
        result = await reminders.create({
            "text": "Call mother",
            "trigger_at": "2026-02-22T19:00:00",
            "contact_id": "contact-123",
        })
        assert result["contact_id"] == "contact-123"

    @pytest.mark.asyncio
    async def test_create_missing_text(self, reminders):
        """Creating a reminder without text returns error."""
        result = await reminders.create({"trigger_at": "2026-02-22T19:00:00"})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create_missing_trigger_at(self, reminders):
        """Creating a reminder without trigger_at returns error."""
        result = await reminders.create({"text": "Do something"})
        assert "error" in result

    # ── Get fired ─────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_fired_past_reminder(self, reminders):
        """get_fired returns pending reminders whose trigger_at has passed."""
        past = (datetime.now() - timedelta(minutes=5)).isoformat()
        await reminders.create({"text": "Past reminder", "trigger_at": past})
        result = await reminders.get_fired()
        assert len(result) == 1
        assert result[0]["text"] == "Past reminder"

    @pytest.mark.asyncio
    async def test_get_fired_excludes_future(self, reminders):
        """get_fired does not return future reminders."""
        future = (datetime.now() + timedelta(hours=1)).isoformat()
        await reminders.create({"text": "Future reminder", "trigger_at": future})
        result = await reminders.get_fired()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_fired_excludes_dismissed(self, reminders):
        """get_fired does not return dismissed reminders."""
        past = (datetime.now() - timedelta(minutes=5)).isoformat()
        created = await reminders.create({"text": "Dismissed", "trigger_at": past})
        await reminders.dismiss(created["id"])
        result = await reminders.get_fired()
        assert result == []

    # ── Dismiss ───────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_dismiss(self, reminders):
        """Dismiss changes status to 'dismissed'."""
        created = await reminders.create({
            "text": "Test reminder",
            "trigger_at": "2026-02-22T19:00:00",
        })
        result = await reminders.dismiss(created["id"])
        assert result["status"] == "dismissed"

    @pytest.mark.asyncio
    async def test_dismiss_not_found(self, reminders):
        """Dismiss returns error for nonexistent reminder."""
        result = await reminders.dismiss("nonexistent-id")
        assert "error" in result

    # ── List upcoming ─────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_list_upcoming(self, reminders):
        """list_upcoming returns pending reminders within time window."""
        future = (datetime.now() + timedelta(minutes=30)).isoformat()
        await reminders.create({"text": "Soon", "trigger_at": future})
        result = await reminders.list_upcoming(hours_ahead=1)
        assert len(result) == 1
        assert result[0]["text"] == "Soon"

    @pytest.mark.asyncio
    async def test_list_upcoming_excludes_past(self, reminders):
        """list_upcoming does not return past reminders."""
        past = (datetime.now() - timedelta(hours=1)).isoformat()
        await reminders.create({"text": "Past", "trigger_at": past})
        result = await reminders.list_upcoming(hours_ahead=1)
        assert result == []

    @pytest.mark.asyncio
    async def test_list_upcoming_excludes_dismissed(self, reminders):
        """list_upcoming does not return dismissed reminders."""
        future = (datetime.now() + timedelta(minutes=30)).isoformat()
        created = await reminders.create({"text": "Dismissed", "trigger_at": future})
        await reminders.dismiss(created["id"])
        result = await reminders.list_upcoming(hours_ahead=1)
        assert result == []

    # ── Delete ────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_delete(self, reminders):
        """Delete removes reminder permanently."""
        created = await reminders.create({
            "text": "Delete me",
            "trigger_at": "2026-02-22T19:00:00",
        })
        result = await reminders.delete(created["id"])
        assert result["status"] == "deleted"

        # Verify it's gone
        fired = await reminders.get_fired()
        assert all(r["id"] != created["id"] for r in fired)

    @pytest.mark.asyncio
    async def test_delete_not_found(self, reminders):
        """Delete returns error for nonexistent reminder."""
        result = await reminders.delete("nonexistent-id")
        assert "error" in result


# ═══════════════════════════════════════════════════════════════════
# Tasks
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture
def tasks(tmp_path):
    """Create a fresh Tasks instance with isolated database."""
    db_path = str(tmp_path / "tasks.db")
    return Tasks(db_path)


class TestTasks:
    """Tests for the Tasks capability."""

    # ── Create ────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_create_task(self, tasks):
        """Creating a task returns the entry with generated ID."""
        result = await tasks.create({"title": "Review project notes"})
        assert "id" in result
        assert result["title"] == "Review project notes"
        assert result["status"] == "pending"
        assert result["priority"] == "normal"  # Default

    @pytest.mark.asyncio
    async def test_create_task_full_fields(self, tasks):
        """Creating a task with all fields."""
        result = await tasks.create({
            "title": "Deploy v2",
            "notes": "Check staging first",
            "due_date": "2026-02-25",
            "priority": "high",
        })
        assert result["notes"] == "Check staging first"
        assert result["due_date"] == "2026-02-25"
        assert result["priority"] == "high"

    @pytest.mark.asyncio
    async def test_create_missing_title(self, tasks):
        """Creating a task without title returns error."""
        result = await tasks.create({"notes": "Some notes"})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create_invalid_priority(self, tasks):
        """Creating a task with invalid priority returns error."""
        result = await tasks.create({"title": "Bad priority", "priority": "urgent"})
        assert "error" in result
        assert "Invalid priority" in result["error"]

    @pytest.mark.asyncio
    async def test_create_valid_priorities(self, tasks):
        """All three priority levels are accepted."""
        for p in ("high", "normal", "low"):
            result = await tasks.create({"title": f"Task {p}", "priority": p})
            assert result["priority"] == p

    # ── List ──────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_list_all(self, tasks):
        """list('all') returns all tasks."""
        await tasks.create({"title": "Task 1"})
        await tasks.create({"title": "Task 2"})
        result = await tasks.list("all")
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_pending(self, tasks):
        """list('pending') returns only pending tasks."""
        t1 = await tasks.create({"title": "Pending"})
        t2 = await tasks.create({"title": "Done"})
        await tasks.complete(t2["id"])
        result = await tasks.list("pending")
        assert len(result) == 1
        assert result[0]["title"] == "Pending"

    @pytest.mark.asyncio
    async def test_list_done(self, tasks):
        """list('done') returns only completed tasks."""
        t1 = await tasks.create({"title": "Done task"})
        await tasks.complete(t1["id"])
        await tasks.create({"title": "Still pending"})
        result = await tasks.list("done")
        assert len(result) == 1
        assert result[0]["title"] == "Done task"

    @pytest.mark.asyncio
    async def test_list_invalid_status(self, tasks):
        """list with invalid status returns empty list."""
        await tasks.create({"title": "Task"})
        result = await tasks.list("invalid")
        assert result == []

    @pytest.mark.asyncio
    async def test_list_empty(self, tasks):
        """list returns empty list when no tasks."""
        result = await tasks.list("all")
        assert result == []

    # ── Complete ───────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_complete_task(self, tasks):
        """Complete marks task as done."""
        created = await tasks.create({"title": "Finish report"})
        result = await tasks.complete(created["id"])
        assert result["status"] == "done"

    @pytest.mark.asyncio
    async def test_complete_not_found(self, tasks):
        """Complete returns error for nonexistent task."""
        result = await tasks.complete("nonexistent-id")
        assert "error" in result

    # ── Get overdue ───────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_overdue(self, tasks):
        """get_overdue returns pending tasks past due date."""
        yesterday = (datetime.now().date() - timedelta(days=1)).isoformat()
        await tasks.create({"title": "Overdue task", "due_date": yesterday})
        result = await tasks.get_overdue()
        assert len(result) == 1
        assert result[0]["title"] == "Overdue task"

    @pytest.mark.asyncio
    async def test_get_overdue_excludes_future(self, tasks):
        """get_overdue does not return future tasks."""
        tomorrow = (datetime.now().date() + timedelta(days=1)).isoformat()
        await tasks.create({"title": "Future task", "due_date": tomorrow})
        result = await tasks.get_overdue()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_overdue_excludes_done(self, tasks):
        """get_overdue does not return completed tasks."""
        yesterday = (datetime.now().date() - timedelta(days=1)).isoformat()
        created = await tasks.create({"title": "Done overdue", "due_date": yesterday})
        await tasks.complete(created["id"])
        result = await tasks.get_overdue()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_overdue_excludes_no_due_date(self, tasks):
        """get_overdue does not return tasks without due date."""
        await tasks.create({"title": "No due date"})
        result = await tasks.get_overdue()
        assert result == []

    # ── Get due today ─────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_due_today(self, tasks):
        """get_due_today returns pending tasks due today."""
        today = datetime.now().date().isoformat()
        await tasks.create({"title": "Due today", "due_date": today})
        result = await tasks.get_due_today()
        assert len(result) == 1
        assert result[0]["title"] == "Due today"

    @pytest.mark.asyncio
    async def test_get_due_today_excludes_other_dates(self, tasks):
        """get_due_today does not return tasks due on other dates."""
        tomorrow = (datetime.now().date() + timedelta(days=1)).isoformat()
        await tasks.create({"title": "Tomorrow", "due_date": tomorrow})
        result = await tasks.get_due_today()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_due_today_excludes_done(self, tasks):
        """get_due_today does not return completed tasks."""
        today = datetime.now().date().isoformat()
        created = await tasks.create({"title": "Done today", "due_date": today})
        await tasks.complete(created["id"])
        result = await tasks.get_due_today()
        assert result == []


# ═══════════════════════════════════════════════════════════════════
# System State
# ═══════════════════════════════════════════════════════════════════

class TestSystemState:
    """Tests for the System State capability."""

    @pytest.mark.asyncio
    async def test_get_returns_all_keys(self):
        """get() returns dict with all 4 required keys."""
        ss = SystemState()
        result = await ss.get()
        assert "datetime" in result
        assert "day_of_week" in result
        assert "battery_percent" in result
        assert "time_of_day" in result

    @pytest.mark.asyncio
    async def test_datetime_is_iso(self):
        """datetime field is in ISO format."""
        ss = SystemState()
        result = await ss.get()
        # Should parse without error
        datetime.fromisoformat(result["datetime"])

    @pytest.mark.asyncio
    async def test_day_of_week_is_string(self):
        """day_of_week is a valid day name."""
        ss = SystemState()
        result = await ss.get()
        valid_days = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"}
        assert result["day_of_week"] in valid_days

    @pytest.mark.asyncio
    async def test_battery_is_integer(self):
        """battery_percent is an integer (>= -1)."""
        ss = SystemState()
        result = await ss.get()
        assert isinstance(result["battery_percent"], int)
        assert result["battery_percent"] >= -1

    @pytest.mark.asyncio
    async def test_time_of_day_classification(self):
        """time_of_day is one of the four valid categories."""
        ss = SystemState()
        result = await ss.get()
        valid = {"morning", "afternoon", "evening", "night"}
        assert result["time_of_day"] in valid

    @pytest.mark.asyncio
    async def test_time_of_day_morning(self):
        """Hours 5-11 are classified as morning."""
        ss = SystemState()
        with patch("capabilities.system_state.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 22, 9, 0, 0)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = await ss.get()
            assert result["time_of_day"] == "morning"

    @pytest.mark.asyncio
    async def test_time_of_day_afternoon(self):
        """Hours 12-16 are classified as afternoon."""
        ss = SystemState()
        with patch("capabilities.system_state.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 22, 14, 0, 0)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = await ss.get()
            assert result["time_of_day"] == "afternoon"

    @pytest.mark.asyncio
    async def test_time_of_day_evening(self):
        """Hours 17-20 are classified as evening."""
        ss = SystemState()
        with patch("capabilities.system_state.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 22, 19, 0, 0)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = await ss.get()
            assert result["time_of_day"] == "evening"

    @pytest.mark.asyncio
    async def test_time_of_day_night(self):
        """Hours 21-4 are classified as night."""
        ss = SystemState()
        with patch("capabilities.system_state.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 22, 23, 0, 0)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = await ss.get()
            assert result["time_of_day"] == "night"


# ═══════════════════════════════════════════════════════════════════
# Voice I/O
# ═══════════════════════════════════════════════════════════════════

class TestVoiceIO:
    """Tests for Voice I/O capability (text mode only — no audio deps needed)."""

    @pytest.fixture
    def voice_io(self):
        """Create a VoiceIO instance."""
        return VoiceIO()

    # ── Initialization ────────────────────────────────────────────

    def test_default_mode_is_text(self, voice_io):
        """Default input mode is text."""
        assert voice_io._input_mode == "text"

    def test_conversation_log_starts_empty(self, voice_io):
        """Conversation log starts empty."""
        assert voice_io._conversation_log == []

    # ── set_input_mode ────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_set_mode_text(self, voice_io):
        """Setting mode to text succeeds."""
        result = await voice_io.set_input_mode("text")
        assert result["status"] == "done"
        assert result["mode"] == "text"

    @pytest.mark.asyncio
    async def test_set_mode_invalid(self, voice_io):
        """Setting invalid mode returns error."""
        result = await voice_io.set_input_mode("telepathy")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_set_mode_voice_without_deps(self, voice_io):
        """Setting voice mode without audio deps returns error."""
        # Audio deps may or may not be available, but if not, should error
        if not voice_io._audio_available or not voice_io._stt_available:
            result = await voice_io.set_input_mode("voice")
            assert "error" in result

    # ── listen (text mode) ────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_listen_text_normal(self, voice_io):
        """listen in text mode returns typed text with confidence 1.0."""
        with patch("capabilities.voice_io.asyncio.to_thread", return_value="Hello Chitra"):
            result = await voice_io.listen()
            assert result["text"] == "Hello Chitra"
            assert result["confidence"] == 1.0

    @pytest.mark.asyncio
    async def test_listen_text_empty(self, voice_io):
        """listen in text mode handles empty input."""
        with patch("capabilities.voice_io.asyncio.to_thread", return_value=""):
            result = await voice_io.listen()
            assert result["text"] == ""
            assert result["confidence"] == 1.0

    @pytest.mark.asyncio
    async def test_listen_text_strips_whitespace(self, voice_io):
        """listen in text mode strips leading/trailing whitespace."""
        with patch("capabilities.voice_io.asyncio.to_thread", return_value="  hello  "):
            result = await voice_io.listen()
            assert result["text"] == "hello"

    @pytest.mark.asyncio
    async def test_listen_text_eof(self, voice_io):
        """listen in text mode handles EOF gracefully."""
        with patch("capabilities.voice_io.asyncio.to_thread", side_effect=EOFError()):
            result = await voice_io._listen_text()
            assert result["text"] == ""
            assert result["confidence"] == 1.0

    # ── speak (text mode) ─────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_speak_text_mode_skips_tts(self, voice_io):
        """speak in text mode skips TTS and returns done."""
        result = await voice_io.speak("Hello")
        assert result["status"] == "done"

    @pytest.mark.asyncio
    async def test_speak_empty_text(self, voice_io):
        """speak with empty text returns done."""
        result = await voice_io.speak("")
        assert result["status"] == "done"

    # ── display ───────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_display_adds_to_log(self, voice_io):
        """display appends to conversation log."""
        await voice_io.display("Hello", "Hi there!")
        assert len(voice_io._conversation_log) == 2
        assert voice_io._conversation_log[0] == {"role": "user", "text": "Hello"}
        assert voice_io._conversation_log[1] == {"role": "chitra", "text": "Hi there!"}

    @pytest.mark.asyncio
    async def test_display_user_only(self, voice_io):
        """display with only user text adds one entry."""
        await voice_io.display("Hello", "")
        assert len(voice_io._conversation_log) == 1
        assert voice_io._conversation_log[0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_display_chitra_only(self, voice_io):
        """display with only chitra text adds one entry."""
        await voice_io.display("", "Hi there!")
        assert len(voice_io._conversation_log) == 1
        assert voice_io._conversation_log[0]["role"] == "chitra"

    @pytest.mark.asyncio
    async def test_display_returns_done(self, voice_io):
        """display returns status done."""
        result = await voice_io.display("Hello", "Hi!")
        assert result["status"] == "done"

    # ── confidence extraction ─────────────────────────────────────

    def test_extract_confidence_no_segments(self, voice_io):
        """_extract_confidence returns 0.0 when no segments."""
        result = voice_io._extract_confidence({"segments": []})
        assert result == 0.0

    def test_extract_confidence_good(self, voice_io):
        """_extract_confidence maps good logprob to high confidence."""
        result = voice_io._extract_confidence({
            "segments": [{"avg_logprob": -0.1}]
        })
        assert result >= 0.8

    def test_extract_confidence_poor(self, voice_io):
        """_extract_confidence maps poor logprob to low confidence."""
        result = voice_io._extract_confidence({
            "segments": [{"avg_logprob": -0.9}]
        })
        assert result <= 0.2

    def test_extract_confidence_clamped(self, voice_io):
        """_extract_confidence clamps to [0.0, 1.0]."""
        # Very bad logprob
        result = voice_io._extract_confidence({
            "segments": [{"avg_logprob": -2.0}]
        })
        assert result == 0.0

        # Perfect logprob
        result = voice_io._extract_confidence({
            "segments": [{"avg_logprob": 0.0}]
        })
        assert result == 1.0
