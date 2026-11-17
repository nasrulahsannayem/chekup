from dataclasses import dataclass
import psutil
import time
from typing import List, Dict, Any, Optional

# Persistent cache for process CPU sampling
_PROCESS_CPU_CACHE: Dict[int, Any] = {}

@dataclass
class ProcessInfo:
    pid: int
    ppid: int
    name: str
    user: str
    state: str
    cpu_percent: float
    mem_percent: float
    age_seconds: int
    cmd: str

def collect_processes() -> List[ProcessInfo]:
    global _PROCESS_CPU_CACHE
    processes: List[ProcessInfo] = []
    current_time = time.time()
    
    # Prune stale cache entries
    stale_pids = set(_PROCESS_CPU_CACHE.keys())
    
    for p in psutil.process_iter(['pid', 'ppid', 'name', 'username', 'status', 'create_time', 'cmdline']):
        try:
            pid = p.info['pid']
            create_time = p.info['create_time']

            # Update stale_pids
            if pid in stale_pids:
                stale_pids.remove(pid)

            # Get CPU percent (uses internal caching, first call may return 0.0 or low values)
            if pid not in _PROCESS_CPU_CACHE:
                _PROCESS_CPU_CACHE[pid] = p

            # Attempt to get cpu_percent using the cached process object
            # This requires calling cpu_percent multiple times to get meaningful values
            # and relies on psutil's internal logic.
            # We don't store actual cpu_percent in cache, just the process object for psutil to use.
            cpu_percent = p.cpu_percent(interval=None) # psutil uses its internal cache

            mem_percent = p.memory_percent()
            age_seconds = int(current_time - create_time)
            
            cmd = " ".join(p.info['cmdline']) if p.info['cmdline'] else p.info['name']
            cmd = (cmd[:237] + '...') if len(cmd) > 240 else cmd # Truncate to 240 chars

            processes.append(ProcessInfo(
                pid=pid,
                ppid=p.info['ppid'],
                name=p.info['name'],
                user=p.info['username'],
                state=p.info['status'],
                cpu_percent=cpu_percent,
                mem_percent=mem_percent,
                age_seconds=age_seconds,
                cmd=cmd
            ))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, TypeError, KeyError):
            # Process may have exited, or permissions denied, or it's a zombie
            if p.info['pid'] in _PROCESS_CPU_CACHE:
                del _PROCESS_CPU_CACHE[p.info['pid']]
            continue
    
    # Remove truly stale entries from cache
    for pid in stale_pids:
        if pid in _PROCESS_CPU_CACHE:
            del _PROCESS_CPU_CACHE[pid]

    return processes

# Initialize psutil's internal CPU sampling to prevent first call returning 0.0 for total CPU percent.
# This is a module-level action as suggested for consistent sampling in psutil.
# For individual process CPU percent, the `interval=None` in loop is the correct way.
psutil.cpu_percent()
