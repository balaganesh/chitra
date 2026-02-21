"""
First-run onboarding conversation.

On first run (data directory is empty or first_run flag is set), Chitra
conducts a short conversational onboarding to seed Memory with initial context.

Onboarding asks:
- User's name
- Preferred input mode (text or voice)
- Key people in their life and relationships
- Basic work schedule
- Any immediate preferences

Every answer is stored to Memory with confidence 1.0 and source "stated".
Onboarding ends with a summary of what Chitra now knows.

Must never be skipped on first run. Must never appear on subsequent boots.
"""

import logging
import os

logger = logging.getLogger(__name__)


# Onboarding questions — each is a dict with:
#   prompt: what Chitra says to the user
#   memory_category: how to categorize the answer in Memory
#   memory_subject: the subject tag for the memory entry
#   follow_up: optional function to process the answer further
ONBOARDING_STEPS = [
    {
        "prompt": (
            "Hello! I'm Chitra — your AI operating system. "
            "I'd like to get to know you a little before we start. "
            "What's your name?"
        ),
        "memory_category": "fact",
        "memory_subject": "name",
        "format_content": lambda answer: f"The user's name is {answer}",
    },
    {
        "prompt": (
            "Nice to meet you, {name}! Do you prefer typing or speaking to me? "
            "You can always switch later."
        ),
        "memory_category": "preference",
        "memory_subject": "input_mode",
        "format_content": lambda answer: f"Prefers {answer} input mode",
        "process_mode": True,  # Special flag — also sets the input mode
    },
    {
        "prompt": (
            "Tell me about a few important people in your life — "
            "their names and how you know them. For example: "
            "\"Amma is my mother, Ravi is my best friend.\""
        ),
        "memory_category": "relationship",
        "memory_subject": "key_people",
        "format_content": lambda answer: answer,
    },
    {
        "prompt": (
            "What does a typical workday look like for you? "
            "When do you usually start and finish work?"
        ),
        "memory_category": "fact",
        "memory_subject": "work_schedule",
        "format_content": lambda answer: f"Work schedule: {answer}",
    },
    {
        "prompt": (
            "Anything else you'd like me to know right away? "
            "Preferences, habits, things you care about — anything goes. "
            "Or just say \"nothing for now\" and we'll get started."
        ),
        "memory_category": "preference",
        "memory_subject": "initial_preferences",
        "format_content": lambda answer: answer,
        "skip_if_empty": True,  # Don't store if user says "nothing"
    },
]


class OnboardingFlow:
    """Guides the user through first-run setup via conversation."""

    def __init__(self, core):
        self.core = core
        self._onboarding_marker = os.path.join(
            self.core.data_dir, ".onboarding_complete"
        )

    async def should_run(self) -> bool:
        """Check if onboarding needs to run (first boot detection).

        Returns True if the onboarding marker file does not exist.
        The marker is created at the end of successful onboarding.
        """
        if os.path.exists(self._onboarding_marker):
            logger.info("Onboarding marker found — skipping onboarding")
            return False

        logger.info("No onboarding marker — onboarding required")
        return True

    async def run(self):
        """Execute the onboarding conversation flow.

        Walks through each onboarding step: display the prompt, listen for
        the user's answer, store the answer to Memory, then move to the next step.

        At the end, displays a summary and creates the onboarding marker
        so it never runs again.
        """
        try:
            logger.info("Starting onboarding flow")
            user_name = None
            stored_memories = []

            for step in ONBOARDING_STEPS:
                # Personalize the prompt if we know the name
                prompt = step["prompt"]
                if user_name and "{name}" in prompt:
                    prompt = prompt.format(name=user_name)

                # Display the question
                await self.core.voice_io.display("", prompt)
                await self.core.voice_io.speak(prompt)

                # Listen for the answer
                listen_result = await self.core.voice_io.listen()
                if "error" in listen_result:
                    logger.error("Onboarding listen error: %s", listen_result["error"])
                    continue

                answer = listen_result.get("text", "").strip()
                if not answer:
                    continue

                # Display the user's answer
                await self.core.voice_io.display(answer, "")

                # Extract the user's name from the first step
                if step["memory_subject"] == "name":
                    user_name = answer

                # Handle input mode preference
                if step.get("process_mode"):
                    await self._process_input_mode(answer)

                # Skip storage for "nothing" answers on optional steps
                if step.get("skip_if_empty") and self._is_empty_answer(answer):
                    continue

                # Store to Memory
                content = step["format_content"](answer)
                memory_entry = {
                    "category": step["memory_category"],
                    "subject": step["memory_subject"],
                    "content": content,
                    "confidence": 1.0,
                    "source": "stated",
                }

                result = await self.core.memory.store(memory_entry)
                if "error" not in result:
                    stored_memories.append(memory_entry)
                    logger.info(
                        "Onboarding stored: [%s] %s",
                        step["memory_category"],
                        step["memory_subject"],
                    )

            # Display summary
            summary = self._build_summary(user_name, stored_memories)
            await self.core.voice_io.display("", summary)
            await self.core.voice_io.speak(summary)

            # Create onboarding marker so it never runs again
            self._mark_complete()

            logger.info("Onboarding flow complete — %d memories stored", len(stored_memories))

        except Exception as e:
            logger.error("Onboarding flow failed: %s", e)
            # Even if onboarding partially fails, mark it complete
            # to prevent re-running on every boot
            self._mark_complete()

    async def _process_input_mode(self, answer: str):
        """Process the user's input mode preference.

        Tries to detect whether the user prefers text or voice from their answer
        and sets the input mode accordingly.
        """
        answer_lower = answer.lower()

        if any(word in answer_lower for word in ("type", "typing", "text", "keyboard")):
            mode = "text"
        elif any(word in answer_lower for word in ("speak", "speaking", "voice", "talk")):
            mode = "voice"
        else:
            # Default to text if the answer is ambiguous
            mode = "text"
            logger.info("Could not determine input mode from '%s' — defaulting to text", answer)

        result = await self.core.voice_io.set_input_mode(mode)
        if "error" in result:
            logger.warning("Failed to set input mode to '%s': %s", mode, result["error"])
        else:
            logger.info("Input mode set to '%s' during onboarding", mode)

    def _is_empty_answer(self, answer: str) -> bool:
        """Check if the user's answer is effectively empty / 'nothing'."""
        empty_phrases = (
            "nothing",
            "nothing for now",
            "no",
            "nope",
            "not right now",
            "skip",
            "that's it",
            "that's all",
            "none",
            "n/a",
        )
        return answer.lower().strip().rstrip(".!") in empty_phrases

    def _build_summary(self, user_name: str | None, memories: list[dict]) -> str:
        """Build a natural language summary of what was learned during onboarding."""
        if not memories:
            return "We're all set! I'll learn more about you as we talk."

        name_part = f", {user_name}" if user_name else ""

        summary_parts = [f"Great{name_part}! Here's what I know so far:"]
        for mem in memories:
            content = mem["content"]
            # Don't repeat the name fact as-is — it's redundant
            if mem.get("subject", mem.get("memory_subject")) == "name":
                continue
            summary_parts.append(f"• {content}")

        summary_parts.append(
            "\nI'll remember all of this. Let's get started — "
            "just talk to me whenever you need something."
        )

        return "\n".join(summary_parts)

    def _mark_complete(self):
        """Create the onboarding marker file to prevent re-running."""
        try:
            with open(self._onboarding_marker, "w") as f:
                f.write("onboarding completed\n")
            logger.info("Onboarding marker created: %s", self._onboarding_marker)
        except OSError as e:
            logger.error("Failed to create onboarding marker: %s", e)
