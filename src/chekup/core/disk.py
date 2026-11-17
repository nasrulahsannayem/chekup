from dataclasses import dataclass
import psutil
from typing import List, Optional

@dataclass
class DiskInfo:
    path: str
    mount: str
    total_mb: int
    used_mb: int
    free_mb: int
    percent: float
    fstype: str

def collect_disk(paths: tuple[str, ...]) -> List[DiskInfo]:
    disk_infos = []
    for path in paths:
        try:
            usage = psutil.disk_usage(path)
            disk_infos.append(DiskInfo(
                path=path,
                mount=usage.mountpoint,
                total_mb=int(usage.total / 1024 / 1024),
                used_mb=int(usage.used / 1024 / 1024),
                free_mb=int(usage.free / 1024 / 1024),
                percent=usage.percent,
                fstype=usage.fstype
            ))
        except Exception:
            continue
    return disk_infos