# Chitra — Linux Device Deployment Guide

How to deploy Chitra as a complete package (Ubuntu Server + Ollama + Chitra) on a small Linux device.

This guide covers hardware selection, OS setup, and a step-by-step install process. After setup, the device boots directly into Chitra with no login screen, no desktop, and no shell visible to the user.

---

## Resource Budget

What Chitra needs at runtime:

| Component | RAM | Storage | Notes |
|---|---|---|---|
| Ollama + qwen2.5:7b | ~6 GB | ~5 GB | The heaviest component |
| Whisper base model | ~1 GB | ~150 MB | CPU inference, loaded lazily |
| Silero VAD + PyTorch | ~0.5 GB | ~2 GB | Shared with Whisper's PyTorch |
| Piper TTS | ~0.2 GB | ~80 MB | Subprocess, not always resident |
| Python + Chitra code | ~0.3 GB | ~50 MB | Lightweight |
| Ubuntu Server 24.04 | ~0.5 GB | ~4 GB | Minimal install, no desktop |
| **Total** | **~8.5 GB active** | **~12 GB** | 16 GB RAM gives comfortable headroom |

**Minimum spec: 16 GB RAM, 32 GB storage, 4+ CPU cores, ARM64 or x86_64.**

---

## Hardware Options

### Tier 1: Best Experience (~$150–250)

- **Mini PC** (Beelink, GMKtec, ACEMAGIC) with Intel N100/N305 or AMD Ryzen 5, 16 GB RAM, 256 GB SSD
- x86_64 — everything works out of the box (Ollama, Whisper, Piper all have native x86_64 builds)
- Size: roughly a paperback book. Not truly handheld but very portable.
- **Recommended for first deployment** — fewest compatibility issues

### Tier 2: Smallest Form Factor (~$100–150)

- **Orange Pi 5 Plus 16 GB** (Rockchip RK3588, ARM64, has NPU)
- Credit-card-sized SBC, genuinely handheld
- ARM64 — Ollama and Piper have ARM64 Linux builds
- Inference will be slower than x86 (expect ~2–4 tokens/sec from qwen2.5:7b)
- Needs: case, power supply, USB microphone, USB speaker, microSD/eMMC

### Tier 3: Budget / Educational (~$80–100)

- **Raspberry Pi 5 16 GB** (Broadcom BCM2712, ARM64)
- Widely available, huge community support
- Very slow LLM inference (~1–2 tokens/sec) — usable but response times are 30–60 seconds
- Good for proving it works, not for daily use

### Not Recommended

- Raspberry Pi 5 8 GB — will run out of RAM
- Any device with less than 16 GB RAM
- Devices without ARM64 or x86_64 architecture

### Audio Hardware

- USB microphone (any basic one, ~$10)
- USB speaker or 3.5mm speaker (if the device has a headphone jack)
- Or: USB speakerphone combo (~$25) for clean single-device audio

---

## Deployment Architecture

```
Power on
  → Linux kernel boots
    → Systemd starts
      → ollama.service starts (loads qwen2.5:7b)
        → chitra.service starts (After=ollama.service)
          → Voice I/O initializes (mic + speaker + Piper TTS)
            → [First boot] Onboarding conversation begins
            → [Subsequent boots] Proactive loop + conversation loop
```

No login prompt. No desktop. No shell visible to the user.

---

## Step-by-Step Setup

### Step 1: Flash Ubuntu Server

1. Download **Ubuntu Server 24.04 LTS** (ARM64 or AMD64 depending on device)
2. Flash to microSD/USB/SSD using Balena Etcher or `dd`
3. Boot, complete basic Ubuntu setup:
   - Username: `chitra`
   - Hostname: `chitra-device`
4. Connect to WiFi/Ethernet for initial setup (only needed once for package downloads)

### Step 2: Install System Dependencies

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv git libasound2-dev libportaudio2 libsndfile1 curl alsa-utils
```

### Step 3: Install Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:7b
```

This downloads ~5 GB. On a slow connection, it may take a while.

### Step 4: Clone and Set Up Chitra

```bash
cd ~
git clone https://github.com/balaganesh/chitra.git
cd chitra
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 5: Set Up Piper TTS and Storage

```bash
python scripts/setup_piper.py
python scripts/setup_storage.py
cp .env.example .env
```

Edit `.env` if you want to change defaults (e.g., set `CHITRA_INPUT_MODE=voice` for voice-first mode).

### Step 6: Test Manually

```bash
source venv/bin/activate
python main.py
```

This should start Chitra. If it is the first run, onboarding will begin. Type responses at the `You:` prompt. Press Ctrl+C to exit.

### Step 7: Test Audio (Voice Mode)

```bash
# List audio devices
aplay -l
arecord -l

# Test playback
speaker-test -t wav -c 1

# Test recording (5 seconds)
arecord -d 5 -f S16_LE -r 16000 /tmp/test.wav
aplay /tmp/test.wav
```

### Step 8: Configure Auto-Start (Optional)

To make Chitra start automatically on boot:

Create `/etc/systemd/system/chitra.service`:

```ini
[Unit]
Description=Chitra AI OS
After=network.target ollama.service
Wants=ollama.service

[Service]
Type=simple
User=chitra
WorkingDirectory=/home/chitra/chitra
Environment=CHITRA_DATA_DIR=/home/chitra/.chitra/data
Environment=CHITRA_INPUT_MODE=voice
ExecStart=/home/chitra/chitra/venv/bin/python main.py
Restart=on-failure
RestartSec=5
StandardInput=tty
StandardOutput=tty
TTYPath=/dev/tty1

[Install]
WantedBy=multi-user.target
```

Enable it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable chitra.service
```

Configure auto-login on tty1:

```bash
sudo mkdir -p /etc/systemd/system/getty@tty1.service.d
sudo tee /etc/systemd/system/getty@tty1.service.d/override.conf > /dev/null <<EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty -o '-p -f chitra' -a chitra --noclear %I \$TERM
EOF
```

Reboot to verify everything starts automatically.

---

## Troubleshooting

**Ollama not starting:** Run `ollama serve` manually to see error output. Check `journalctl -u ollama`.

**No audio devices:** Verify USB mic/speaker are connected with `arecord -l` and `aplay -l`. Install ALSA utils if missing.

**Slow LLM responses:** Expected on ARM devices. Consider using a smaller model like `qwen2.5:3b` by setting `CHITRA_LLM_MODEL=qwen2.5:3b` in `.env`.

**Out of memory:** Check `free -h`. If less than 2 GB free after Ollama loads, the device needs more RAM or a smaller model.

**Piper TTS not working:** Run `python scripts/setup_piper.py` again. Check that `~/.chitra/data/tts/piper` exists and is executable.

---

## What to Buy (Recommendation)

For your first device: a **mini PC with 16 GB RAM and x86_64**:
- Beelink S12 Pro (Intel N100, 16 GB, 500 GB SSD) — ~$150–180
- ACEMAGIC S1 (similar specs) — ~$140

These give the fastest path to a working demo. Once it works, you can try porting to a smaller ARM device like the Orange Pi 5 Plus for a truly handheld form factor.

---

*This is a planning document. The deploy script (`scripts/deploy.sh`) and systemd unit file (`scripts/chitra.service`) will be created when deployment is actively pursued.*
