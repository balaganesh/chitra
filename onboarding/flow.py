"""
First-run onboarding conversation.

On first run (data directory is empty or first_run flag is set), Chitra
conducts a short conversational onboarding to seed Memory with initial context.

Onboarding asks:
- User's name
- Key people in their life and relationships
- Basic work schedule
- Any immediate preferences

Every answer is stored to Memory with confidence 1.0 and source "stated".
Onboarding ends with a summary of what Chitra now knows.

Must never be skipped on first run. Must never appear on subsequent boots.
"""

import logging

logger = logging.getLogger(__name__)


class OnboardingFlow:
    """Guides the user through first-run setup via conversation."""

    def __init__(self, core):
        self.core = core

    async def should_run(self) -> bool:
        """Check if onboarding needs to run (first boot detection)."""
        raise NotImplementedError

    async def run(self):
        """Execute the onboarding conversation flow."""
        raise NotImplementedError
