"""Docker container monitoring (read-only).

Container names always come from user configuration; Chekup never
assumes any particular container exists on the host.
"""

import subprocess
from typing import Any, Dict, List

__all__ = ["get_container_statuses"]


def run(args: List[str], timeout: int = 3) -> str:
    """Run a command, return stripped stdout; empty string on any failure."""
    try:
        p = subprocess.run(args, capture_output=True, text=True,
                           timeout=timeout, errors="replace")
        return p.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


def get_container_status(name: str) -> Dict[str, Any]:
    """Return status and restart count for one container name."""
    out = run(["docker", "inspect", "-f",
               "{{.State.Status}}|{{.RestartCount}}", name])
    if not out or "|" not in out:
        return {"name": name, "state": "not found", "restarts": "?"}
    state, restarts = out.split("|", 1)
    return {"name": name, "state": state.strip(), "restarts": restarts.strip()}


def get_container_statuses(names: List[str]) -> List[Dict[str, Any]]:
    """Return status dicts for the configured container names."""
    return [get_container_status(n) for n in names]
