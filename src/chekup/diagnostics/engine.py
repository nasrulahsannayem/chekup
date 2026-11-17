"""Diagnostics engine for Chekup.

Produces :class:`Finding` objects from sampled system state.  All
suggestions are strictly informational — the engine never recommends
running commands that mutate the system, consistent with Chekup's
read-only promise.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..config import AppConfig
from ..core.cpu import CpuSample
from ..core.disk import DiskInfo
from ..core.memory import MemoryInfo

SEVERITIES = ("info", "warning", "critical")


@dataclass
class Finding:
    """A single diagnostic finding.

    Attributes
    ----------
    severity:
        One of ``'info'``, ``'warning'`` or ``'critical'``.
    title:
        Short human-readable label.
    detail:
        What was detected and why it matters.
    suggestion:
        A safe, informational next step for a human to review.
    """

    severity: str
    title: str
    detail: str
    suggestion: str

    def __post_init__(self) -> None:
        if self.severity not in SEVERITIES:
            raise ValueError(
                f"invalid severity {self.severity!r}; must be one of {SEVERITIES}"
            )


def _check_utilization_findings(
    label: str,
    value: Optional[float],
    warn: float,
    critical: float,
    detail_suffix: str = "",
) -> List[Finding]:
    """Emit one finding for a utilization metric against warn/critical bounds."""
    if value is None:
        return []
    if value >= critical:
        return [
            Finding(
                severity="critical",
                title=f"{label} usage is critical",
                detail=(
                    f"{label} usage is at {value:.1f}% which is at or above the "
                    f"critical threshold ({critical:.0f}%). Sustained critical usage "
                    f"can cause timeouts, dropped work{detail_suffix}."
                ),
                suggestion=(
                    f"Review which workloads are consuming {label} and consider "
                    f"scheduling heavy jobs for quieter windows."
                ),
            )
        ]
    if value >= warn:
        return [
            Finding(
                severity="warning",
                title=f"{label} usage is elevated",
                detail=(
                    f"{label} usage is at {value:.1f}% which is at or above the "
                    f"warning threshold ({warn:.0f}%). Continued growth may reach "
                    f"the critical threshold{detail_suffix}."
                ),
                suggestion=(
                    f"Monitor {label} usage over the next refresh cycles and note "
                    f"which processes or mounts account for the load."
                ),
            )
        ]
    return []


def evaluate(
    cpu: Optional[CpuSample],
    memory: Optional[MemoryInfo],
    disk: List[DiskInfo],
    services: Optional[Dict[str, str]],
    containers: Optional[List[Dict[str, Any]]],
    healthchecks: Optional[List[Dict[str, Any]]],
    config: AppConfig,
    zombies: List[Any],
) -> List[Finding]:
    """Evaluate sampled state against configured thresholds.

    Every rule produces a Finding that explains (1) what was detected,
    (2) why it matters, and (3) a safe, informational next step.
    """
    findings: List[Finding] = []

    # Respect the diagnostics_enabled toggle in config.
    if not getattr(config, "diagnostics_enabled", True):
        return findings

    # --- CPU -------------------------------------------------------------
    if cpu is not None:
        findings.extend(
            _check_utilization_findings(
                "CPU", cpu.percent, config.cpu_warn, config.cpu_critical
            )
        )

    # --- Memory ----------------------------------------------------------
    if memory is not None:
        findings.extend(
            _check_utilization_findings(
                "Memory", memory.percent, config.mem_warn, config.mem_critical
            )
        )

    # --- Disks (each configured path individually) ------------------------
    for d in disk:
        if d.percent >= config.disk_critical:
            findings.append(
                Finding(
                    severity="critical",
                    title=f"Disk {d.path} usage is critical",
                    detail=(
                        f"Filesystem mounted at {d.path!r} ({d.mount!r}) is "
                        f"{d.percent:.1f}% full. When a filesystem fills up, new "
                        f"writes fail and applications can crash or lose data."
                    ),
                    suggestion=(
                        f"Identify large or stale files under {d.path!r} (e.g. old "
                        f"logs or archives) and plan archival or removal."
                    ),
                )
            )
        elif d.percent >= config.disk_warn:
            findings.append(
                Finding(
                    severity="warning",
                    title=f"Disk {d.path} usage is elevated",
                    detail=(
                        f"Filesystem mounted at {d.path!r} ({d.mount!r}) is "
                        f"{d.percent:.1f}% full, above the warning threshold "
                        f"({config.disk_warn:.0f}%)."
                    ),
                    suggestion=(
                        f"Watch the growth of {d.path!r} and plan free space "
                        f"before it reaches the critical threshold."
                    ),
                )
            )

    # --- Services ---------------------------------------------------------
    if services:
        for name, state in sorted(services.items()):
            if state == "active":
                continue
            if state == "unknown":
                findings.append(
                    Finding(
                        severity="info",
                        title=f"Service {name} state unknown",
                        detail=(
                            f"Service {name!r} returned state {state!r}; Chekup "
                            f"could not confirm it is active."
                        ),
                        suggestion=(
                            f"Verify whether {name!r} is expected to be installed "
                            f"and running on this host."
                        ),
                    )
                )
            else:
                findings.append(
                    Finding(
                        severity="warning",
                        title=f"Service {name} is not active",
                        detail=(
                            f"Service {name!r} reports state {state!r} instead of "
                            f"'active'. A non-active service may mean dependent "
                            f"functionality is degraded or unavailable."
                        ),
                        suggestion=(
                            f"Review the recent logs for {name!r} to understand why "
                            f"it is not active before taking any action."
                        ),
                    )
                )

    # --- Containers -------------------------------------------------------
    if containers:
        for c in containers:
            state = str(c.get("state", ""))
            name = c.get("name", "<unnamed>")
            if state == "running":
                continue
            findings.append(
                Finding(
                    severity="warning",
                    title=f"Container {name} is not running",
                    detail=(
                        f"Container {name!r} is in state {state!r} with "
                        f"{c.get('restarts', 0)} recorded restarts. A non-running "
                        f"container usually indicates a crash or exit."
                    ),
                    suggestion=(
                        f"Inspect the container's recent log output to understand "
                        f"why it left the running state."
                    ),
                )
            )

    # --- Healthchecks -----------------------------------------------------
    if healthchecks:
        for hc in healthchecks:
            if hc.get("ok"):
                continue
            url = hc.get("url", "<unknown>")
            status = hc.get("status")
            error = hc.get("error")
            reason = (
                f"status {status}"
                if status is not None
                else (f"error: {error}" if error else "failed")
            )
            findings.append(
                Finding(
                    severity="warning",
                    title=f"Healthcheck failed: {url}",
                    detail=(
                        f"Healthcheck for {url!r} did not return the expected "
                        f"result ({reason}). The endpoint may be slow, "
                        f"misconfigured, or down."
                    ),
                    suggestion=(
                        f"Confirm whether {url!r} is expected to be reachable from "
                        f"this host and whether the expected status code is "
                        f"correct in configuration."
                    ),
                )
            )

    # --- Zombie processes -------------------------------------------------
    if zombies:
        count = len(zombies)
        findings.append(
            Finding(
                severity="warning",
                title=f"{count} zombie process(es) detected",
                detail=(
                    f"{count} process(es) are in zombie state. Zombies do not "
                    f"consume CPU or memory but they retain a process table "
                    f"entry until reaped by their parent."
                ),
                suggestion=(
                    f"Identify the parent process(es) of the zombies so they can "
                    f"be reviewed and made to reap their children."
                ),
            )
        )

    return findings
