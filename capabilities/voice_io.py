"""
Voice I/O capability.

The conversational interface layer. Handles all audio input and output.
This is the only way the user interacts with Chitra.

Actions:
    listen() — activate microphone, capture speech, return transcribed text
    speak(text) — convert text to speech and play through speaker
    display(user_text, chitra_text) — update conversational display

Technology:
    STT: OpenAI Whisper (local)
    TTS: Piper TTS (local)
    VAD: Silero VAD
"""

import logging

logger = logging.getLogger(__name__)


class VoiceIO:
    """Handles speech input, speech output, and conversational display."""

    def __init__(self):
        pass

    async def listen(self) -> dict:
        """Activate microphone, detect speech, return transcribed text.

        Returns:
            {"text": str, "confidence": float}
        """
        raise NotImplementedError

    async def speak(self, text: str) -> dict:
        """Convert text to speech and play through speaker.

        Returns:
            {"status": "done"}
        """
        raise NotImplementedError

    async def display(self, user_text: str, chitra_text: str) -> dict:
        """Update the conversational interface display.

        Returns:
            {"status": "done"}
        """
        raise NotImplementedError
