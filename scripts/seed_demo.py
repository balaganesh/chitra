"""
Seed script for the PHASE1_SCOPE.md demo scenario.

Pre-populates all capability databases with the data needed to run the
demo scenario end-to-end. Uses today's date so all temporal references
(upcoming meetings, neglected contacts, overdue tasks) are correct.

Safe to run multiple times — wipes and re-creates all databases each run.

Usage:
    python scripts/seed_demo.py

After seeding, boot Chitra normally:
    python main.py

The demo scenario from PHASE1_SCOPE.md:

  Chitra boots. The user says "Chitra". Chitra responds:

    "Good morning Bala. You have a team meeting at 10. It's 8:47.
     You mentioned last week you wanted to call your mother more often —
     it's been 5 days since you last noted a call with her."

  Bala: "Set a reminder to call her at 7 this evening.
         Also remind me 15 minutes before the meeting."

  Chitra: "Done. Reminder set for 7pm for your mother.
           Meeting reminder set for 9:45."

  (Proactive, unprompted):
    "You have no tasks scheduled for this afternoon. You had noted
     wanting to review your project notes this week — want me to
     remind you at 2pm?"

  Bala: "Yes."

  Chitra: "Reminder set for 2pm — review project notes."
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta

# Add project root to path so we can import capabilities
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from capabilities.calendar import Calendar
from capabilities.contacts import Contacts
from capabilities.memory import Memory
from capabilities.tasks import Tasks

logger = logging.getLogger(__name__)


def _wipe_databases(data_dir: str):
    """Remove all existing capability databases so we start clean."""
    db_files = [
        "contacts.db",
        "calendar.db",
        "reminders.db",
        "tasks.db",
        "memory.db",
    ]
    for db_file in db_files:
        path = os.path.join(data_dir, db_file)
        if os.path.exists(path):
            os.remove(path)
            logger.info("Removed: %s", path)


def _mark_onboarding_complete(data_dir: str):
    """Create the onboarding marker so Chitra skips onboarding on boot.

    The seed data replaces what onboarding would have collected.
    """
    marker = os.path.join(data_dir, ".onboarding_complete")
    with open(marker, "w") as f:
        f.write("onboarding completed — seeded by seed_demo.py\n")
    logger.info("Onboarding marker created: %s", marker)


async def seed_contacts(data_dir: str) -> dict:
    """Seed contacts and return created contact dicts keyed by name.

    Creates:
    - Amma (mother) — last interaction 5 days ago
    - Ravi (best friend) — last interaction 2 days ago
    - Priya (colleague) — last interaction today
    """
    contacts = Contacts(os.path.join(data_dir, "contacts.db"))
    today = datetime.now().date()
    created = {}

    contact_data = [
        {
            "name": "Amma",
            "relationship": "mother",
            "phone": "+91-9876543210",
            "notes": "Lives in Chennai. Prefers evening calls after 6pm.",
            "communication_preference": "phone call",
        },
        {
            "name": "Ravi",
            "relationship": "best friend",
            "phone": "+91-9876543211",
            "email": "ravi@example.com",
            "notes": "College friend. Works in Bangalore.",
            "communication_preference": "text message",
        },
        {
            "name": "Priya",
            "relationship": "colleague",
            "email": "priya@work.com",
            "notes": "Works on the same team. Project lead.",
            "communication_preference": "slack",
        },
    ]

    # Days since last interaction for each contact
    last_interaction_offsets = {
        "Amma": 5,   # 5 days ago — triggers neglected contact alert
        "Ravi": 2,   # recent
        "Priya": 0,  # today
    }

    for data in contact_data:
        result = await contacts.create(data)
        if "error" in result:
            logger.error("Failed to create contact %s: %s", data["name"], result["error"])
            continue

        name = data["name"]
        contact_id = result["id"]
        created[name] = result

        # Override last_interaction to the correct offset
        offset_days = last_interaction_offsets[name]
        interaction_date = (today - timedelta(days=offset_days)).isoformat()

        await contacts.update(contact_id, {"last_interaction": interaction_date})
        logger.info("  Contact: %s (last interaction: %s)", name, interaction_date)

    return created


async def seed_calendar(data_dir: str):
    """Seed calendar events for the demo scenario.

    Creates:
    - Team meeting today, 30 minutes from now (so it appears in upcoming events)
    - No afternoon events (so the proactive loop can note the free afternoon)

    The meeting time is set dynamically so the demo works regardless of
    when the seed script is run.
    """
    calendar = Calendar(os.path.join(data_dir, "calendar.db"))
    now = datetime.now()
    today = now.date().isoformat()

    # Set meeting 30 minutes from now so it shows up in upcoming events
    meeting_time = now + timedelta(minutes=30)
    meeting_time_str = meeting_time.strftime("%H:%M")

    events = [
        {
            "title": "Team meeting",
            "date": today,
            "time": meeting_time_str,
            "duration_minutes": 60,
            "notes": "Weekly standup and project review",
            "participants": ["Priya", "Arun", "Deepa"],
        },
    ]

    for event in events:
        result = await calendar.create(event)
        if "error" in result:
            logger.error("Failed to create event: %s", result["error"])
        else:
            logger.info("  Event: %s at %s on %s", event["title"], event["time"], event["date"])


async def seed_tasks(data_dir: str):
    """Seed tasks for the demo scenario.

    Creates:
    - "Review project notes" — pending, due this week, normal priority
      (the proactive loop should suggest a reminder for this)
    - A couple of other tasks for realism
    """
    tasks = Tasks(os.path.join(data_dir, "tasks.db"))
    today = datetime.now().date()

    # Due date for "review project notes" — end of this week (Friday)
    # Calculate days until Friday (weekday 4)
    days_until_friday = (4 - today.weekday()) % 7
    if days_until_friday == 0 and today.weekday() == 4:
        # It's already Friday — due today
        friday = today
    elif days_until_friday == 0:
        # It's Saturday or later in the week cycle, use next Friday
        friday = today + timedelta(days=7)
    else:
        friday = today + timedelta(days=days_until_friday)

    task_data = [
        {
            "title": "Review project notes",
            "notes": "Go through last week's meeting notes and prepare summary",
            "due_date": friday.isoformat(),
            "priority": "normal",
        },
        {
            "title": "Update documentation",
            "notes": "Add new API endpoints to the docs",
            "due_date": (today + timedelta(days=3)).isoformat(),
            "priority": "low",
        },
        {
            "title": "Prepare presentation for Friday",
            "notes": "Quarterly review slides",
            "due_date": friday.isoformat(),
            "priority": "high",
        },
    ]

    for task in task_data:
        result = await tasks.create(task)
        if "error" in result:
            logger.error("Failed to create task: %s", result["error"])
        else:
            logger.info("  Task: %s (due: %s, priority: %s)", task["title"], task["due_date"], task["priority"])


async def seed_memory(data_dir: str, contacts: dict):
    """Seed memory entries for the demo scenario.

    Creates the same memories that onboarding would have collected,
    plus the key memory that drives the demo:
    - "Bala mentioned wanting to call his mother more often"
    """
    memory = Memory(os.path.join(data_dir, "memory.db"))

    # Get Amma's contact_id if available
    amma_id = contacts.get("Amma", {}).get("id")
    ravi_id = contacts.get("Ravi", {}).get("id")

    # Memories that onboarding would have collected
    onboarding_memories = [
        {
            "category": "fact",
            "subject": "name",
            "content": "The user's name is Bala",
            "confidence": 1.0,
            "source": "stated",
        },
        {
            "category": "preference",
            "subject": "input_mode",
            "content": "Prefers text input mode",
            "confidence": 1.0,
            "source": "stated",
        },
        {
            "category": "relationship",
            "subject": "key_people",
            "content": "Amma is his mother, lives in Chennai. Ravi is his best friend from college.",
            "confidence": 1.0,
            "source": "stated",
        },
        {
            "category": "fact",
            "subject": "work_schedule",
            "content": "Work schedule: Usually starts work around 9am, finishes by 6pm. Works Monday to Friday.",
            "confidence": 1.0,
            "source": "stated",
        },
    ]

    # The key memory that drives the demo scenario —
    # Bala mentioned wanting to call his mother more often
    demo_memories = [
        {
            "category": "preference",
            "subject": "calling_mother",
            "content": "Bala mentioned last week that he wants to call his mother more often. He feels he hasn't been keeping in touch enough.",
            "confidence": 1.0,
            "source": "stated",
            "contact_id": amma_id,
        },
        {
            "category": "observation",
            "subject": "morning_routine",
            "content": "Bala usually checks in with Chitra first thing in the morning around 8:30-9am before starting work.",
            "confidence": 0.8,
            "source": "inferred",
        },
        {
            "category": "relationship",
            "subject": "amma",
            "content": "Amma (mother) lives in Chennai. Prefers phone calls in the evening after 6pm.",
            "confidence": 1.0,
            "source": "stated",
            "contact_id": amma_id,
        },
        {
            "category": "relationship",
            "subject": "ravi",
            "content": "Ravi is Bala's best friend from college. Lives in Bangalore. They text regularly.",
            "confidence": 1.0,
            "source": "stated",
            "contact_id": ravi_id,
        },
        {
            "category": "preference",
            "subject": "project_notes",
            "content": "Bala noted this week that he wants to review his project notes. He hasn't had time yet.",
            "confidence": 1.0,
            "source": "stated",
        },
    ]

    all_memories = onboarding_memories + demo_memories

    for entry in all_memories:
        result = await memory.store(entry)
        if "error" in result:
            logger.error("Failed to store memory: %s", result["error"])
        else:
            logger.info("  Memory: [%s] %s", entry["category"], entry["subject"])


async def seed_all():
    """Run the complete seed process."""
    data_dir = os.environ.get("CHITRA_DATA_DIR", os.path.expanduser("~/.chitra/data"))
    os.makedirs(data_dir, exist_ok=True)

    logger.info("=" * 60)
    logger.info("Chitra Demo Seed Script")
    logger.info("=" * 60)
    logger.info("Data directory: %s", data_dir)
    logger.info("Date: %s", datetime.now().strftime("%Y-%m-%d %H:%M"))
    logger.info("")

    # Step 1: Wipe existing databases
    logger.info("Step 1: Wiping existing databases...")
    _wipe_databases(data_dir)
    logger.info("")

    # Step 2: Seed contacts
    logger.info("Step 2: Seeding contacts...")
    contacts = await seed_contacts(data_dir)
    logger.info("")

    # Step 3: Seed calendar
    logger.info("Step 3: Seeding calendar events...")
    await seed_calendar(data_dir)
    logger.info("")

    # Step 4: Seed tasks
    logger.info("Step 4: Seeding tasks...")
    await seed_tasks(data_dir)
    logger.info("")

    # Step 5: Seed memory
    logger.info("Step 5: Seeding memory entries...")
    await seed_memory(data_dir, contacts)
    logger.info("")

    # Step 6: Mark onboarding complete
    logger.info("Step 6: Marking onboarding complete...")
    _mark_onboarding_complete(data_dir)
    logger.info("")

    # Summary
    logger.info("=" * 60)
    logger.info("Demo seed complete!")
    logger.info("")
    logger.info("Seeded data:")
    logger.info("  Contacts: Amma (mother, 5 days ago), Ravi (friend), Priya (colleague)")
    meeting_time = (datetime.now() + timedelta(minutes=30)).strftime("%H:%M")
    logger.info("  Calendar: Team meeting today at %s (30 min from now)", meeting_time)
    logger.info("  Tasks:    Review project notes, Update docs, Prepare presentation")
    logger.info("  Memory:   9 entries (name, preferences, relationships, observations)")
    logger.info("  Onboarding: marked complete")
    logger.info("")
    logger.info("To run the demo:")
    logger.info("  1. Ensure Ollama is running:  ollama serve")
    logger.info("  2. Pull the model:            ollama pull llama3.1:8b")
    logger.info("  3. Boot Chitra:               python main.py")
    logger.info("=" * 60)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
    )
    asyncio.run(seed_all())
