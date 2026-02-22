# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Chitra, please report it responsibly. **Do not open a public GitHub issue for security vulnerabilities.**

Instead, please email: **chitra@balaganesh.dev**

Include:
- A description of the vulnerability
- Steps to reproduce it
- The potential impact
- Any suggested fix (optional but appreciated)

## Response Timeline

- **Acknowledgment**: Within 48 hours of report
- **Assessment**: Within 7 days
- **Fix or mitigation**: Prioritized based on severity

## Scope

This policy applies to the Chitra codebase and its direct dependencies. It covers:

- The Orchestration Core and all capability modules
- The LLM client and prompt handling
- Data storage (SQLite databases)
- Voice I/O pipeline (audio capture, STT, TTS)
- Configuration handling and environment variables
- Deployment scripts and systemd service files

## Design Principles

Chitra is designed with security in mind:

- **Local first**: All data stays on device. No cloud API calls, no telemetry, no data exfiltration.
- **No network exposure**: Ollama runs on localhost only. No ports are exposed externally.
- **No secrets in code**: All configuration via environment variables. No hardcoded credentials.
- **Input validation**: All user input is validated before use in file paths, database queries, and system commands.
- **Parameterized queries**: All SQL uses parameterized queries via Python's sqlite3 module.

## Supported Versions

| Version | Supported |
|---|---|
| `main` branch (latest) | Yes |
| `dev` branch | Best-effort |
| Older commits | No |

## Acknowledgments

We appreciate the security research community's efforts in responsibly disclosing vulnerabilities. Contributors who report valid security issues will be acknowledged in the changelog (unless they prefer to remain anonymous).
