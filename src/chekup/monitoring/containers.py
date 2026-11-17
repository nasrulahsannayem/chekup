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


def list_running_containers() -> List[str]:
    """Auto-discover all running container names via `docker ps`."""
    try:
        p = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=5, errors="replace"
        )
        names = [n.strip() for n in p.stdout.strip().splitlines() if n.strip()]
        return names
    except Exception:
        return []


def get_container_status(name: str) -> Dict[str, Any]:
    """Return status and restart count for one container name."""
    out = run(["docker", "inspect", "-f",
               "{{.State.Status}}|{{.RestartCount}}", name])
    if not out or "|" not in out:
        return {"name": name, "state": "not found", "restarts": "?"}
    state, restarts = out.split("|", 1)
    return {"name": name, "state": state.strip(), "restarts": restarts.strip()}


def get_container_statuses(names: List[str]) -> List[Dict[str, Any]]:
    """Return status dicts for the configured container names.

    Fully config-driven: whatever container names the user lists in
    config (``docker_containers``) get real ``docker inspect`` data.
    No container name is ever hard-coded.
    """
    return [get_container_status(n) for n in names]
