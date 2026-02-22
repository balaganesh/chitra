# Contributing to Chitra

Thank you for your interest in contributing to Chitra. This document explains how to set up the development environment, the branching model, code style requirements, and the process for submitting changes.

---

## Development Setup

**Prerequisites:** Python 3.11+, Ollama (for LLM testing)

```bash
git clone https://github.com/balaganesh/chitra.git
cd chitra
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/setup_storage.py
```

Audio dependencies (whisper, sounddevice, torch) are optional. Text mode works without them.

See [`docs/DEV_SETUP.md`](docs/DEV_SETUP.md) for detailed setup instructions.

---

## Branching Model

- **`main`** — Stable, release-ready code. All CI checks must pass.
- **`dev`** — Active development branch. Changes are merged here first.
- **Feature branches** — Branch from `dev`, name descriptively (e.g., `add-calendar-recurring-events`).

Workflow:
1. Branch from `dev`
2. Make your changes
3. Open a pull request targeting `dev`
4. After review and CI pass, merge to `dev`
5. `dev` is periodically merged to `main` when stable

---

## Code Style

Chitra uses **ruff** for linting. Configuration is in [`pyproject.toml`](pyproject.toml).

```bash
ruff check .
```

All code must pass ruff with zero errors before merging. The CI pipeline enforces this.

Key conventions:
- Line length: 100 characters
- All Python files must have a module-level docstring
- Avoid comments that narrate what the code does — comments should explain *why*, not *what*
- Use `from __future__ import annotations` in capability modules for Python 3.11 compatibility

---

## Testing

All changes must include tests. Run the full suite before submitting:

```bash
python -m pytest tests/ -v
```

All tests must pass. The CI pipeline runs lint and tests on every push and pull request.

When adding a new capability or modifying existing behavior:
- Add unit tests for the new/changed functionality
- If the change affects the conversation pipeline, add or update E2E tests in `TestTextModeE2E`
- Voice-mode tests that require audio hardware should use the `skip_no_audio` marker

---

## Architecture Guidelines

Before making changes, read:
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — System architecture and interaction flows
- [`docs/VISION.md`](docs/VISION.md) — Design philosophy and principles
- [`docs/CAPABILITIES.md`](docs/CAPABILITIES.md) — Capability module API contracts

Key principles:
- **Local first** — No cloud dependencies, no external API calls
- **Conversation is the only interface** — No GUI, no forms, no settings screens
- **AI as orchestrator** — Capabilities are consumed by the AI, not by the user directly
- **Graceful degradation** — Optional dependencies (audio, TTS, STT) degrade gracefully when unavailable
- **Model swappability** — The LLM model is a configuration value, never hardcoded

---

## Pull Request Process

1. Ensure your branch is up to date with `dev`
2. Run `ruff check .` — zero errors
3. Run `python -m pytest tests/ -v` — all tests pass
4. Write a clear PR description explaining *what* and *why*
5. Keep PRs focused — one logical change per PR
6. If your change affects documentation, update the relevant docs

---

## Reporting Issues

Use [GitHub Issues](https://github.com/balaganesh/chitra/issues) for bug reports and feature requests. Please use the provided issue templates.

For security vulnerabilities, see [`SECURITY.md`](SECURITY.md).

---

## License

By contributing to Chitra, you agree that your contributions will be licensed under the [Apache 2.0 License](LICENSE).
