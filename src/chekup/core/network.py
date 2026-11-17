from dataclasses import dataclass
import psutil
from typing import Dict

@dataclass
class NetworkInfo:
    received_bytes: int
    sent_bytes: int
    per_interface: Dict[str, Dict[str, int]]

def collect_network() -> NetworkInfo:
    counters = psutil.net_io_counters(pernic=True)
    total_recv = sum(c.bytes_recv for c in counters.values())
    total_sent = sum(c.bytes_sent for c in counters.values())
    per_iface = {}
    for iface, c in counters.items():
        per_iface[iface] = {'received_bytes': c.bytes_recv, 'sent_bytes': c.bytes_sent}
    return NetworkInfo(
        received_bytes=total_recv,
        sent_bytes=total_sent,
        per_interface=per_iface
    )