"""
Chitra — AI-first Operating System
Entry point. Boots the AI Orchestration Core as the primary process.
"""

import asyncio
import os

from dotenv import load_dotenv

from orchestration.core import OrchestrationCore


def main():
    """Boot Chitra. Load configuration, initialize the Orchestration Core, and run."""
    load_dotenv()

    data_dir = os.environ.get("CHITRA_DATA_DIR", os.path.expanduser("~/.chitra/data"))
    os.makedirs(data_dir, exist_ok=True)

    core = OrchestrationCore()
    asyncio.run(core.run())


if __name__ == "__main__":
    main()
