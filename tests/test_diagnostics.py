"""Tests for chekup.diagnostics engine."""
from chekup.diagnostics.engine import evaluate, Finding
from chekup.config import AppConfig
from chekup.core.cpu import CpuSample
from chekup.core.memory import MemoryInfo


def _cpu(pct=50.0, cores=2):
    """Helper to build a full CpuSample."""
    return CpuSample(
        percent=pct,
        cores=cores,
        per_core=[0.0] * cores,
        freq_mhz=0,
    )


def _mem(pct=50.0):
    """Helper to build a full MemoryInfo."""
    return MemoryInfo(
        percent=pct,
        total_mb=8192,
        used_mb=int(8192 * pct / 100),
        available_mb=int(8192 * (100 - pct) / 100),
        swap_total_mb=2048,
        swap_used_mb=100,
        swap_percent=5.0,
    )


def test_cpu_warning():
    cpu = _cpu(pct=92.5)
    cfg = AppConfig()
    # 92.5 > cpu_critical=85 → critical finding
    findings = evaluate(
        cpu=cpu, memory=_mem(), disk=[], services={},
        containers=[], healthchecks=[], zombies=[],
        config=cfg,
    )
    titles = [f.title for f in findings]
    assert any("CPU" in t and "critical" in t for t in titles)


def test_memory_critical():
    mem = _mem(pct=96.0)
    # 96 > mem_critical=90 → critical finding
    findings = evaluate(
        cpu=_cpu(), memory=mem, disk=[], services={},
        containers=[], healthchecks=[], zombies=[],
        config=AppConfig(),
    )
    titles = [f.title for f in findings]
    assert any("Memory" in t and "critical" in t for t in titles)


def test_no_findings():
    cpu = _cpu(pct=20.0, cores=4)
    mem = _mem(pct=30.0)
    findings = evaluate(
        cpu=cpu, memory=mem, disk=[], services={},
        containers=[], healthchecks=[], zombies=[],
        config=AppConfig(),
    )
    assert len(findings) == 0


def test_diagnostics_disabled():
    cfg = AppConfig()
    cfg.diagnostics_enabled = False
    cpu = _cpu(pct=99.0)
    findings = evaluate(
        cpu=cpu, memory=_mem(), disk=[], services={},
        containers=[], healthchecks=[], zombies=[],
        config=cfg,
    )
    assert len(findings) == 0
