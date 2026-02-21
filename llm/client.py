"""
LLM client — interface to the local Ollama instance.

Critical design requirement: the model is swappable via CHITRA_LLM_MODEL
environment variable. Changing the underlying model requires zero code changes.

All LLM calls go through this client. The Orchestration Core never calls
Ollama directly.

Robust JSON parsing:
- Wrap all JSON parsing in try/except
- On malformed JSON, retry with correction prompt (max 2 retries)
- On persistent failure, return safe fallback response
- Log all malformed outputs
"""

import json
import logging
import os

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


class LLMClient:
    """Interface to the local LLM via Ollama. Model is configurable, never hardcoded."""

    def __init__(self):
        self.model = os.environ.get("CHITRA_LLM_MODEL", "llama3.1:8b")
        self.base_url = "http://localhost:11434"

    async def call(self, system_prompt: str, user_message: str) -> dict:
        """Send a prompt to the local LLM and return parsed structured JSON.

        Implements retry with correction prompt on malformed JSON.
        Falls back to a safe conversational response on persistent failure.

        Returns:
            {
                "intent": str,
                "action": dict | None,
                "response": str,
                "memory_store": list
            }
        """
        raise NotImplementedError

    def _parse_response(self, raw_text: str) -> dict:
        """Parse LLM response text into structured JSON.

        Raises ValueError on malformed JSON.
        """
        raise NotImplementedError

    def _fallback_response(self) -> dict:
        """Return a safe conversational response when LLM output is unusable."""
        return {
            "intent": "unknown",
            "action": None,
            "response": "I'm sorry, I had trouble processing that. Could you say that again?",
            "memory_store": [],
        }
