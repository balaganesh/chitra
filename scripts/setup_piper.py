"""
Piper TTS setup script.

Downloads the Piper binary and English neural voice model into CHITRA_DATA_DIR/tts/.
Safe to run multiple times — skips if already present.
"""

import os
import logging

logger = logging.getLogger(__name__)


def setup_piper():
    """Download Piper TTS binary and voice model."""
    data_dir = os.environ.get("CHITRA_DATA_DIR", os.path.expanduser("~/.chitra/data"))
    tts_dir = os.path.join(data_dir, "tts")
    os.makedirs(tts_dir, exist_ok=True)

    # TODO: Download Piper binary for current platform
    # TODO: Download English neural voice model
    logger.info("Piper TTS setup not yet implemented")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    setup_piper()
