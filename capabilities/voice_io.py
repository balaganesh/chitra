"""
Voice I/O capability.

The conversational interface layer. Handles all input and output — both
voice and text. This is the only way the user interacts with Chitra.

Two first-class input modes:
- Text mode: user types at terminal prompt, zero latency, always available
- Voice mode: microphone → Silero VAD → Whisper STT

In text mode, Chitra displays responses as text only — no TTS audio.
In voice mode, Chitra speaks responses aloud via Piper TTS.

Actions:
    listen() → {"text": str, "confidence": float}
    speak(text) → {"status": "done"}
    display(user_text, chitra_text) → {"status": "done"}
    set_input_mode(mode) → {"status": "done", "mode": str}

Technology:
    STT: OpenAI Whisper (local)
    TTS: Piper TTS (local, subprocess)
    VAD: Silero VAD
    Audio I/O: sounddevice + numpy
    Display: rich library
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess

logger = logging.getLogger(__name__)

# --- Optional audio dependencies ---
# These may not be installed during development or on systems without audio.
# Voice I/O degrades gracefully to text-only mode when they are absent.

_HAS_SOUNDDEVICE = False
try:
    import sounddevice as sd
    import numpy as np

    _HAS_SOUNDDEVICE = True
except ImportError:
    sd = None
    np = None
    logger.warning("sounddevice/numpy not available — voice mode disabled")

_HAS_WHISPER = False
try:
    import whisper

    _HAS_WHISPER = True
except ImportError:
    whisper = None
    logger.warning("openai-whisper not available — STT disabled")

_HAS_SILERO_VAD = False
try:
    import torch

    _HAS_SILERO_VAD = True
except ImportError:
    torch = None
    logger.warning("torch not available — VAD disabled")

# Rich is a core dependency — always present
from rich.console import Console
from rich.text import Text


class VoiceIO:
    """Handles text/voice input, speech output, and conversational display."""

    # Audio recording constants
    SAMPLE_RATE = 16000  # Whisper expects 16kHz
    CHANNELS = 1  # Mono
    VAD_THRESHOLD = 0.5  # Silero VAD speech probability threshold
    SILENCE_DURATION_MS = 1000  # Silence before end-of-speech detection
    MAX_RECORDING_SECONDS = 30  # Safety cap on recording length

    def __init__(self):
        # Input mode: "text" (default) or "voice"
        self._input_mode = "text"

        # Rich console for terminal display
        self._console = Console()

        # In-memory conversation log for display
        self._conversation_log: list[dict] = []

        # Whisper model — loaded lazily on first voice listen()
        self._whisper_model = None
        self._whisper_model_name = os.environ.get("CHITRA_WHISPER_MODEL", "base")

        # Silero VAD model — loaded lazily on first voice listen()
        self._vad_model = None

        # Piper TTS paths — resolved from CHITRA_DATA_DIR
        data_dir = os.environ.get("CHITRA_DATA_DIR", os.path.expanduser("~/.chitra/data"))
        self._piper_binary = os.path.join(data_dir, "tts", "piper")
        self._piper_model = os.path.join(data_dir, "tts", "en_US-lessac-medium.onnx")

        # Capability flags
        self._audio_available = _HAS_SOUNDDEVICE
        self._stt_available = _HAS_WHISPER
        self._vad_available = _HAS_SILERO_VAD
        self._tts_available = (
            os.path.isfile(self._piper_binary)
            and os.access(self._piper_binary, os.X_OK)
        )

        if not self._tts_available:
            logger.warning("Piper TTS not found at %s — TTS disabled", self._piper_binary)

        logger.info(
            "VoiceIO initialized — mode: %s, audio: %s, stt: %s, vad: %s, tts: %s",
            self._input_mode,
            self._audio_available,
            self._stt_available,
            self._vad_available,
            self._tts_available,
        )

    # ── Public actions ──────────────────────────────────────────────

    async def listen(self) -> dict:
        """Return user input as text. Behavior depends on current input mode.

        Text mode: prompts user at terminal, returns typed text with confidence 1.0
        Voice mode: activates mic → VAD → Whisper STT

        Returns:
            {"text": str, "confidence": float}
        """
        try:
            if self._input_mode == "text":
                return await self._listen_text()
            else:
                return await self._listen_voice()
        except Exception as e:
            logger.error("Listen failed: %s", e)
            return {"error": f"Listen failed: {e}"}

    async def speak(self, text: str) -> dict:
        """Convert text to speech via Piper TTS and play through speaker.

        Only plays audio in voice mode. In text mode, returns immediately —
        the user reads Chitra's response on screen instead.

        Returns:
            {"status": "done"}
        """
        try:
            if not text:
                return {"status": "done"}

            # In text mode, skip TTS entirely — display only
            if self._input_mode == "text":
                return {"status": "done"}

            if not self._tts_available:
                logger.info("TTS unavailable — skipping speech")
                return {"status": "done"}

            if not self._audio_available:
                logger.info("Audio unavailable — skipping playback")
                return {"status": "done"}

            await asyncio.to_thread(self._speak_blocking, text)

            logger.info("Spoke: %s", text[:80])
            return {"status": "done"}

        except Exception as e:
            logger.error("Speak failed: %s", e)
            return {"error": f"Speak failed: {e}"}

    async def display(self, user_text: str, chitra_text: str) -> dict:
        """Update the conversational interface display with the latest exchange.

        Appends to conversation log and renders to terminal via rich.

        Returns:
            {"status": "done"}
        """
        try:
            if user_text:
                self._conversation_log.append({"role": "user", "text": user_text})
            if chitra_text:
                self._conversation_log.append({"role": "chitra", "text": chitra_text})

            self._render_exchange(user_text, chitra_text)

            return {"status": "done"}

        except Exception as e:
            logger.error("Display failed: %s", e)
            return {"error": f"Display failed: {e}"}

    async def set_input_mode(self, mode: str) -> dict:
        """Switch between text and voice input modes.

        Returns:
            {"status": "done", "mode": str}
        """
        try:
            if mode not in ("text", "voice"):
                return {"error": f"Invalid mode: {mode}. Must be 'text' or 'voice'"}

            if mode == "voice":
                if not self._audio_available:
                    return {"error": "Cannot switch to voice mode — sounddevice not available"}
                if not self._stt_available:
                    return {"error": "Cannot switch to voice mode — whisper not available"}

            self._input_mode = mode
            logger.info("Input mode set to: %s", mode)
            return {"status": "done", "mode": mode}

        except Exception as e:
            logger.error("Failed to set input mode: %s", e)
            return {"error": f"Mode switch failed: {e}"}

    # ── Text mode ───────────────────────────────────────────────────

    async def _listen_text(self) -> dict:
        """Text mode: prompt user at terminal and return typed input.

        Uses asyncio.to_thread because input() is blocking.
        """
        try:
            user_text = await asyncio.to_thread(input, "You: ")
            user_text = user_text.strip()

            if not user_text:
                return {"text": "", "confidence": 1.0}

            logger.info("Text input received: %d chars", len(user_text))
            return {"text": user_text, "confidence": 1.0}

        except EOFError:
            logger.info("EOF received on text input")
            return {"text": "", "confidence": 1.0}
        except Exception as e:
            logger.error("Text listen failed: %s", e)
            return {"error": f"Text input failed: {e}"}

    # ── Voice mode ──────────────────────────────────────────────────

    async def _listen_voice(self) -> dict:
        """Voice mode: record via mic, detect speech with VAD, transcribe with Whisper.

        Pipeline:
        1. Ensure Whisper + VAD models are loaded (lazy)
        2. Record audio with VAD-based speech detection
        3. Transcribe with Whisper
        4. Return text with confidence score
        """
        if not self._audio_available:
            return {"error": "Voice mode unavailable — sounddevice not installed"}
        if not self._stt_available:
            return {"error": "Voice mode unavailable — whisper not installed"}

        try:
            await self._ensure_voice_models_loaded()

            audio_data = await asyncio.to_thread(self._record_with_vad)

            if audio_data is None or len(audio_data) == 0:
                return {"text": "", "confidence": 0.0}

            result = await asyncio.to_thread(self._transcribe, audio_data)

            text = result.get("text", "").strip()
            confidence = self._extract_confidence(result)

            logger.info("Voice transcribed: '%s' (confidence: %.2f)", text, confidence)
            return {"text": text, "confidence": confidence}

        except Exception as e:
            logger.error("Voice listen failed: %s", e)
            return {"error": f"Voice input failed: {e}"}

    async def _ensure_voice_models_loaded(self):
        """Load Whisper and Silero VAD models if not already loaded.

        Models are loaded in a thread since loading involves file I/O
        and can take several seconds.
        """
        if self._whisper_model is None and _HAS_WHISPER:
            logger.info("Loading Whisper model: %s", self._whisper_model_name)
            self._whisper_model = await asyncio.to_thread(
                whisper.load_model, self._whisper_model_name
            )
            logger.info("Whisper model loaded")

        if self._vad_model is None and _HAS_SILERO_VAD:
            logger.info("Loading Silero VAD model")
            self._vad_model = await asyncio.to_thread(self._load_silero_vad)
            logger.info("Silero VAD model loaded")

    def _load_silero_vad(self):
        """Load Silero VAD model. Blocking — called via asyncio.to_thread.

        NOTE: torch.hub.load may attempt a network fetch on first run if
        the model is not cached locally. For Phase 1 local-only operation,
        the VAD model must be pre-cached during setup. A future improvement
        is to use the silero-vad pip package which bundles the model locally.
        """
        model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            onnx=False,
        )
        return model

    def _record_with_vad(self):
        """Record audio from microphone, using VAD to detect speech boundaries.

        Blocking — always called via asyncio.to_thread.

        Returns numpy array of float32 audio samples, or None if no speech detected.
        """
        chunk_duration_ms = 30
        chunk_samples = int(self.SAMPLE_RATE * chunk_duration_ms / 1000)
        silence_chunks = int(self.SILENCE_DURATION_MS / chunk_duration_ms)
        max_chunks = int(self.MAX_RECORDING_SECONDS * 1000 / chunk_duration_ms)

        audio_chunks = []
        speech_started = False
        silence_count = 0
        total_chunks = 0

        self._console.print("[dim]Listening... (speak now)[/dim]")

        with sd.InputStream(
            samplerate=self.SAMPLE_RATE,
            channels=self.CHANNELS,
            dtype="float32",
            blocksize=chunk_samples,
        ) as stream:
            while total_chunks < max_chunks:
                chunk, overflowed = stream.read(chunk_samples)
                if overflowed:
                    logger.warning("Audio buffer overflow")

                total_chunks += 1

                # Feed chunk to VAD
                audio_tensor = torch.from_numpy(chunk.flatten())
                speech_prob = self._vad_model(audio_tensor, self.SAMPLE_RATE).item()

                if speech_prob >= self.VAD_THRESHOLD:
                    if not speech_started:
                        speech_started = True
                        logger.info("Speech detected")
                    silence_count = 0
                    audio_chunks.append(chunk.copy())
                elif speech_started:
                    # Capture audio during brief pauses within speech
                    audio_chunks.append(chunk.copy())
                    silence_count += 1

                    if silence_count >= silence_chunks:
                        logger.info("End of speech detected")
                        break

        if not audio_chunks:
            logger.info("No speech detected")
            return None

        return np.concatenate(audio_chunks, axis=0)

    def _transcribe(self, audio_data) -> dict:
        """Transcribe audio using Whisper. Blocking — called via asyncio.to_thread.

        Args:
            audio_data: numpy float32 array at 16kHz mono

        Returns:
            Whisper result dict with 'text' and 'segments' keys
        """
        audio_float = audio_data.flatten().astype(np.float32)

        # Normalize to [-1, 1] if needed
        max_val = np.abs(audio_float).max()
        if max_val > 1.0:
            audio_float = audio_float / max_val

        result = self._whisper_model.transcribe(
            audio_float,
            language="en",
            fp16=False,  # CPU-safe
        )
        return result

    def _extract_confidence(self, whisper_result: dict) -> float:
        """Extract a confidence score from Whisper transcription result.

        Maps average log probability across segments to a 0-1 score.
        """
        segments = whisper_result.get("segments", [])
        if not segments:
            return 0.0

        avg_logprobs = [s.get("avg_logprob", -1.0) for s in segments]
        mean_logprob = sum(avg_logprobs) / len(avg_logprobs)

        # avg_logprob range: -1.0 (low) to 0.0 (perfect)
        confidence = max(0.0, min(1.0, 1.0 + mean_logprob))
        return round(confidence, 2)

    # ── TTS pipeline ────────────────────────────────────────────────

    def _speak_blocking(self, text: str):
        """Run Piper TTS and play the output. Blocking — called via asyncio.to_thread.

        Pipes text to Piper stdin, captures raw PCM from stdout, plays via sounddevice.
        """
        try:
            process = subprocess.run(
                [
                    self._piper_binary,
                    "--model", self._piper_model,
                    "--output_raw",
                ],
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=30,
            )

            if process.returncode != 0:
                logger.error(
                    "Piper TTS failed: %s",
                    process.stderr.decode("utf-8", errors="replace"),
                )
                return

            raw_audio = process.stdout
            if not raw_audio:
                logger.warning("Piper produced no audio output")
                return

            # Piper raw output: 16-bit signed PCM, mono
            # Sample rate depends on model (22050 Hz for lessac model)
            piper_sample_rate = 22050
            audio_array = np.frombuffer(raw_audio, dtype=np.int16)
            audio_float = audio_array.astype(np.float32) / 32768.0

            sd.play(audio_float, samplerate=piper_sample_rate)
            sd.wait()

        except subprocess.TimeoutExpired:
            logger.error("Piper TTS timed out")
        except Exception as e:
            logger.error("TTS playback failed: %s", e)

    # ── Display ─────────────────────────────────────────────────────

    def _render_exchange(self, user_text: str, chitra_text: str):
        """Render a conversation exchange to the terminal using rich.

        Minimal design: clean speaker attribution with color, no borders or panels.
        """
        if user_text:
            line = Text()
            line.append("You", style="bold cyan")
            line.append(f"  {user_text}")
            self._console.print(line)

        if chitra_text:
            line = Text()
            line.append("Chitra", style="bold green")
            line.append(f"  {chitra_text}")
            self._console.print(line)

        if user_text or chitra_text:
            self._console.print()
