"""
System State capability.

Always-available device and environment context.
Injected into every LLM call alongside Memory.

No database — reads live system state on every call.
Uses only standard library and cross-platform interfaces (Linux + macOS).

Actions:
    get() — return current system state snapshot
"""

import logging
import shutil
import subprocess
from datetime import datetime

logger = logging.getLogger(__name__)


class SystemState:
    """Provides current device and environment context."""

    async def get(self) -> dict:
        """Return current system state snapshot.

        Returns:
            {
                "datetime": str (ISO format),
                "day_of_week": str (e.g. "Monday"),
                "battery_percent": int (0-100, -1 if unavailable),
                "time_of_day": "morning" | "afternoon" | "evening" | "night"
            }

        """
        try:
            now = datetime.now()
            hour = now.hour

            if 5 <= hour < 12:
                time_of_day = "morning"
            elif 12 <= hour < 17:
                time_of_day = "afternoon"
            elif 17 <= hour < 21:
                time_of_day = "evening"
            else:
                time_of_day = "night"

            return {
                "datetime": now.isoformat(),
                "day_of_week": now.strftime("%A"),
                "battery_percent": self._get_battery_percent(),
                "time_of_day": time_of_day,
            }

        except Exception as e:
            logger.error("Failed to get system state: %s", e)
            return {
                "datetime": datetime.now().isoformat(),
                "day_of_week": datetime.now().strftime("%A"),
                "battery_percent": -1,
                "time_of_day": "unknown",
            }

    def _get_battery_percent(self) -> int:
        """Read battery percentage. Cross-platform: Linux and macOS.

        Returns -1 if battery info is unavailable (e.g. desktop without battery).
        """
        # Linux — read from /sys
        try:
            with open("/sys/class/power_supply/BAT0/capacity", "r") as f:
                return int(f.read().strip())
        except (FileNotFoundError, ValueError, PermissionError):
            pass

        # macOS — use pmset
        if shutil.which("pmset"):
            try:
                result = subprocess.run(
                    ["pmset", "-g", "batt"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                # Output contains a line like: "... 85%; charging; ..."
                for line in result.stdout.splitlines():
                    if "%" in line:
                        # Extract the number before %
                        pct_str = line.split("%")[0].split()[-1]
                        return int(pct_str)
            except (subprocess.TimeoutExpired, ValueError, IndexError):
                pass

        # No battery info available (desktop machine, VM, etc.)
        return -1
