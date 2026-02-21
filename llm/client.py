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
import re

import httpx

from llm.prompts import CORRECTION_PROMPT

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


class LLMClient:
    """Interface to the local LLM via Ollama. Model is configurable, never hardcoded."""

    def __init__(self):
        self.model = os.environ.get("CHITRA_LLM_MODEL", "llama3.1:8b")
        self.base_url = "http://localhost:11434"
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=120.0)

        logger.info("LLM client initialized — model: %s, url: %s", self.model, self.base_url)

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
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        # First attempt
        raw_text = await self._send(messages)
        if raw_text is None:
            return self._fallback_response()

        parsed = self._parse_response(raw_text)
        if parsed is not None:
            return parsed

        # Retry loop with correction prompt
        for attempt in range(1, MAX_RETRIES + 1):
            logger.warning(
                "Malformed JSON from LLM (attempt %d/%d), retrying with correction",
                attempt, MAX_RETRIES,
            )

            # Append the malformed response and correction prompt to the conversation
            messages.append({"role": "assistant", "content": raw_text})
            messages.append({"role": "user", "content": CORRECTION_PROMPT})

            raw_text = await self._send(messages)
            if raw_text is None:
                return self._fallback_response()

            parsed = self._parse_response(raw_text)
            if parsed is not None:
                logger.info("JSON parsed successfully on retry %d", attempt)
                return parsed

        # All retries exhausted
        logger.error("LLM output unusable after %d retries — using fallback", MAX_RETRIES)
        return self._fallback_response()

    async def _send(self, messages: list[dict]) -> str | None:
        """Send messages to Ollama chat API and return raw response text.

        Returns None on connection or API failure.
        """
        try:
            response = await self._client.post(
                "/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "format": "json",
                },
            )
            response.raise_for_status()

            data = response.json()
            content = data.get("message", {}).get("content", "")

            if not content:
                logger.error("Empty response from LLM")
                return None

            return content

        except httpx.ConnectError:
            logger.error(
                "Cannot connect to Ollama at %s — is it running? (ollama serve)",
                self.base_url,
            )
            return None
        except httpx.TimeoutException:
            logger.error("LLM request timed out")
            return None
        except httpx.HTTPStatusError as e:
            logger.error("LLM API error: %s", e)
            return None
        except Exception as e:
            logger.error("LLM call failed: %s", e)
            return None

    def _parse_response(self, raw_text: str) -> dict | None:
        """Parse LLM response text into structured JSON.

        Attempts to extract valid JSON even if the LLM wraps it in
        markdown code blocks or adds extra text around it.

        Returns parsed dict on success, None on failure.
        """
        try:
            # First try: direct parse
            result = json.loads(raw_text)
            return self._validate_response(result)
        except json.JSONDecodeError:
            pass

        # Second try: extract JSON from markdown code blocks
        try:
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
            if match:
                result = json.loads(match.group(1))
                return self._validate_response(result)
        except json.JSONDecodeError:
            pass

        # Third try: find the first { ... } block in the text
        try:
            start = raw_text.index("{")
            # Find the matching closing brace by counting braces
            depth = 0
            for i in range(start, len(raw_text)):
                if raw_text[i] == "{":
                    depth += 1
                elif raw_text[i] == "}":
                    depth -= 1
                    if depth == 0:
                        result = json.loads(raw_text[start:i + 1])
                        return self._validate_response(result)
        except (ValueError, json.JSONDecodeError):
            pass

        # All parsing attempts failed
        logger.error("Failed to parse LLM response as JSON: %s", raw_text[:200])
        return None

    def _validate_response(self, result: dict) -> dict | None:
        """Validate that parsed JSON has the required fields.

        Fills in missing optional fields with safe defaults rather than
        rejecting the entire response.
        """
        if not isinstance(result, dict):
            logger.error("LLM response is not a JSON object")
            return None

        # "response" is the only truly required field — Chitra must say something
        if "response" not in result:
            logger.error("LLM response missing 'response' field")
            return None

        # Fill in optional fields with safe defaults
        result.setdefault("intent", "unknown")
        result.setdefault("action", None)
        result.setdefault("memory_store", [])

        return result

    def _fallback_response(self) -> dict:
        """Return a safe conversational response when LLM output is unusable."""
        return {
            "intent": "unknown",
            "action": None,
            "response": "I'm sorry, I had trouble processing that. Could you say that again?",
            "memory_store": [],
        }

    async def close(self):
        """Close the HTTP client. Call on shutdown."""
        await self._client.aclose()
