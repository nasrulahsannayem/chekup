"""Textual TUI for Chekup — read-only system monitoring dashboard."""

from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Any, Dict, List

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Footer, Header, DataTable, Static
from textual import events


from .styles import human, age
from ..config import AppConfig, load_config
from ..core.cpu import CpuSample, collect_cpu
from ..core.memory import MemoryInfo, collect_memory
from ..core.disk import DiskInfo, collect_disk
from ..core.system import SystemInfo
from ..core.processes import ProcessInfo, collect_processes
from ..monitoring.services import get_all_services
from ..monitoring.containers import get_container_statuses, list_running_containers
from ..monitoring.healthchecks import (
    get_healthchecks_status,
    check_nginx_listener,
)
from ..diagnostics.engine import evaluate, Finding


class Chekup(App):
    """Live system monitoring dashboard (read-only)."""

    TITLE = "Chekup"
    SUB_TITLE = "Read-only system monitor v1.0.0"
    CSS_PATH = "styles.tcss"

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh_now", "Refresh"),
        ("d", "toggle_details", "Details"),
    ]

    def __init__(self, config: AppConfig | None = None):
        super().__init__()
        self.config = config or load_config()
        self.frame = 0
        self.details = False
        self.cpu_history: list[float] = []
        self.ram_history: list[float] = []
        self.last_services: dict[str, str] = {}
        self.last_processes: list[ProcessInfo] = []

    # -- Compose --
    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Chekup — Read-only system monitor", id="banner")
        with Container(id="metrics"):
            yield Static(id="cpu", classes="metric")
            yield Static(id="ram", classes="metric")
            yield Static(id="disk", classes="metric")
            yield Static(id="host", classes="metric")
        with Container(id="main"):
            yield Static(id="services", classes="panel")
            yield Static(id="endpoints", classes="panel")
            yield DataTable(id="process", classes="panel")
            yield Static(id="alerts", classes="panel")
        yield Static("Starting live monitor ...", id="statusbar")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#process", DataTable).add_columns(
            "PID", "PROCESS", "CPU", "RAM", "STATE",
        )
        self.set_interval(self.config.refresh_interval, self._tick)
        self._tick()

    # -- Layout responsiveness --
    def on_resize(self, event: events.Resize) -> None:
        w = event.size.width
        self.remove_class("compact", "tiny")
        if w < 70:
            self.add_class("tiny")
        elif w < 100:
            self.add_class("compact")

    # -- Actions --
    def action_refresh_now(self) -> None:
        self._tick()

    def action_toggle_details(self) -> None:
        self.details = not self.details
        self._tick()

    # -- Main refresh loop --
    def _tick(self) -> None:
        try:
            self.frame += 1
            # Collect metrics
            cpu = collect_cpu()
            mem = collect_memory()
            disks = collect_disk(self.config.disk_paths)
            procs = collect_processes()
            self.last_processes = procs

            # Services (every 3rd tick)
            if self.frame % 3 == 1 or not self.last_services:
                self.last_services = get_all_services(
                    self.config.services_custom,
                    self.config.services_auto_discover,
                )

            # Containers (auto-discover if enabled)
            containers = []
            if self.config.docker_enabled:
                container_names = self.config.docker_containers
                if self.config.docker_auto_discover and not container_names:
                    container_names = list_running_containers()
                if container_names:
                    containers = get_container_statuses(container_names)

            # Healthchecks + router + nginx fallback
            healthchecks = []
            if self.config.healthchecks:
                healthchecks = get_healthchecks_status(self.config.healthchecks)
            if self.config.router_url:
                from ..monitoring.healthchecks import check_url
                router_result = check_url(self.config.router_url, timeout=2.0)
                if not any(h.get("url") == self.config.router_url for h in healthchecks):
                    healthchecks.append(router_result)
            if self.config.check_nginx:
                nginx_ok = check_nginx_listener()
                if not nginx_ok:
                    healthchecks.append({
                        "url": "nginx(:80/:443)", "ok": False,
                        "status": None, "error": "NOT LISTENING"
                    })

            # Diagnostics
            zombies = [p for p in procs if p.state == "zombie"]
            findings: list[Finding] = []
            if self.config.diagnostics_enabled:
                findings = evaluate(
                    cpu=cpu, memory=mem, disk=disks,
                    services=self.last_services,
                    containers=containers,
                    healthchecks=healthchecks,
                    config=self.config, zombies=zombies,
                )

            # Update history
            self.cpu_history.append(cpu.percent)
            self.ram_history.append(mem.percent)
            self.cpu_history = self.cpu_history[-20:]
            self.ram_history = self.ram_history[-20:]

            # Render panels
            self._render_cpu(cpu)
            self._render_mem(mem)
            self._render_disk(disks)
            self._render_host()
            self._render_services()
            self._render_endpoints(containers, healthchecks)
            self._render_processes()
            self._render_alerts(findings, zombies)
            self._render_statusbar()
        except Exception as exc:
            self.query_one("#statusbar").update(f"[red]Error: {exc}[/]")

    # -- Panels --
    def _bar(self, value: float, width: int = 18) -> str:
        value = max(0.0, min(100.0, value))
        filled = int(value / 100 * width)
        color = "green" if value < 70 else "yellow" if value < 90 else "red"
        return f"[{color}]{'━' * filled}[/][#45536b]{'━' * (width - filled)}[/]"

    def _render_cpu(self, cpu: CpuSample) -> None:
        load = "?/?/?"
        try:
            a, b, c = os.getloadavg()
            load = f"{a:.2f} / {b:.2f} / {c:.2f}"
        except Exception:
            pass
        self.query_one("#cpu").update(
            f"[bold cyan]CPU[/]\n"
            f"[bold white]{cpu.percent:5.1f}%[/]\n{self._bar(cpu.percent)}\n"
            f"[dim]Load: {load} | Cores: {cpu.cores}[/]"
        )

    def _render_mem(self, mem: MemoryInfo) -> None:
        self.query_one("#ram").update(
            f"[bold cyan]MEMORY[/]\n"
            f"[bold white]{mem.percent:5.1f}%[/]\n{self._bar(mem.percent)}\n"
            f"[dim]{mem.used_mb} MB / {mem.total_mb} MB | Free: {mem.available_mb} MB[/]\n"
            f"[dim]Swap: {mem.swap_percent:.0f}% ({mem.swap_used_mb} / {mem.swap_total_mb} MB)[/]"
        )

    def _render_disk(self, disks: list[DiskInfo]) -> None:
        lines: list[str] = ["[bold cyan]STORAGE[/]"]
        for d in disks:
            lines.append(f"{d.path}: [bold]{d.percent:.0f}%[/] {self._bar(d.percent, 12)}")
            lines.append(f"[dim]{d.used_mb} MB / {d.total_mb} MB[/]")
        self.query_one("#disk").update("\n".join(lines))

    def _render_host(self) -> None:
        now = datetime.now()
        boot = int(time.time() - __import__("psutil").boot_time())
        uname = os.uname()
        self.query_one("#host").update(
            f"[bold cyan]SYSTEM[/]\n"
            f"[bold white]{uname.nodename}[/]\n"
            f"OS: {uname.sysname} {uname.release}\n"
            f"Uptime: {age(boot)}\n"
            f"[dim]{now.strftime('%d %b %Y %H:%M:%S')}[/]"
        )

    def _render_services(self) -> None:
        lines: list[str] = ["[bold cyan]SERVICES[/]"]
        if not self.last_services:
            lines.append("[dim]No services configured[/]")
        else:
            for name, state in sorted(self.last_services.items()):
                ok = state == "active"
                icon = "🟢" if ok else "🟡"
                clr = "green" if ok else "yellow"
                lines.append(f"{icon} {name:<14} [{clr}]{state}[/]")
        self.query_one("#services").update("\n".join(lines))

    def _render_endpoints(self, containers: list[dict], healthchecks: list[dict]) -> None:
        lines: list[str] = ["[bold cyan]ENDPOINTS[/]"]
        for c in containers:
            ok = c.get("state") == "running"
            clr = "green" if ok else "red"
            lines.append(f"[{clr}]📦 {c['name']}[/] — {c.get('state', '?')}")
        for hc in healthchecks:
            ok = hc.get("ok")
            clr = "green" if ok else "red"
            url = hc.get("url", "?")
            lines.append(f"[{clr}]🔗 {url}[/] — {hc.get('status', 'error')}")
        if not containers and not healthchecks:
            lines.append("[dim]No endpoints configured[/]")
        self.query_one("#endpoints").update("\n".join(lines))

    def _render_processes(self) -> None:
        top = sorted(self.last_processes, key=lambda p: p.cpu_percent, reverse=True)
        table = self.query_one("#process", DataTable)
        table.clear()
        for p in top[:12]:
            table.add_row(
                str(p.pid),
                p.name[:18],
                f"{p.cpu_percent:.1f}%",
                f"{p.mem_percent:.1f}%",
                p.state[:10],
            )

    def _render_alerts(self, findings: list[Finding], zombies: list[ProcessInfo]) -> None:
        lines: list[str] = []
        if not findings:
            lines.append("[green]✓ No issues detected[/]")
        for f in findings:
            icon = {"critical": "🔴", "warning": "🟡", "info": "ℹ️"}.get(f.severity, "?")
            clr = {"critical": "red", "warning": "yellow", "info": "blue"}.get(f.severity, "white")
            lines.append(f"[{clr}]{icon} {f.title}[/]")
            if self.details:
                lines.append(f"[dim]{f.detail}[/]")
                lines.append(f"[dim]→ {f.suggestion}[/]")
        if zombies:
            lines.append(f"[yellow]{len(zombies)} zombie process(es)[/]")
        lines.append("")
        lines.append("[dim]Chekup is READ-ONLY. No action will be taken automatically.[/]")
        self.query_one("#alerts").update("\n".join(lines))

    def _render_statusbar(self) -> None:
        now = datetime.now()
        spin = ["◐", "◓", "◑", "◒"][self.frame % 4]
        self.query_one("#statusbar").update(
            f"{spin} LIVE  {now.strftime('%H:%M:%S')}  |  "
            f"Refresh: {self.config.refresh_interval:.0f}s  |  "
            "q Quit  •  r Refresh  •  d Details  |  "
            "READ-ONLY"
        )
        self.sub_title = f"v1.0.0 — {self.frame} refresh(es)"
