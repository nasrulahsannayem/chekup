"""Systemd service monitoring (read-only).

Service names always come from user configuration.  When
``auto_discover`` is enabled, the first active services on the host
are picked up; otherwise only explicitly configured services are shown.
"""

import subprocess
from typing import Dict, List

__all__ = ["get_service_status", "get_all_services"]


def run(args: List[str], timeout: int = 3) -> str:
    """Run a command, return stripped stdout; empty string on any failure."""
    try:
        p = subprocess.run(args, capture_output=True, text=True,
                           timeout=timeout, errors="replace")
        return p.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


def get_service_status(name: str) -> str:
    """Return the systemd state of one unit (active/inactive/unknown...)."""
    status = run(["systemctl", "is-active", name])
    return status if status else "unknown"


def _discover_active_services(limit: int = 6) -> List[str]:
    """Best-effort discovery of currently active services (read-only)."""
    out = run(
        ["systemctl", "list-units", "--type=service", "--state=active",
         "--no-legend", "--no-pager"], timeout=4)
    names: List[str] = []
    for line in out.splitlines():
        parts = line.split()
        if parts and parts[0].endswith(".service"):
            names.append(parts[0][: -len(".service")])
        if len(names) >= limit:
            break
    return names


def get_all_services(custom: List[str], auto_discover: bool = True) -> Dict[str, str]:
    """Return {unit: state} for configured services."""
    names: List[str] = list(custom)
    if auto_discover and not names:
        names = _discover_active_services()
    if not names:
        return {}
    return {n: get_service_status(n) for n in names}
