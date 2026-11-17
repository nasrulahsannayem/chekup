"""System information utilities."""

import socket
import platform
import psutil
import time
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class SystemInfo:
    hostname: str
    os_name: str
    kernel: str
    arch: str
    python_version: str
    load1: float
    load5: float
    load15: float
    uptime_seconds: int

    @classmethod
    def collect(cls) -> SystemInfo:
        hostname = socket.gethostname()
        os_name = platform.system()
        kernel = platform.release()
        arch = platform.machine()
        python_version = platform.python_version()
        try:
            load1, load5, load15 = psutil.getloadavg()
        except Exception:
            load1 = load5 = load15 = 0.0
        boot_time = psutil.boot_time()
        uptime_seconds = int(time.time() - boot_time)
        return cls(
            hostname=hostname,
            os_name=os_name,
            kernel=kernel,
            arch=arch,
            python_version=python_version,
            load1=load1,
            load5=load5,
            load15=load15,
            uptime_seconds=uptime_seconds,
        )

def get_system_info() -> SystemInfo:
    """Convenient wrapper returning SystemInfo.collect()."""
    return SystemInfo.collect()

__all__ = ["SystemInfo", "collect", "get_system_info"]
