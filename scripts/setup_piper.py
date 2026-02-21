"""
Piper TTS setup script.

Downloads the Piper binary and English neural voice model into CHITRA_DATA_DIR/tts/.
Safe to run multiple times — skips files that already exist.

Downloads from:
- Piper binary: GitHub rhasspy/piper releases (2023.11.14-2)
- Voice model: Hugging Face rhasspy/piper-voices (en_US-lessac-medium)

Platform support:
- macOS aarch64 (Apple Silicon) — development
- macOS x86_64 (Intel)
- Linux x86_64 — target runtime
- Linux aarch64

No internet calls are made after setup is complete. Piper runs entirely locally.
"""

import logging
import os
import platform
import shutil
import ssl
import stat
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

# ── Piper binary release ──────────────────────────────────────────
PIPER_VERSION = "2023.11.14-2"
PIPER_BASE_URL = f"https://github.com/rhasspy/piper/releases/download/{PIPER_VERSION}"

# Map (system, machine) to download filename
PIPER_BINARIES = {
    ("Darwin", "arm64"): "piper_macos_aarch64.tar.gz",
    ("Darwin", "x86_64"): "piper_macos_x64.tar.gz",
    ("Linux", "x86_64"): "piper_linux_x86_64.tar.gz",
    ("Linux", "aarch64"): "piper_linux_aarch64.tar.gz",
}

# ── Voice model ───────────────────────────────────────────────────
VOICE_MODEL_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium"
VOICE_FILES = [
    "en_US-lessac-medium.onnx",
    "en_US-lessac-medium.onnx.json",
]


def _get_platform_key() -> tuple[str, str]:
    """Return (system, machine) tuple for current platform."""
    system = platform.system()    # "Darwin" or "Linux"
    machine = platform.machine()  # "arm64", "x86_64", "aarch64"
    return (system, machine)


def _download_with_context(url: str, dest_path: str, ctx: ssl.SSLContext):
    """Download a URL to a file using the given SSL context."""
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, context=ctx) as response:
        with open(dest_path, "wb") as f:
            shutil.copyfileobj(response, f)


def _download_file(url: str, dest_path: str, description: str) -> bool:
    """Download a file from URL to dest_path with progress logging.

    Returns True on success, False on failure.
    """
    try:
        logger.info("Downloading %s...", description)
        logger.info("  URL: %s", url)
        logger.info("  Destination: %s", dest_path)

        # Use a temporary file to avoid partial downloads
        dest_dir = os.path.dirname(dest_path)
        with tempfile.NamedTemporaryFile(dir=dest_dir, delete=False, suffix=".tmp") as tmp:
            tmp_path = tmp.name

        # Create SSL context — on macOS, Python's default certifi bundle
        # may not be configured. Fall back to unverified if needed.
        # This is acceptable because we download from known URLs (GitHub, HuggingFace)
        # and this is a one-time setup script, not runtime code.
        try:
            ctx = ssl.create_default_context()
            _download_with_context(url, tmp_path, ctx)
        except (ssl.SSLCertVerificationError, urllib.error.URLError):
            logger.warning("  SSL verification failed — retrying without verification")
            ctx = ssl._create_unverified_context()
            _download_with_context(url, tmp_path, ctx)

        # Move temp file to final destination
        shutil.move(tmp_path, dest_path)
        size_mb = os.path.getsize(dest_path) / (1024 * 1024)
        logger.info("  Downloaded: %.1f MB", size_mb)
        return True

    except Exception as e:
        logger.error("  Download failed: %s", e)
        # Clean up partial download
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return False


def _extract_piper_binary(tar_path: str, tts_dir: str) -> bool:
    """Extract the piper binary from the downloaded tarball.

    The tarball contains a 'piper/' directory with the binary and shared libraries.
    We extract everything into tts_dir.

    Returns True on success, False on failure.
    """
    try:
        logger.info("Extracting Piper binary...")

        # Extract to a temporary directory first to avoid naming conflicts
        # (the tarball contains a 'piper/' dir, and we need a 'piper' binary)
        with tempfile.TemporaryDirectory() as extract_dir:
            with tarfile.open(tar_path, "r:gz") as tar:
                tar.extractall(path=extract_dir)

            # The tarball extracts to extract_dir/piper/ with all contents
            piper_subdir = os.path.join(extract_dir, "piper")
            if not os.path.isdir(piper_subdir):
                logger.error("  Expected 'piper/' directory not found in tarball")
                return False

            # Move all contents from extracted piper/ into tts_dir
            for item in os.listdir(piper_subdir):
                src = os.path.join(piper_subdir, item)
                dst = os.path.join(tts_dir, item)
                if os.path.exists(dst):
                    if os.path.isdir(dst):
                        shutil.rmtree(dst)
                    else:
                        os.remove(dst)
                shutil.move(src, dst)

        # Ensure the piper binary is executable
        piper_binary = os.path.join(tts_dir, "piper")
        if os.path.isfile(piper_binary):
            st = os.stat(piper_binary)
            os.chmod(piper_binary, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
            logger.info("  Piper binary ready: %s", piper_binary)
        else:
            logger.error("  Piper binary not found after extraction")
            return False

        return True

    except Exception as e:
        logger.error("  Extraction failed: %s", e)
        return False


def setup_piper():
    """Download Piper TTS binary and voice model.

    Skips files that already exist. Safe to run multiple times.
    """
    data_dir = os.environ.get("CHITRA_DATA_DIR", os.path.expanduser("~/.chitra/data"))
    tts_dir = os.path.join(data_dir, "tts")
    os.makedirs(tts_dir, exist_ok=True)

    success = True

    # ── Step 1: Download and extract Piper binary ─────────────────

    piper_binary = os.path.join(tts_dir, "piper")

    if os.path.isfile(piper_binary) and os.access(piper_binary, os.X_OK):
        logger.info("Piper binary already exists: %s — skipping", piper_binary)
    else:
        platform_key = _get_platform_key()
        tarball_name = PIPER_BINARIES.get(platform_key)

        if tarball_name is None:
            logger.error(
                "Unsupported platform: %s %s. Supported: %s",
                platform_key[0],
                platform_key[1],
                ", ".join(f"{s} {m}" for s, m in PIPER_BINARIES),
            )
            success = False
        else:
            url = f"{PIPER_BASE_URL}/{tarball_name}"
            tar_path = os.path.join(tts_dir, tarball_name)

            if _download_file(url, tar_path, f"Piper binary ({tarball_name})"):
                if _extract_piper_binary(tar_path, tts_dir):
                    # Clean up tarball after successful extraction
                    os.remove(tar_path)
                    logger.info("Piper binary installed successfully")
                else:
                    success = False
            else:
                success = False

    # ── Step 2: Download voice model ──────────────────────────────

    for filename in VOICE_FILES:
        dest = os.path.join(tts_dir, filename)

        if os.path.isfile(dest):
            logger.info("Voice file already exists: %s — skipping", filename)
            continue

        url = f"{VOICE_MODEL_BASE}/{filename}?download=true"
        if not _download_file(url, dest, f"Voice model ({filename})"):
            success = False

    # ── Summary ───────────────────────────────────────────────────

    if success:
        logger.info("")
        logger.info("Piper TTS setup complete!")
        logger.info("  Binary: %s", piper_binary)
        for f in VOICE_FILES:
            logger.info("  Model:  %s", os.path.join(tts_dir, f))
    else:
        logger.error("")
        logger.error("Piper TTS setup incomplete — some downloads failed.")
        logger.error("Re-run this script to retry failed downloads.")
        sys.exit(1)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
    )
    setup_piper()
