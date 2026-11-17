"""Tests for chekup.core modules."""
import psutil
from chekup.core.cpu import collect_cpu, CpuSample
from chekup.core.memory import collect_memory, MemoryInfo
from chekup.core.disk import collect_disk, DiskInfo
from chekup.core.network import collect_network, NetworkInfo
from chekup.core.processes import collect_processes, ProcessInfo
from chekup.core.system import get_system_info, SystemInfo


def test_collect_cpu():
    cpu = collect_cpu()
    assert isinstance(cpu, CpuSample)
    assert 0 <= cpu.percent <= 100
    assert cpu.cores >= 1


def test_collect_memory():
    mem = collect_memory()
    assert isinstance(mem, MemoryInfo)
    assert 0 <= mem.percent <= 100
    assert mem.total_mb > 0


def test_collect_disk():
    disks = collect_disk(("/"))
    # In containers / may not show; test that return is list
    assert isinstance(disks, list)
    if disks:
        d = disks[0]
        assert isinstance(d, DiskInfo)
        assert d.path == "/"
        assert 0 <= d.percent <= 100


def test_collect_network():
    net = collect_network()
    assert isinstance(net, NetworkInfo)
    assert net.received_bytes >= 0
    assert net.sent_bytes >= 0


def test_collect_processes():
    procs = collect_processes()
    assert isinstance(procs, list)
    assert len(procs) >= 1
    p = procs[0]
    assert isinstance(p, ProcessInfo)
    assert hasattr(p, "pid")
    assert hasattr(p, "name")
    # No sensitive data exposed
    assert not hasattr(p, "username")
    assert not hasattr(p, "cmdline")


def test_get_system_info():
    info = get_system_info()
    assert info.hostname is not None
    assert len(info.hostname) > 0
    assert info.uptime_seconds >= 0
    assert info.python_version is not None
