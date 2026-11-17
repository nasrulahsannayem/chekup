"""CPU monitoring utilities."""

import psutil
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class CpuSample:
    """Snapshot of CPU utilization."""

    percent: float
    per_core: List[float]
    freq_mhz: Optional[float]
    cores: int


__all__ = ["CpuSample", "collect_cpu", "get_cpu_percent", "get_cpu_frequency", "get_cpu_cores"]


def collect_cpu() -> CpuSample:
    """Return a CpuSample with current CPU metrics."""
    per_core = psutil.cpu_percent(interval=None, percpu=True)
    freq = psutil.cpu_freq()
    return CpuSample(
        percent=psutil.cpu_percent(interval=None),
        per_core=per_core,
        freq_mhz=freq.current if freq else None,
        cores=psutil.cpu_count(logical=True),
    )


def get_cpu_percent(interval: float | None = None) -> float:
    """Return the CPU utilization percentage."""
    return psutil.cpu_percent(interval=interval)


def get_cpu_frequency() -> Optional[float]:
    """Return the current CPU frequency in MHz."""
    freq = psutil.cpu_freq()
    return freq.current if freq else None


def get_cpu_cores() -> int:
    """Return the number of CPU cores."""
    return psutil.cpu_count(logical=True)
