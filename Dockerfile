# Chitra — Linux validation image
# Used for testing Linux compatibility on macOS development machines.
# NOT a production deployment image.
#
# Build:  docker build -t chitra-linux .
# Test:   docker run chitra-linux python -m pytest tests/ -v
# Piper:  docker run chitra-linux python scripts/setup_piper.py

FROM python:3.11-slim

# System deps for sounddevice (ALSA headers) and audio file handling
RUN apt-get update && apt-get install -y --no-install-recommends \
    libasound2-dev \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-m", "pytest", "tests/", "-v"]
