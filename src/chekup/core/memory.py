from dataclasses import dataclass
import psutil
from typing import Optional

@dataclass
class MemoryInfo:
    total_mb: int
    used_mb: int
    available_mb: int
    percent: float
    swap_total_mb: int
    swap_used_mb: int
    swap_percent: float

def collect_memory() -> MemoryInfo:
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    
    return MemoryInfo(
        total_mb=int(memory.total / 1024 / 1024),
        used_mb=int(memory.used / 1024 / 1024),
        available_mb=int(memory.available / 1024 / 1024),
        percent=memory.percent,
        swap_total_mb=int(swap.total / 1024 / 1024),
        swap_used_mb=int(swap.used / 1024 / 1024),
        swap_percent=swap.percent
    )