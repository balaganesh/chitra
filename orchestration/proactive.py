"""
Proactive loop — background task that ticks on a configurable interval.

On every tick:
1. Check triggered reminders (Reminders.get_fired)
2. Check upcoming calendar events (Calendar.get_upcoming)
3. Check neglected contacts (Contacts.get_neglected)
4. Check overdue tasks (Tasks.get_overdue)
5. Lightweight LLM call — is there anything worth surfacing?
6. If yes, formulate message and speak/display
7. If no, sleep until next tick

Never interrupts an active conversation (checks is_user_active flag).
"""

import asyncio
import logging
import os

from llm.prompts import PROACTIVE_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


class ProactiveLoop:
    """Background loop that surfaces relevant information unprompted."""

    def __init__(self, core):
        self.core = core
        self.interval = int(os.environ.get("CHITRA_PROACTIVE_INTERVAL", "60"))

    async def run(self):
        """Run the proactive loop indefinitely.

        Sleeps for the configured interval between ticks. Catches all
        exceptions per-tick so the loop never dies.
        """
        logger.info(
            "Proactive loop starting — interval: %d seconds", self.interval
        )

        while True:
            try:
                await asyncio.sleep(self.interval)
                await self.tick()
            except asyncio.CancelledError:
                logger.info("Proactive loop cancelled — shutting down")
                break
            except Exception as e:
                logger.error("Proactive loop tick failed: %s", e)
                # Don't crash — sleep and try again next tick

    async def tick(self):
        """Single proactive tick — gather context, decide whether to speak.

        Skips entirely if the user is in an active conversation (to avoid
        interrupting mid-exchange).
        """
        # Never interrupt an active conversation
        if self.core.is_user_active:
            logger.debug("Proactive tick skipped — user is active")
            return

        try:
            # Gather proactive context from all relevant capabilities
            context_parts = await self._gather_proactive_context()

            if not context_parts:
                # Nothing to evaluate — no fired reminders, no upcoming events, etc.
                logger.debug("Proactive tick — nothing to evaluate")
                return

            # Build the proactive context description
            context_description = "\n".join(context_parts)

            # Build the proactive prompt
            proactive_message = PROACTIVE_PROMPT_TEMPLATE.format(
                context=context_description
            )

            # Assemble system prompt with memory context (same as regular calls)
            full_context = await self.core.context_assembler.assemble(
                self.core.conversation_history
            )
            system_prompt = full_context["system_prompt"]

            # Lightweight LLM call — should we speak?
            llm_response = await self.core.llm.call(system_prompt, proactive_message)

            should_speak = llm_response.get("should_speak", False)
            response_text = llm_response.get("response", "")

            if should_speak and response_text:
                # Check again — user may have become active during LLM call
                if self.core.is_user_active:
                    logger.info(
                        "Proactive message ready but user became active — skipping"
                    )
                    return

                logger.info("Proactive message: %s", response_text[:80])

                # Display and speak the proactive message
                await self.core.voice_io.display("", response_text)
                await self.core.voice_io.speak(response_text)

                # Dismiss any fired reminders that were surfaced
                await self._dismiss_fired_reminders()

                # Store any memory entries from the proactive LLM call
                memory_entries = llm_response.get("memory_store", [])
                if memory_entries:
                    await self.core.store_memories(memory_entries)
            else:
                logger.debug("Proactive tick — nothing worth surfacing")

        except Exception as e:
            logger.error("Proactive tick error: %s", e)

    async def _gather_proactive_context(self) -> list[str]:
        """Gather context from capabilities for proactive evaluation.

        Returns a list of natural language context strings. Returns an empty
        list if there's nothing noteworthy to evaluate.
        """
        parts = []

        # 1. Fired reminders — reminders whose trigger_at has passed
        try:
            fired = await self.core.reminders.get_fired()
            if fired:
                lines = ["Triggered reminders:"]
                for r in fired:
                    text = r.get("text", "")
                    trigger_at = r.get("trigger_at", "")[:16]
                    lines.append(f"- {text} (was due at {trigger_at})")
                parts.append("\n".join(lines))
        except Exception as e:
            logger.error("Proactive: failed to check reminders: %s", e)

        # 2. Upcoming calendar events (within 1 hour)
        try:
            upcoming = await self.core.calendar.get_upcoming(hours_ahead=1)
            if upcoming:
                lines = ["Upcoming events (next hour):"]
                for event in upcoming:
                    title = event.get("title", "untitled")
                    time = event.get("time", "")
                    duration = event.get("duration_minutes", 60)
                    participants = event.get("participants", [])

                    entry = f"- {title} at {time} ({duration} min)"
                    if participants:
                        entry += f" with {', '.join(participants)}"
                    lines.append(entry)
                parts.append("\n".join(lines))
        except Exception as e:
            logger.error("Proactive: failed to check calendar: %s", e)

        # 3. Neglected contacts (no interaction in 7+ days)
        try:
            neglected = await self.core.contacts.get_neglected(days_threshold=7)
            if neglected:
                lines = ["People you haven't been in touch with recently:"]
                for contact in neglected[:3]:  # Limit to top 3 to avoid overload
                    name = contact.get("name", "unknown")
                    relationship = contact.get("relationship", "")
                    last = contact.get("last_interaction", "unknown")
                    entry = f"- {name}"
                    if relationship:
                        entry += f" ({relationship})"
                    entry += f" — last interaction: {last}"
                    lines.append(entry)
                parts.append("\n".join(lines))
        except Exception as e:
            logger.error("Proactive: failed to check contacts: %s", e)

        # 4. Overdue tasks
        try:
            overdue = await self.core.tasks.get_overdue()
            if overdue:
                lines = ["Overdue tasks:"]
                for task in overdue:
                    title = task.get("title", "untitled")
                    due = task.get("due_date", "unknown")
                    priority = task.get("priority", "normal")
                    lines.append(f"- {title} (due: {due}, priority: {priority})")
                parts.append("\n".join(lines))
        except Exception as e:
            logger.error("Proactive: failed to check tasks: %s", e)

        return parts

    async def _dismiss_fired_reminders(self):
        """Dismiss all fired reminders after they have been surfaced.

        Called after the proactive message is displayed/spoken, so the
        reminders don't fire again on the next tick.
        """
        try:
            fired = await self.core.reminders.get_fired()
            for reminder in fired:
                reminder_id = reminder.get("id")
                if reminder_id:
                    await self.core.reminders.dismiss(reminder_id)
                    logger.info("Auto-dismissed fired reminder: %s", reminder_id)
        except Exception as e:
            logger.error("Failed to dismiss fired reminders: %s", e)
